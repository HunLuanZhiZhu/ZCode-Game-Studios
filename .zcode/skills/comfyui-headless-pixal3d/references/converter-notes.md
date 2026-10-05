# Converter notes — ComfyUI UI-template → API-format, Pixal3D/TRELLIS.2 edition

Everything in this file was learned by actually breaking and fixing a run on 2026-10-05
(4 attempts; the first "succeeded" in 5 s without producing a model). Read this before
editing `convert()` in `scripts/comfy3d.py` or hand-editing anything in `workflows/*.json`.

## Why a converter exists

Official templates (`comfyui_workflow_templates_json/templates/*.json`) are UI format
(`nodes`/`links`, LiteGraph). `POST /prompt` needs API format
(`{ "<node_id>": {"class_type": ..., "inputs": {...}} }`). The ComfyUI frontend does this
conversion client-side when you press Queue; headless has to do it itself.

## Widget-spec formats (object_info)

An input is a WIDGET (its value comes from `widgets_values`) iff:

1. `["INT", {...}]` / `["FLOAT", {...}]` / `["STRING", {...}]` / `["BOOLEAN", {...}]`
2. `["COMBO", {"options": [...]}]` (v3 style, e.g. `LoadMoGeModel.model_name`)
3. `[["opt1", "opt2", ...]]` or `[["opt1",...], {"advanced": true}]`
   (classic combo, e.g. `KSampler.sampler_name`, `UNETLoader.unet_name`)
4. `["COLOR", {"default": "#000000", "socketless": true}]` — any type with a `default` or
   `options` in its options-dict (`ImageCropToMask.background`)

Everything else is a LINK input: `["MODEL", {}]`, `["MODEL", {"tooltip": ...}]`,
`["LOAD_3D", {}]`, `["FILE_3D_GLB,FILE_3D_GLTF,...", {...}]` (union types are one string),
`["COMFY_MATCHTYPE_V3", {...}]` (lazy switch inputs). The discriminator: **link specs carry
no `default` and no `options`**. `["MODEL"]` (bare, single upper-case string) is also a link.

## control_after_generate eats an extra widgets_values slot

`KSampler` widgets_values = `[seed, "fixed", steps, cfg, sampler, scheduler, denoise]` but
object_info order is `seed, steps, cfg, sampler_name, scheduler, denoise`. When the value
for an INT/FLOAT input is one of `fixed/increment/decrement/randomize`, it is the PREVIOUS
widget's companion — consume the next array value instead. Same for `PrimitiveInt.value`.

## COMFY_DYNAMICCOMBO_V3 (RemeshMesh.sign_mode, DecimateMesh.placement_mode)

A dynamic combo stores `[...base widgets..., <selected key>, <dynamic sub-widget values...>]`
in widgets_values — the sub-widget values make naive pointer mapping misalign every input
after it. Two-part fix:

1. Map the selected key normally, then submit each sub-input as a **dotted key**
   (`"sign_mode.qef"`, `"sign_mode.drop_inverted_components"`, ...). Which sub-inputs are
   required depends on the selected option: spec options are a list of dicts
   `{"key": "udf", "inputs": {"required": {"qef": ["BOOLEAN", {"default": false}], ...}}}`.
   The selected option's sub-inputs are REQUIRED server-side — omitting them fails
   validation. Auto-fill from each sub-spec's `default` (that is what the UI sends anyway).
2. `OVERRIDES` in comfy3d.py patches the two fields the misalignment gets wrong
   (`RemeshMesh` id 241 in both Pixal3D templates: `smooth_iters: 20`,
   `drop_small_components: 0.01`; everything else falls back to spec defaults which match).
   Node ids are stable per template file but check them after a template update.

`DecimateMesh` with `placement_mode="midpoint"` has NO sub-inputs (only the `qem` option
does) — that is why it validates without overrides.

## Save3DAdvanced / Preview3DAdvanced / MeshToFile3D

- `Save3DAdvanced` is the ONLY `output_node` in the pipeline (`MeshToFile3D` is NOT, despite
  its name — it merely produces the File3D that Save3DAdvanced consumes and writes).
