#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
comfy3d.py -- headless ComfyUI client for image-to-3D game assets (Pixal3D + TRELLIS.2). Stdlib only.

Subcommands:
  find                       Check the 8 weights against registered model dirs (no server needed)
  download [--only NAME]     Download missing weights from ModelScope (DOMESTIC source, resumable)
  run   --template image     Single image -> textured GLB  (3d_pixal3d_trellis2_image_to_model)
        --template multiview 4-view turnaround sheet -> GLB (3d_pixal3d_multi_views)
        [--image PATH] [--seed N] [--out DIR] [--port 8189] [--timeout 2700] [--keep-server]
  convert --template NAME    Regenerate workflows/<name>_api.json from the official UI template
        [--object-info PATH] (offline, uses a cached GET /object_info dump; maintenance path)

No install paths are hardcoded. Discovery order (identical to the sibling comfyui-headless-image21 skill):
  1. env COMFYUI_HOME (dir containing ComfyUI/main.py or main.py)
  2. %%APPDATA%%/Comfy Desktop/installations.json
  3. shallow scan of common roots for a ComfyUI checkout
Model registrations are read (never assumed) from settings.json modelsDirs,
shared_model_paths.yaml and <code_root>/extra_model_paths.yaml.

WEIGHT SOURCES - the traffic-quota rule:
  hf-mirror.com is a FAKE domestic source for newer (xet-backed) repos: it 308-redirects to
  huggingface.co which 302s to us.aws.cdn.hf.co (AWS international CDN). Bytes served from
  abroad count against the user's 100 GB/month international quota. ModelScope (modelscope.cn,
  Alibaba) mirrors Comfy-Org 1:1 and serves bytes from China. `download` verifies the final
  byte-serving host before every transfer and aborts if it is not modelscope.cn.
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
PORT = 8189
SERVER = f"http://127.0.0.1:{PORT}"

# ComfyUI folder-type -> file name(s), plus the ModelScope repo each file lives in.
# "used-by": image = single-image template, mv = multi-view template.
WEIGHTS = {
    ("diffusion_models", "pixal3d_int8_convrot.safetensors"):            {"gib": 5.20, "used": "image", "repo": "Comfy-Org/Pixal3D"},
    ("diffusion_models", "pixal3d_multiview_int8_convrot.safetensors"):  {"gib": 5.20, "used": "mv",    "repo": "Comfy-Org/Pixal3D"},
    ("diffusion_models", "trellis_2_int8_convrot.safetensors"):          {"gib": 4.89, "used": "image", "repo": "Comfy-Org/TRELLIS.2"},
    ("vae", "trellis_2_shape_vae_bf16.safetensors"):                     {"gib": 1.02, "used": "both",  "repo": "Comfy-Org/Pixal3D"},
    ("vae", "trellis_2_texture_vae_bf16.safetensors"):                   {"gib": 0.88, "used": "both",  "repo": "Comfy-Org/Pixal3D"},
    ("clip_vision", "dino_v3_L_naf_fp32.safetensors"):                   {"gib": 1.13, "used": "both",  "repo": "Comfy-Org/Pixal3D"},
    ("geometry_estimation", "moge_2_vitl_normal_fp16.safetensors"):      {"gib": 0.62, "used": "image", "repo": "Comfy-Org/MoGe"},
    ("background_removal", "birefnet.safetensors"):                      {"gib": 0.41, "used": "both",  "repo": "Comfy-Org/BiRefNet"},
}
MS_URL = "https://www.modelscope.cn/models/{repo}/resolve/master/{path}"
TEMPLATES = {
    "image": "3d_pixal3d_trellis2_image_to_model.json",
    "multiview": "3d_pixal3d_multi_views.json",
}
WORKFLOWS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workflows")

