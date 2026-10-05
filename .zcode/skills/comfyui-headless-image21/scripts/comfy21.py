#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
comfy21.py -- headless ComfyUI client for Qwen-Image 2.1 game assets. Stdlib only.

Subcommands:
  find                     Discover install, python, model registrations; check 2.1 weights
  models                   List what the running server has registered per folder
  serve [--port 8188]      Start headless server if not already up (idempotent)
  t2i   --prompt TXT       Text-to-image. --width/--height/--seed/--steps/--out/--no-alpha
  edit  --image PATH       Reference-guided edit (default: background removal -> RGBA PNG)
        [--instruction TXT] [--width/--height unused: canvas follows the reference]
  stop                     Kill the server started on the chosen port

No install paths are hardcoded. Discovery order:
  1. env COMFYUI_HOME (dir containing ComfyUI/main.py or main.py)
  2. %%APPDATA%%/Comfy Desktop/installations.json  (Desktop app install registry)
  3. shallow scan of common roots for a ComfyUI checkout
Model registrations are read from (never assumed):
  %%APPDATA%%/Comfy Desktop/settings.json (modelsDirs)
  %%APPDATA%%/Comfy Desktop/shared_model_paths.yaml
  <code_root>/extra_model_paths.yaml
  live server GET /models/<folder>  (ground truth when server is up)
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~") + "/AppData/Roaming")
DESKTOP_DIR = os.path.join(APPDATA, "Comfy Desktop")
PORT = 8188
SERVER = f"http://127.0.0.1:{PORT}"

QWEN21_FILES = {
    "diffusion_models": ["qwen_image_2.1_int8_convrot.safetensors", "qwen_image_2.1_bf16.safetensors"],
    "text_encoders": ["qwen3vl_8b_int8_convrot.safetensors", "qwen3vl_8b_bf16.safetensors"],
    "vae": ["qwen_image_2.1_vae_bf16.safetensors"],
}
HF_REPO = "Comfy-Org/Qwen-Image-2.1"
HF_URL = "https://huggingface.co/{repo}/resolve/main/split_files/{folder}/{file}"
MIRROR_URL = "https://hf-mirror.com/{repo}/resolve/main/split_files/{folder}/{file}"


def log(msg):
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


# ---------------------------------------------------------------- discovery

def _yaml_base_paths(path):
    """Regex-parse base_path entries from an extra_model_paths-style yaml (no yaml dep).
    Comment lines are skipped: the Desktop-generated yaml embeds a `base_path: '...'`
    EXAMPLE inside its header comment, and Windows will happily treat '...' as a path."""
    out = []
    if not os.path.isfile(path):
        return out
    for line in open(path, encoding="utf-8", errors="replace"):
        s = line.strip()
        if s.startswith("#"):
            continue
        m = re.search(r"base_path\s*:\s*['\"]?([^'\"\n]+)", s)
        if m:
            b = m.group(1).strip()
            if os.path.isabs(b) and os.path.isdir(b):
                out.append(b)
    return out


