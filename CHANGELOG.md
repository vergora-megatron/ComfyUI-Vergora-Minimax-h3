# Changelog

## 0.2.2 - 2026-10-16

Fixed

- A `404 {"detail":"Not Found"}` now says what it means: the request never reached the gateway's
  route, typically because a local proxy (`HTTP_PROXY` / `HTTPS_PROXY`, a system proxy or a VPN) is
  intercepting it, or because `BASE_URL` is wrong. Suggested fix: `NO_PROXY=api.vergora.ai` or turn
  the proxy off.

## 0.2.1 - 2026-10-15

Fixed

- The missing-image check no longer fires when an image *is* connected. ComfyUI resolves links only
  at execution time, so during validation a wired input arrives as `None` — reading its value made a
  connected image look absent. The check now asks `input_types`, which lists exactly the inputs that
  are wired. Both directions are covered by the offline test.

## 0.2.0 - 2026-10-15

Changed

- The reference image is now the single image input. `reference_image_urls` was removed: URL-based
  reference images make the upstream fetch the link (which fails with `4002 Failed to download file`
  once it expires) and were never verified for this channel, while a second image input also made
  ComfyUI print the validation message once per input. Wire a `LoadImage` node or an image generation
  node into `reference_images` instead.
- The missing-image message is a single line. `VALIDATE_INPUTS` now declares exactly one parameter and
  no `**kwargs`, because ComfyUI repeats a returned message once for every input the function
  receives — the earlier signature produced the same sentence eleven times.

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