# ---- converter constants (see references/converter-notes.md for the full story) ----
SKIP_TYPES = {"Note", "MarkdownNote"}
DROP_TYPES = {"Preview3DAdvanced"}                 # viewport-only; Save3DAdvanced is the real sink
WIDGET_KINDS = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO", "COMFY_DYNAMICCOMBO_V3"}
CTRL_WORDS = {"fixed", "increment", "decrement", "randomize"}
# Dynamic-combo sub-widgets cannot be expressed in UI widgets_values: after the selected key,
# the remaining array entries are junk. Only the two fields the pointer map gets wrong need
# overrides (smooth_iters / drop_small_components); sign_mode sub-keys are auto-filled.
OVERRIDES = {
    "241": {"smooth_iters": 20, "drop_small_components": 0.01},   # RemeshMesh, both templates
}
CLASS_EXTRAS = {"Save3DAdvanced": {"viewport_state": "{}"}}


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
    code_root = python_exe = None
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
        sys.exit("[FATAL] No ComfyUI checkout found. Set COMFYUI_HOME and retry.")
    for p in [os.path.join(code_root, ".venv", "Scripts", "python.exe"),
              os.path.join(code_root, ".venv", "bin", "python"),
              os.path.join(os.path.dirname(code_root), ".venv", "Scripts", "python.exe")]:
        if os.path.isfile(p):
            python_exe = p
            break
    if python_exe is None:
        log("warn: no bundled .venv python found; falling back to sys.executable")
        python_exe = sys.executable

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
    return {"code_root": code_root, "python_exe": python_exe, "model_dirs": model_dirs,
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


def final_host(url, timeout=30):
    """HEAD the url following redirects; return the host that would serve the bytes."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    final_url = resp.geturl()
    resp.close()
    return urllib.parse.urlparse(final_url).netloc


# ---------------------------------------------------------------- weights

def registered_dirs_for(folder, d):
    return [os.path.join(md, folder) for md in d["model_dirs"]
            if os.path.isdir(os.path.join(md, folder))]


def find_weights(d):
    ok = 0
    total = 0.0
    for (folder, name), meta in WEIGHTS.items():
        hit = None
        for dr in registered_dirs_for(folder, d):
            p = os.path.join(dr, name)
            if os.path.isfile(p):
                hit = p
                break
        if hit:
            ok += 1
            total += os.path.getsize(hit) / 2**30
            log(f"OK   {folder}/{name}  ({os.path.getsize(hit) / 2**30:.2f} GiB)  {hit}")
        else:
            log(f"MISS {folder}/{name}  (~{meta['gib']:.2f} GiB, used by: {meta['used']})")
            log(f"     -> python {os.path.abspath(__file__)} download --only {name}")
    log(f"{ok}/{len(WEIGHTS)} weights present ({total:.1f} GiB on disk)")
    return ok == len(WEIGHTS)


def _domestic_check(url):
    host = final_host(url)
    if not host.lower().endswith("modelscope.cn"):
        raise RuntimeError(f"REFUSING to download: {url} ultimately serves bytes from '{host}' "
                           f"(international traffic). Expected modelscope.cn.")
    return host


def download_weights(d, only=None):
    todo = {k: v for k, v in WEIGHTS.items() if only is None or k[1] == only}
    for (folder, name), meta in todo.items():
        dirs = registered_dirs_for(folder, d)
        dest_dir = dirs[0] if dirs else None
        if dest_dir is None:
            sys.exit(f"[FATAL] No registered dir for '{folder}'. Add the model root to "
                     f"<code_root>/extra_model_paths.yaml first (see SKILL.md section 3), "
                     f"or pass a registered root.")
        dest = os.path.join(dest_dir, name)
        if os.path.isfile(dest) and os.path.getsize(dest) > 1024 * 1024:
            log(f"SKIP {name}: already present ({os.path.getsize(dest) / 2**30:.2f} GiB)")
            continue
        url = MS_URL.format(repo=meta["repo"], path=f"{folder}/{name}")
        host = _domestic_check(url)
        log(f"download {name} (~{meta['gib']:.2f} GiB) via {host}")
        expect = meta["gib"] * 2**30
        for attempt in range(1, 6):
            try:
                done = os.path.getsize(dest) if os.path.isfile(dest) else 0
                req = urllib.request.Request(url)
                if done:
                    req.add_header("Range", f"bytes={done}-")
                with urllib.request.urlopen(req, timeout=120) as r, open(dest, "ab" if done else "wb") as f:
                    while True:
                        chunk = r.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                sz = os.path.getsize(dest)
                log(f"attempt {attempt}: done, {sz / 2**30:.2f} GiB on disk")
                if sz >= expect * 0.999:
                    break
            except Exception as e:
                log(f"attempt {attempt} failed: {e}; retrying in 10s")
                time.sleep(10)
        else:
            sys.exit(f"[FATAL] {name}: 5 attempts failed; rerun the same command to resume.")
        log(f"DONE {name}")
    find_weights(d)


# ---------------------------------------------------------------- converter
# Full rationale in references/converter-notes.md. Key rules:
#  * widget specs: ["INT"/"FLOAT"/"STRING"/"BOOLEAN", {..}] | ["COMBO", {options}] |
#    [["opt","opt"]] | ["COLOR",{default..,"socketless":true}] - link types carry NO default/options
#  * KSampler-style seeds carry an extra control_after_generate value ("fixed") in widgets_values
#  * COMFY_DYNAMICCOMBO_V3: selected option's sub-inputs must be submitted as dotted keys
#  * Save3D*/Load3D-family require viewport_state; "{}" is accepted server-side
#  * combo options are dynamic (directory listings) - never validate membership statically

def is_widget_spec(spec):
    if isinstance(spec, list) and spec:
        t = spec[0]
        if isinstance(t, list):
            return True
        if isinstance(t, str) and t in WIDGET_KINDS:
            return True
        if isinstance(t, str):
            if len(spec) > 1 and isinstance(spec[1], dict):
                d = spec[1]
                return "default" in d or "options" in d
            if len(spec) == 1:
                return not t.isupper()
    return False


def spec_kind(spec):
    if isinstance(spec, list) and spec and isinstance(spec[0], str):
        return spec[0]
    return "COMBO"


def spec_default(spec):
    if isinstance(spec, list) and len(spec) > 1 and isinstance(spec[1], dict):
        return spec[1].get("default")
    if isinstance(spec, dict):
        return spec.get("default")
    return None


def value_ok(v, spec):
    k = spec_kind(spec)
    if k == "INT":
        if isinstance(v, bool):
            return False
        if isinstance(v, int):
            return True
        if isinstance(v, str):
            try:
                int(v); return True
            except ValueError:
                return False
        return False
    if k == "FLOAT":
        if isinstance(v, bool):
            return False
        if isinstance(v, (int, float)):
            return True
        if isinstance(v, str):
            try:
                float(v); return True
            except ValueError:
                return False
        return False
    if k == "BOOLEAN":
        return isinstance(v, bool)
    if k == "STRING":
        return isinstance(v, str)
    if k in ("COMBO", "COMFY_DYNAMICCOMBO_V3"):
        return isinstance(v, str) or (isinstance(v, (int, float)) and not isinstance(v, bool))
    return True


def coerce(v, spec):
    k = spec_kind(spec)
    if k == "INT" and isinstance(v, str):
        return int(v)
    if k == "FLOAT" and isinstance(v, str):
        return float(v)
    return v


def fill_dynamic_combo_subinputs(ins, specs, node_id, problems):
    for name, spec in specs.items():
        if spec_kind(spec) != "COMFY_DYNAMICCOMBO_V3":
            continue
        v = ins.get(name)
        if not isinstance(v, str):
            continue
        opts = spec[1].get("options") if isinstance(spec, list) and len(spec) > 1 else None
        opt = next((o for o in (opts or []) if isinstance(o, dict) and o.get("key") == v), None)
        if not opt:
            continue
        for sub, sub_spec in ((opt.get("inputs") or {}).get("required") or {}).items():
            key = f"{name}.{sub}"
            if key in ins:
                continue
            dv = spec_default(sub_spec)
            if dv is None:
                problems.append(f"node {node_id}: dynamic combo sub-input {key} has no default")
            else:
                ins[key] = dv


def convert(wf, objinfo):
    links = {l[0]: (str(l[1]), l[2]) for l in wf["links"]}
    api = {}
    problems = []
    for node in wf["nodes"]:
        ctype = node["type"]
        if ctype in SKIP_TYPES or ctype in DROP_TYPES:
            continue
        info = objinfo.get(ctype)
        if not info:
            problems.append(f"node {node['id']}: class {ctype} not on server")
            continue
        d = info.get("input", {}) or {}
        reqd = d.get("required") or {}
        opt = d.get("optional") or {}
        order = list(reqd) + list(opt)
        specs = {}
        specs.update(reqd)
        specs.update(opt)
        linked = {}
        for e in node.get("inputs", []) or []:
            lk = e.get("link")
            if lk is not None and lk in links:
                on, oslot = links[lk]
                linked[e["name"]] = [on, oslot]
        wv = node.get("widgets_values") or []
        p = 0
        ins = {}
        for name in order:
            spec = specs.get(name)
            if spec is None:
                continue
            if is_widget_spec(spec):
                if name in linked:
                    ins[name] = linked[name]
                    if p < len(wv):
                        p += 1
                    continue
                if p >= len(wv):
                    continue
                v = wv[p]
                p += 1
                if isinstance(v, str) and v in CTRL_WORDS and p < len(wv):
                    v = wv[p]
                    p += 1
                if value_ok(v, spec):
                    ins[name] = coerce(v, spec)
                elif spec_default(spec) is not None:
                    ins[name] = spec_default(spec)
            else:
                if name in linked:
                    ins[name] = linked[name]
        fill_dynamic_combo_subinputs(ins, specs, node["id"], problems)
        if str(node["id"]) in OVERRIDES:
            ins.update(OVERRIDES[str(node["id"])])
        if ctype in CLASS_EXTRAS:
            ins.update(CLASS_EXTRAS[ctype])
        for name, spec in reqd.items():
            if name not in ins and spec_default(spec) is None:
                problems.append(f"node {node['id']} ({ctype}): required input {name} missing without default")
        api[str(node["id"])] = {"class_type": ctype, "inputs": ins, "_meta": {"title": ctype}}
    return api, problems


# ---------------------------------------------------------------- run

def find_template_ui_file(name, d):
    base = os.path.join(d["code_root"], ".venv", "Lib", "site-packages",
                        "comfyui_workflow_templates_json", "templates", TEMPLATES[name])
    return base if os.path.isfile(base) else None


def serve(d, port):
    global PORT, SERVER
    PORT = port
    SERVER = f"http://127.0.0.1:{PORT}"
    if server_up():
        log(f"server already up at {SERVER}, reusing")
        return None
    shared_yaml = os.path.join(DESKTOP_DIR, "shared_model_paths.yaml")
    launch = [d["python_exe"], os.path.join(d["code_root"], "main.py"),
              "--port", str(PORT), "--disable-auto-launch"]
    if os.path.isfile(shared_yaml):
        launch += ["--extra-model-paths-config", shared_yaml]
    if d["input_dir"]:
        launch += ["--input-directory", d["input_dir"], "--output-directory", d["output_dir"]]
    log(f"starting headless server (port {PORT})")
    return subprocess.Popen(launch, cwd=d["code_root"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run(args):
    d = discover()
    wf_path = os.path.join(WORKFLOWS_DIR, f"pixal3d_{'image_to_model' if args.template == 'image' else 'multiview'}_api.json")
    if not os.path.isfile(wf_path):
        sys.exit(f"[FATAL] {wf_path} missing. Regenerate with: convert --template {args.template}")
    api = json.load(open(wf_path, encoding="utf-8"))

    if not os.path.isfile(args.image):
        sys.exit(f"[FATAL] image not found: {args.image}")
    img_name = os.path.basename(args.image)
    if not d["input_dir"]:
        sys.exit("[FATAL] could not discover a ComfyUI input directory")
    dst = os.path.join(d["input_dir"], img_name)
    if os.path.abspath(dst) != os.path.abspath(args.image):
        shutil.copyfile(args.image, dst)
        log(f"input image copied -> {dst}")
    patched = 0
    for nid, nd in api.items():
        if nd["class_type"] == "LoadImage":
            nd["inputs"]["image"] = img_name
            patched += 1
    log(f"patched {patched} LoadImage node(s) -> {img_name}")
    if args.seed is not None:
        for nid, nd in api.items():
            if nd["class_type"] == "KSampler":
                nd["inputs"]["seed"] = args.seed
        log(f"seeds set to {args.seed}")

    proc = serve(d, args.port)
    try:
        ready = False
        for _ in range(120):
            if server_up():
                ready = True
                break
            time.sleep(1)
        if not ready:
            sys.exit("[FATAL] server not ready in 120s")
        if not find_weights(d):
            sys.exit("[FATAL] missing weights - run: python comfy3d.py download")
        try:
            resp = http_json(f"{SERVER}/prompt", {"prompt": api, "client_id": "comfy3d"}, timeout=60)
        except urllib.error.HTTPError as e:
            sys.exit(f"[FATAL] /prompt rejected (HTTP {e.code}): "
                     f"{e.read().decode('utf-8', 'replace')[:4000]}")
        ne = resp.get("node_errors") or {}
        if ne:
            sys.exit(f"[FATAL] node validation errors: {json.dumps(ne)[:4000]}")
        pid = resp["prompt_id"]
        log(f"submitted prompt_id={pid}, no validation errors")
        t0 = time.time()
        last = -60
        while True:
            time.sleep(5)
            el = time.time() - t0
            if el > args.timeout:
                sys.exit(f"[FATAL] timeout {args.timeout}s waiting for result")
            try:
                hist = http_json(f"{SERVER}/history/{pid}", timeout=30)
            except Exception as e:
                log(f"  poll error (retrying): {e}")
                continue
            entry = hist.get(pid)
            if not entry:
                if el - last >= 60:
                    last = el
                    log(f"  running... {el:.0f}s")
                continue
            st = entry.get("status", {})
            if st.get("status_str") == "error":
                sys.exit(f"[FATAL] execution error: {json.dumps(st)[:3000]}")
            if st.get("completed"):
                log(f"execution finished in {el:.0f}s, status={st.get('status_str')}")
                out_dir = args.out or d["output_dir"] or os.getcwd()
                os.makedirs(out_dir, exist_ok=True)
                n_saved = 0
                model = None
                for node_id, outs in (entry.get("outputs") or {}).items():
                    for key, items in outs.items():
                        if not isinstance(items, list):
                            continue
                        for it in items:
                            if not isinstance(it, dict) or not it.get("filename"):
                                continue
                            q = urllib.parse.urlencode({"filename": it["filename"],
                                                        "subfolder": it.get("subfolder", ""),
                                                        "type": it.get("type", "output")})
                            with urllib.request.urlopen(f"{SERVER}/view?{q}", timeout=600) as r:
                                data = r.read()
                            dest = os.path.join(out_dir, it["filename"])
                            with open(dest, "wb") as f:
                                f.write(data)
                            n_saved += 1
                            if it["filename"].lower().endswith((".glb", ".gltf", ".fbx", ".obj")):
                                model = dest
                            log(f"saved: node {node_id} [{key}] -> {dest} ({len(data) / 1048576:.1f} MB)")
                if model is None:
                    sys.exit("[FATAL] completed but NO 3D model file in outputs - "
                             "this is the 'fake success' signature, see references/converter-notes.md")
                log(f"ALL DONE, {n_saved} file(s), model: {model}")
                return
            if el - last >= 60:
                last = el
                log(f"  running... {el:.0f}s")
    finally:
        if proc is not None and not args.keep_server:
            log("stopping server")
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except Exception:
                proc.kill()


def cmd_convert(args):
    if args.object_info:
        objinfo = json.load(open(args.object_info, encoding="utf-8"))
    else:
        d = discover()
        proc = serve(d, PORT)
        try:
            for _ in range(120):
                if server_up():
                    break
                time.sleep(1)
            objinfo = http_json(f"{SERVER}/object_info", timeout=180)
        finally:
            if proc is not None:
                proc.terminate()
    wf = json.load(open(find_template_ui_file(args.template, discover()), encoding="utf-8"))
    api, problems = convert(wf, objinfo)
    for nid, nd in api.items():
        if nd["class_type"] == "LoadImage":
            nd["inputs"]["image"] = "INPUT_IMAGE.png"
    out = args.out or os.path.join(
        WORKFLOWS_DIR, f"pixal3d_{'image_to_model' if args.template == 'image' else 'multiview'}_api.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(api, f, indent=1)
    log(f"converted {len(api)} nodes -> {out}")
    for pr in problems:
        log(f"  PROBLEM: {pr}")
    if problems:
        sys.exit(2)
    log("no conversion problems")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("find", help="check the 8 weights against registered model dirs")
    dp = sub.add_parser("download", help="download missing weights from ModelScope (domestic)")
    dp.add_argument("--only", help="download a single file by name")
    rp = sub.add_parser("run", help="image -> 3D model (GLB)")
    rp.add_argument("--template", choices=["image", "multiview"], default="image")
    rp.add_argument("--image", required=True, help="input image (single image, or 4-view turnaround sheet for multiview)")
    rp.add_argument("--seed", type=int, default=None)
    rp.add_argument("--out", default=None, help="download dir for results (default: discovered ComfyUI output dir)")
    rp.add_argument("--port", type=int, default=8189)
    rp.add_argument("--timeout", type=int, default=2700)
    rp.add_argument("--keep-server", action="store_true")
    cp = sub.add_parser("convert", help="regenerate workflows/*_api.json from the official UI template")
    cp.add_argument("--template", choices=["image", "multiview"], required=True)
    cp.add_argument("--object-info", default=None, help="cached GET /object_info JSON (offline mode)")
    cp.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.cmd == "find":
        find_weights(discover())
    elif args.cmd == "download":
        download_weights(discover(), args.only)
    elif args.cmd == "run":
        run(args)
    elif args.cmd == "convert":
        cmd_convert(args)


if __name__ == "__main__":
    main()