def discover():
    """Return dict with code_root (dir holding main.py), python_exe, model_dirs, input_dir, output_dir."""
    cands = []
    env = os.environ.get("COMFYUI_HOME")
    if env:
        cands.append(env)
    inst = os.path.join(DESKTOP_DIR, "installations.json")
    if os.path.isfile(inst):
        try:
            for item in json.load(open(inst, encoding="utf-8")):
                cands.append(item.get("installPath", ""))
        except Exception as e:
            log(f"warn: cannot parse {inst}: {e}")
    # Shallow scan: every existing drive root + common program dirs, no machine-specific paths.
    # Matched "*omfy*" dirs are scanned one level deeper (installs often nest: .../ComfyUI-Installs).
    roots = ["C:\\Program Files", os.path.expanduser("~"),
             os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")]
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        dr = f"{letter}:\\"
        if os.path.isdir(dr):
            roots.append(dr)
    for root in roots:
        try:
            entries = [d for d in os.listdir(root) if "omfy" in d.lower()]
        except OSError:
            continue
        cands += [os.path.join(root, d) for d in entries]
        for d in entries:
            sub = os.path.join(root, d)
            if os.path.isdir(sub):
                try:
                    cands += [os.path.join(sub, s) for s in os.listdir(sub) if "omfy" in s.lower()]
                except OSError:
                    pass

    code_root = None
    for c in cands:
        if not c or not os.path.isdir(c):
            continue
        for sub in ["ComfyUI", "."]:
            if os.path.isfile(os.path.join(c, sub, "main.py")):
                code_root = os.path.abspath(os.path.join(c, sub))
                break
        if code_root:
            break
    if code_root is None:
        sys.exit("[FATAL] No ComfyUI checkout found. Set COMFYUI_HOME to the folder containing "
                 "ComfyUI/main.py (or main.py directly) and retry.")

    py = None
    for p in [os.path.join(code_root, ".venv", "Scripts", "python.exe"),
              os.path.join(code_root, ".venv", "bin", "python"),
              os.path.join(os.path.dirname(code_root), ".venv", "Scripts", "python.exe")]:
        if os.path.isfile(p):
            py = p
            break
    if py is None:
        log("warn: no bundled .venv python found; falling back to sys.executable "
            "(needs torch installed)")
        py = sys.executable

    model_dirs = []
    settings = os.path.join(DESKTOP_DIR, "settings.json")
    if os.path.isfile(settings):
        try:
            model_dirs += [p for p in json.load(open(settings, encoding="utf-8")).get("modelsDirs", [])
                           if os.path.isdir(p)]
        except Exception:
            pass
    for y in [os.path.join(DESKTOP_DIR, "shared_model_paths.yaml"),
              os.path.join(code_root, "extra_model_paths.yaml")]:
        for b in _yaml_base_paths(y):
            if os.path.isdir(b) and b not in model_dirs:
                model_dirs.append(b)

    input_dir = output_dir = None
    for md in model_dirs:
        sib = os.path.dirname(md.rstrip("\\/"))
        if os.path.isdir(os.path.join(sib, "input")):
            input_dir = os.path.join(sib, "input")
            output_dir = os.path.join(sib, "output")
            break
    return {"code_root": code_root, "python_exe": py, "model_dirs": model_dirs,
            "input_dir": input_dir, "output_dir": output_dir}


# ---------------------------------------------------------------- http

def http_json(url, payload=None, timeout=30):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def server_up():
    try:
        http_json(f"{SERVER}/system_stats", timeout=4)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- weights

def registered_dirs_for(folder, d):
    """Registered directories that may hold <folder> models, best-effort ordering."""
    hits = []
    for md in d["model_dirs"]:
        cand = os.path.join(md, folder)
        if os.path.isdir(cand):
            hits.append(cand)
    return hits


def check_weights(d):
    """For each 2.1 component: preferred available file, or download hints. Returns picks."""
    picks = {}
    for folder, names in QWEN21_FILES.items():
        dirs = registered_dirs_for(folder, d)
        found = None
        for name in names:
            for dr in dirs:
                p = os.path.join(dr, name)
                if os.path.isfile(p):
                    found = (name, p)
                    break
            if found:
                break
        if found:
            picks[folder] = found[0]
            log(f"OK  {folder}: {found[0]}  ({os.path.getsize(found[1]) / 2**30:.1f} GiB)")
        else:
            picks[folder] = None
            log(f"MISS {folder}: none of {names} found in {dirs or '(no registered dir)'}")
            for name in names[:1]:
                log(f"     download -> {HF_URL.format(repo=HF_REPO, folder=folder, file=name)}")
                log(f"     mirror   -> {MIRROR_URL.format(repo=HF_REPO, folder=folder, file=name)}")
    missing = [k for k, v in picks.items() if v is None]
    if missing:
        log("hint: huggingface-cli download (mirror): HF_ENDPOINT=https://hf-mirror.com "
            f"huggingface-cli download {HF_REPO} split_files/<folder>/<file> --local-dir <registered_dir>")
    return picks


# ---------------------------------------------------------------- serve / stop

def serve(args_port):
    global PORT, SERVER
    PORT = args_port
    SERVER = f"http://127.0.0.1:{PORT}"
    if server_up():
        log(f"server already up at {SERVER}, reusing")
        return
    d = discover()
    shared_yaml = os.path.join(DESKTOP_DIR, "shared_model_paths.yaml")
    launch = [d["python_exe"], os.path.join(d["code_root"], "main.py"),
              "--port", str(PORT), "--disable-auto-launch"]
    if os.path.isfile(shared_yaml):
        launch += ["--extra-model-paths-config", shared_yaml]
    if d["input_dir"]:
        launch += ["--input-directory", d["input_dir"], "--output-directory", d["output_dir"]]
    log_path = os.path.join(os.environ.get("TEMP", "."), "comfy21_server.log")
    log_fh = open(log_path, "ab", buffering=0)
    log_fh.write(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} serve port={PORT} =====\n".encode())
    subprocess.Popen(launch, cwd=d["code_root"], stdout=log_fh, stderr=subprocess.STDOUT,
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    log(f"starting server on {SERVER}; log: {log_path}")
    deadline = time.time() + 300
    while time.time() < deadline:
        if server_up():
            log("server ready")
            return
        time.sleep(3)
    sys.exit(f"[FATAL] server not ready after 300s, see {log_path}")


def stop():
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    pids = {line.split()[-1] for line in out.splitlines()
            if f":{PORT}" in line and "LISTENING" in line}
    for pid in pids:
        subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
        log(f"killed pid {pid}")


# ---------------------------------------------------------------- workflows

def build_t2i(picks, prompt, w, h, seed, steps, batch=1, negative=None, cfg=1.0,
              sampler="euler", scheduler="simple"):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": picks["diffusion_models"], "weight_dtype": "default"},
              "_meta": {"title": "diffusion_model"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": picks["text_encoders"], "type": "qwen_image", "device": "default"},
              "_meta": {"title": "text_encoder"}},
        "3": {"class_type": "TextEncodeQwenImage21",
              "inputs": {"clip": ["2", 0], "prompt": prompt,
                         "negative_prompt": negative, "resolution": max(w, h)},
              "_meta": {"title": "prompt"}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": batch},
              "_meta": {"title": "latent"}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": picks["vae"]}, "_meta": {"title": "vae"}},
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["3", 0], "negative": ["3", 1], "latent_image": ["4", 0],
                         "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": sampler,
                         "scheduler": scheduler, "denoise": 1.0},
              "_meta": {"title": "sampler"}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["5", 0]}, "_meta": {"title": "decode"}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "qwen21_t2i"},
              "_meta": {"title": "save"}},
    }