- `viewport_state` (type `LOAD_3D`) is a REQUIRED input on Save3D/Preview3D nodes. The UI
  serializes the whole 3D viewport into it. Server-side `execute_save_3d_advanced` does
  `viewport_state if isinstance(viewport_state, dict) else {}` — so **submitting the string
  `"{}"` passes validation and is safe**.
- `Preview3DAdvanced` nodes are dropped entirely by the converter (`DROP_TYPES`): they are
  viewport-only previews and each carries its own viewport_state problem. Dropping output
  nodes is safe as long as `Save3DAdvanced` remains.

## Combo options are dynamic — never validate membership statically

`LoadImage.image` options are the files in the (server-configured) input dir; a cached
`/object_info` dump taken with a different `--input-directory` will not contain your file.
Converters must accept any scalar for combo inputs and let the server re-validate.

## The "fake success" signature and the three gates

`POST /prompt` returns HTTP 200 + prompt_id even when nodes are invalid; invalid nodes are
dropped, their dependent outputs silently ignored, and execution "completes" in seconds with
only unrelated preview nodes run. Server log shows `* <Class> <id>:` validation reasons and
`Output will be ignored`. Gates that catch it (all three are in comfy3d.py run()):

1. `resp["node_errors"]` from `/prompt` non-empty → abort before polling.
2. Execution status `error` → abort with the status dump.
3. Completed but no `.glb/.gltf/.fbx/.obj` in outputs → abort (gate 3 is what actually
   caught the first fake success, since the partial run also returned `status: success`).

## Weights and the traffic-quota rule

hf-mirror.com 308-redirects `/resolve/` to huggingface.co, which 302s to
`us.aws.cdn.hf.co` (CloudFront; observed `x-hf-cdn-pop: aws-eu-west-3`). Domain name is
meaningless — only the FINAL byte-serving host matters. ModelScope mirrors Comfy-Org 1:1
(same file trees, verified 2026-10-05) and serves 200 directly from `www.modelscope.cn`.
`curl -sIL <url> -o /dev/null -w "%{url_effective}\n"` before any bulk download. A 0.7 GB
lesson was paid for this already.

## Blender verification traps

- The default startup scene's 2 m Cube encloses a generated ~0.8 m asset: renders and
  viewport captures show only the cube's shell. Delete `Cube` before judging anything.
- Blender 5.2 + blender-mcp `get_screenshot_of_area_as_image` returns an all-black image
  even when the viewport is correctly framed (scene state verified fine). Use a temp camera
  + sun + `bpy.ops.render.render(write_still=True)` (640 px, EEVEE, ~3 s) as the check.

## Reference timings (single consumer GPU, dynamic-VRAM streaming, 2026-10-05)

- Single-image (1024² transparent corgi PNG): 241 s end-to-end, 48.7 MB GLB,
  699,329 faces (DecimateMesh cap 700k), 1 baked PBR material.
- Multi-view (6336×2688 turnaround strip, 4 reference-guided views): ~6.5 min end-to-end,
  48.0 MB GLB, 698,693 faces. 4-azimuth Blender check: front face present, back face
  ABSENT (reconstructed from the back view — the single-image route cannot do this),
  left/right consistent. The template saves its four crops as
  `front_view/back_view/left_view/right_view_*.png` — use them to debug panel order.
- The multiview template's `ImageCropV2` boxes are FIXED pixels sized to its example sheet:
  x=0/1652/3182/4728, width 1669/1492/1476/1608, height 2688 (total 6336×2688). A sheet of
  any other geometry gets cropped wrong; compose with make_turnaround_strip.py.
- Weights on disk: 8 files, 19.4 GiB (both templates' union).
- Cold server start to ready: ~16 s; object_info ~1010 classes / 2 MB JSON.
- VRAM contention rule: running a 2D server (Qwen 2.1, port 8188) at the same time as the
  3D server (port 8189) doubles the resident model footprint — if that exceeds VRAM, the 3D
  run OOMs or crawls. Stop the idle server before a 3D run. Timings above are a reference
  point; they scale with GPU, free VRAM, and storage speed.
