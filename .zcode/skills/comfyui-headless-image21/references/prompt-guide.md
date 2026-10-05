# Qwen-Image 2.1 — Official Prompt Guide (distilled)

Primary sources (quote-level fidelity kept where marked):

- Model card: https://huggingface.co/Qwen/Qwen-Image-2.1 (official RGBA template quoted below)
- ComfyUI official tutorial: https://docs.comfy.org/tutorials/image/qwen/qwen-image-2-1
- Qwen team blog / GitHub: https://github.com/QwenLM/Qwen-Image

## 1. Text-to-image prompting

- **Order: subject first, then composition, then style/lighting details.** Keep prompts
  concise; the model follows dense prose well but does not need filler.
- **Text rendering**: put the exact on-image text in quotes —
  `"A neon shop sign that reads \"QWEN IMAGE 2.1\", rainy night, reflections on wet pavement"`.
  Text rendering (EN + CN) is a core strength; small text follows the prompt more closely
  at `cfg 2` than at the default `cfg 1` (ComfyUI tutorial).
- Style-tag style also works: `"Astronaut in a jungle, cold color palette, muted colors, detailed, 8k"`.
- Resolution is a total pixel budget (1024 native, up to 2048); showcase quality examples
  use 2048x2048 with ~40 steps. For drafts: 25 steps at 1024.
- Negative prompts do nothing at `cfg 1` (the official path). Raise cfg only if you want
  the negative to act.

## 2. Transparent / RGBA images (official template)

The model card recommends this literal wrapper for transparent output:

> "This is an RGBA image with transparency. A cute cartoon dragon sticker. The image has
> alpha channel and the background is transparent."

i.e. `This is an RGBA image with transparency. <subject>. The image has alpha channel and
the background is transparent.`

Verified locally (ComfyUI 0.37, qwen_image_2.1_int8_convrot, seed 42, 512px):
alpha min 0, ~50% transparent pixels. The decisive tokens are the alpha phrases — prompts
that only say "transparent background" / "sticker" / Chinese 透明背景 produced fully
opaque white backgrounds in a same-seed sweep (see SKILL.md §6).

For converting EXISTING art to transparent, prefer the edit route:
instruction `"Remove the background, and output a PNG image"`.

## 3. Edit instructions (reference-guided generation)

- **Imperative and short beats descriptive prose**: "Change the background to a sunset
  beach", "Remove the background, and output a PNG image", "Make the sword glow blue".
- **Text edits: quote the exact target string** (EN and CN both work):
  `"Change the sign text to read 'GRAND OPENING'"`.
- **Identity preservation phrasing** helps when swapping content onto a subject
  (official tutorial example): "Keep the character and pose in `<image1>` unchanged, put
  this light blue denim shirt from `<image2>` on the character — preserve the original
  facial features, hair, body shape and pose."
- **Localized edits**: "describe the object or region to change and the rest of the image
  is preserved" — no mask needed for a well-named region.
- **Region marking**: paint a colored mark on `image_1` (Mask Editor / Paint Pen), then
  address it by color: "change the jacket in the red area". Two rules from the official
  tutorial: keep the mark *inside* the region you want changed, and state the desired
  color in the prompt as well when the mark's color would otherwise appear in the output.

## 4. Multi-reference (up to 10 images)

- Slots are addressed in text as `<image1>` … `<image10>`; **`image_1` is the image being
  edited; the rest supply content** (official tutorial).
- In API-format JSON the slots are autogrow inputs and MUST use dotted keys:
  `"images.image_1": [<node>, 0]`, `"images.image_2": [<node>, 0]`, … (flat `image_1`
  errors; a nested `"images": {...}` dict is silently dropped — see SKILL.md §5).
- Reference images can differ in size/aspect; the output canvas follows `image_1`.

## 5. Prompt length — what is (and is not) specified

**No official character/token limit has been published** for Qwen-Image 2.1 prompts —
neither the model card nor the ComfyUI tutorial states one. What the local ComfyUI 0.37
implementation actually does (`comfy/text_encoders/qwen_image21.py`):

- Your prompt is wrapped in a chat template: `system: "Comprehend and analyze the
  provided prompt." → user: <your prompt> → assistant:` (a `thinking` mode exists in the
  tokenizer call chain).
- The tokenizer sets no hard truncation (`max_length=99999999` in the Qwen3-VL base) —
  ComfyUI does not clip your prompt; the practical ceiling is the encoder's context
  window. Very long prompts still work but dilute attention; official examples are all
  one-to-three sentences.
- Edit instructions should stay imperative and short regardless (§3).

## 6. Official basic parameters

| Parameter | Official value | Source |
|---|---|---|
| steps | ~40–50 euler for quality; template default 25 | ComfyUI template note |
| cfg | 1.0 default (negative_prompt inactive); raise (e.g. 2) for dense prompts / small text | ComfyUI template + tutorial |
| sampler / scheduler | `euler` / `simple` in all official templates | templates |
| resolution | total pixel budget, native 1024, up to 2048; multiples of 32 | template note |
| shift | **0.69, baked into the model config** (`supported_models.py` `QwenImage21.sampling_settings`) — that is why 2.1 templates need no `ModelSamplingAuraFlow` node | ComfyUI source |
| latent | 64 channels (R/G/B/A × 16), VAE natively RGBA | `comfy/sd.py` |
| references | up to 10; `image_1` is the edit target; canvas follows `image_1` | template note |
| negative_prompt | only effective when cfg > 1 | template note |

## 7. Optional: prompt enhancement

ComfyUI's 2.1 templates ship an optional `refine_prompt` step: a dedicated text encoder
rewrites the prompt before sampling, "turning a short request into a longer, more detailed
one", with a `thinking_mode` toggle and a preview node to inspect the rewritten text.
Off by default; useful for one-word subjects, skip it when you need exact wording control.