def build_edit(picks, image_name, instruction, seed, steps, res, negative="", cfg=1.0):
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": image_name, "upload": "image"},
              "_meta": {"title": "reference_image"}},
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": picks["diffusion_models"], "weight_dtype": "default"},
              "_meta": {"title": "diffusion_model"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": picks["text_encoders"], "type": "qwen_image", "device": "default"},
              "_meta": {"title": "text_encoder"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": picks["vae"]}, "_meta": {"title": "vae"}},
        # NOTE: dotted key "images.image_1" -- flat "image_1" raises TypeError and a nested
        # "images": {...} dict is SILENTLY DROPPED (reference never reaches the model).
        "5": {"class_type": "TextEncodeQwenImage21",
              "inputs": {"clip": ["3", 0], "prompt": instruction, "negative_prompt": negative,
                         "vae": ["4", 0], "resolution": res, "images.image_1": ["1", 0]},
              "_meta": {"title": "prompt"}},
        # latent_image = encoder output slot 2: canvas follows the reference image size
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["2", 0], "positive": ["5", 0], "negative": ["5", 1], "latent_image": ["5", 2],
                         "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": "euler",
                         "scheduler": "simple", "denoise": 1.0},
              "_meta": {"title": "sampler"}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["4", 0]}, "_meta": {"title": "decode"}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "qwen21_edit"},
              "_meta": {"title": "save"}},
    }


# ---------------------------------------------------------------- submit / fetch

OFFICIAL_RGBA_TEMPLATE = ("This is an RGBA image with transparency. {prompt} "
                          "The image has alpha channel and the background is transparent.")


def apply_transparent(prompt):
    """Wrap in the official model-card RGBA template unless the prompt already
    mentions alpha (which triggers transparency on its own)."""
    if "alpha" in prompt.lower():
        return prompt
    return OFFICIAL_RGBA_TEMPLATE.format(prompt=prompt)


def submit(wf):
    try:
        pid = http_json(f"{SERVER}/prompt", payload={"prompt": wf})["prompt_id"]
        log(f"submitted prompt_id={pid}")
        return pid
    except urllib.error.HTTPError as e:
        log("submit rejected:")
        print(e.read().decode("utf-8", errors="replace")[:3000])
        sys.exit(1)


