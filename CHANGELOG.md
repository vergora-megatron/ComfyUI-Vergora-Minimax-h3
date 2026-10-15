# Changelog

## 0.1.0 - 2026-10-15

First release, split out of ComfyUI-Vergora-Wan3 because minimax-h3 has its own contract.

- One node, `VergoraMinimaxH3Video`, generating video from one or more reference images plus a
  prompt (the channel is image-driven; a text-only request is refused before submitting).
- Widgets restricted to what the channel actually accepts: `resolution` offers `1080p` only, and
  `ratio` offers `16:9` / `9:16` / `1:1` — there is no `adaptive`.
- `reference_images` takes an IMAGE batch (up to 10), and `reference_image_urls`,
  `reference_video_urls`, `reference_audio_urls` take URLs, one per line.
- The reference-image rule is reported through ComfyUI's input validation, so the message shows up in
  the node's own error panel instead of the generic "node failed" toast.
- Shared robustness with the Wan 3.0 pack: real upstream progress on the canvas, verified downloads
  with retries, inline images budgeted under the gateway body limit, and readable messages for
  quota, missing channel, TLS and 402/413 errors.