def fetch(pid, out_dir, stem, timeout=1800):
    deadline = time.time() + timeout
    while time.time() < deadline:
        h = http_json(f"{SERVER}/history/{pid}", timeout=30)
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                for m in st.get("messages", []):
                    if m[0] == "execution_error":
                        log(f"node {m[1].get('node_id')} ({m[1].get('node_type')}): "
                            f"{m[1].get('exception_message', '')[:400]}")
                sys.exit(1)
            if st.get("completed"):
                break
        time.sleep(2)
    else:
        sys.exit(f"[FATAL] timeout after {timeout}s")
    os.makedirs(out_dir, exist_ok=True)
    saved = []
    for _, out in h[pid].get("outputs", {}).items():
        for img in out.get("images", []):
            q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""),
                                        "type": img.get("type", "output")})
            ext = os.path.splitext(img["filename"])[1] or ".png"
            dest = os.path.join(out_dir, f"{stem}{ext}")
            n = 1
            while os.path.exists(dest):
                dest = os.path.join(out_dir, f"{stem}_{n}{ext}")
                n += 1
            urllib.request.urlretrieve(f"{SERVER}/view?{q}", dest)
            saved.append(dest)
            log(f"saved {dest}")
    return saved


# ---------------------------------------------------------------- subcommands

def cmd_find(_a):
    d = discover()
    log(f"code_root : {d['code_root']}")
    log(f"python    : {d['python_exe']}")
    log(f"model_dirs: {d['model_dirs'] or '(none registered)'}")
    log(f"input/out : {d['input_dir']} | {d['output_dir']}")
    log(f"server    : {'up at ' + SERVER if server_up() else 'not running'}")
    if server_up():
        for folder in QWEN21_FILES:
            try:
                names = http_json(f"{SERVER}/models/{folder}", timeout=10)
                q = [n for n in names if "qwen_image_2.1" in n or "qwen3vl_8b" in n]
                log(f"server {folder}: {q if q else '(no 2.1 files registered)'}")
            except Exception as e:
                log(f"server {folder}: query failed ({e})")
    log("--- 2.1 weight check (filesystem over registered dirs) ---")
    check_weights(d)


def cmd_models(_a):
    for folder in ["diffusion_models", "text_encoders", "vae", "loras", "checkpoints"]:
        try:
            names = http_json(f"{SERVER}/models/{folder}", timeout=10)
            log(f"{folder}: {len(names)} file(s)")
            for n in names:
                print("  ", n)
        except Exception as e:
            log(f"{folder}: query failed ({e})")


def read_prompts(path):
    """Prompts file -> list of prompt strings.
    .json: an array of strings (or {"prompts": [...]}).
    text : blocks separated by BLANK lines (a prompt may span multiple lines;
           single-line files behave as before). '#' comment lines are skipped."""
    txt = open(path, encoding="utf-8-sig").read()
    if path.lower().endswith(".json"):
        data = json.loads(txt)
        if isinstance(data, dict):
            data = data.get("prompts", [])
        if not isinstance(data, list):
            sys.exit('[FATAL] JSON prompts file must be an array of strings or {"prompts": [...]}')
        return [str(p) for p in data if str(p).strip()]
    blocks, cur = [], []
    for line in txt.splitlines():
        if line.strip() == "":
            if cur:
                blocks.append(" ".join(s.strip() for s in cur if s.strip()))
                cur = []
        elif not line.lstrip().startswith("#"):
            cur.append(line)
    if cur:
        blocks.append(" ".join(s.strip() for s in cur if s.strip()))
    return blocks


def cmd_t2i(a):
    if not a.prompt and not a.prompts_file:
        sys.exit("[FATAL] --prompt or --prompts-file required")
    serve(a.port)
    picks = check_weights(discover())
    if None in picks.values():
        sys.exit("[FATAL] missing 2.1 weights; download first (see hints above)")

    def prepare(prompt):
        return apply_transparent(prompt) if a.transparent else prompt

    if a.negative and a.cfg <= 1.0:
        log("hint: negative_prompt has no effect at cfg<=1 (official path is cfg 1); "
            "pass --cfg 2 to activate it")
    if a.prompts_file:
        lines = read_prompts(a.prompts_file)
        if not lines:
            sys.exit(f"[FATAL] no prompts in {a.prompts_file}")
        # submit ALL first (the server queues them), then collect -- keeps the GPU busy
        jobs = []
        for i, line in enumerate(lines):
            wf = build_t2i(picks, prepare(line), a.width, a.height, a.seed + i, a.steps,
                           negative=a.negative, cfg=a.cfg, sampler=a.sampler, scheduler=a.scheduler)
            jobs.append((f"qwen21_t2i_{i + 1:02d}", submit(wf)))
        log(f"queued {len(jobs)} job(s)")
        for stem, pid in jobs:
            fetch(pid, a.out, stem, a.timeout)
        return

    wf = build_t2i(picks, prepare(a.prompt), a.width, a.height, a.seed, a.steps, batch=a.n,
                   negative=a.negative, cfg=a.cfg, sampler=a.sampler, scheduler=a.scheduler)
    fetch(submit(wf), a.out, "qwen21_t2i", a.timeout)


def cmd_edit(a):
    serve(a.port)
    d = discover()
    picks = check_weights(d)
    if None in picks.values():
        sys.exit("[FATAL] missing 2.1 weights; download first (see hints above)")
    if not os.path.isfile(a.image):
        sys.exit(f"[FATAL] image not found: {a.image}")
    if not d["input_dir"]:
        sys.exit("[FATAL] no input directory discovered; start the server manually with "
                 "--input-directory set, or register models via Comfy Desktop")
    target = os.path.join(d["input_dir"], f"_comfy21_ref_{os.getpid()}_{os.path.basename(a.image)}")
    shutil.copyfile(a.image, target)
    log(f"reference copied to {target}")
    instruction = a.instruction or "Remove the background, and output a PNG image"
    res = a.resolution if a.resolution else 1024
    if a.negative and a.cfg <= 1.0:
        log("hint: negative_prompt has no effect at cfg<=1; pass --cfg 2 to activate it")
    wf = build_edit(picks, os.path.basename(target), instruction, a.seed, a.steps, res,
                    negative=a.negative, cfg=a.cfg)
    try:
        fetch(submit(wf), a.out, "qwen21_edit", a.timeout)
    finally:
        try:
            os.remove(target)  # don't accumulate reference copies in the server input dir
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser(description="Qwen-Image 2.1 game assets via headless ComfyUI")
    ap.add_argument("--port", type=int, default=PORT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("find")
    sub.add_parser("models")
    sub.add_parser("serve")
    sub.add_parser("stop")
    p = sub.add_parser("t2i")
    p.add_argument("--prompt", default=None, help="required unless --prompts-file")
    p.add_argument("--prompts-file", dest="prompts_file", default=None,
                   help="one prompt per line (# comments ok); one queued job per line")
    p.add_argument("--n", type=int, default=1,
                   help="variations of one prompt in a SINGLE run (latent batch; fastest multi-image path)")
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--seed", type=int, default=42, help="batch items use seed, seed+1, ...")
    p.add_argument("--steps", type=int, default=25)
    p.add_argument("--negative", default=None, help="negative prompt; INACTIVE at cfg<=1, pair with --cfg 2")
    p.add_argument("--cfg", type=float, default=1.0, help="official default 1.0; 2.0 for dense prompts/small text")
    p.add_argument("--sampler", default="euler")
    p.add_argument("--scheduler", default="simple")
    p.add_argument("--transparent", action="store_true",
                   help="wrap the prompt in the official model-card RGBA template")
    p.add_argument("--no-alpha", dest="transparent", action="store_false")
    p.add_argument("--out", default=os.path.join(os.getcwd(), "generated"))
    p.add_argument("--timeout", type=int, default=1800)
    p = sub.add_parser("edit")
    p.add_argument("--image", required=True, help="path to the reference image")
    p.add_argument("--instruction", default=None, help="default: background removal -> RGBA")
    p.add_argument("--negative", default="", help="negative prompt; INACTIVE at cfg<=1")
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--steps", type=int, default=25)
    p.add_argument("--resolution", type=int, default=0, help="pixel budget; 0 = follow reference")
    p.add_argument("--out", default=os.path.join(os.getcwd(), "generated"))
    p.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()
    globals()["PORT"] = a.port
    globals()["SERVER"] = f"http://127.0.0.1:{a.port}"
    {"find": cmd_find, "models": cmd_models, "serve": lambda _: serve(a.port),
     "stop": lambda _: stop(), "t2i": cmd_t2i, "edit": cmd_edit}[a.cmd](a)


if __name__ == "__main__":
    main()
