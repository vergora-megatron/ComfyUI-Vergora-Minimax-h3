# ComfyUI Vergora Minimax H3 Video

A ComfyUI custom node that generates video with **minimax-h3** through the Vergora API. It is a
separate package from [ComfyUI-Vergora-Wan3](https://github.com/vergora-megatron/ComfyUI-Vergora-Wan3)
because the two models do not share a contract: minimax-h3 is image-driven and accepts only three
ratios. Both packs can be installed side by side.

- **Model:** `minimax-h3`, fixed by the package.
- **Input:** one or more reference images (an `IMAGE` batch or URLs) plus a prompt.
- **Verified on:** ComfyUI 0.40.0 (frontend 1.55.17), Python 3.13, Windows 11.

## What this model accepts

These limits come from testing the channel behind `minimax-h3` (2026-10-15). They are baked into the
widgets, so you cannot accidentally pick a value the upstream will reject.

| Setting | Accepted | Notes |
| --- | --- | --- |
| Reference image | required | Text-only jobs fail with `缺少必填参数：ref_image_0`; the node refuses them locally |
| `resolution` | `720p`, `1080p` | `1080p` is the default |
| `ratio` | `16:9`, `9:16`, `1:1` | There is no `adaptive` on this channel |
| `duration` | 2 to 30 seconds, or `-1` | `-1` asks the service to pick the length |
| `audio`, `prompt_extend`, `seed` | as in the W3.0 pack | `seed = -1` means "let the service choose" |

The reference image is connected as an `IMAGE`; a batch of up to 10 is fine. It is deliberately the
only image input: sending a URL instead would make the upstream fetch that URL, which fails whenever
the link stops resolving (`4002 Failed to download file`), and a second image input would also make
ComfyUI print the validation message once per input. Use a `LoadImage` node or the output of an
image generation node. `reference_video_urls` and `reference_audio_urls` exist because the channel's
request body has `videos` / `audios` fields, but they have not been exercised yet.

## Requirements

- ComfyUI (developed against 0.40.0)
- A Vergora API key
- No extra pip packages: the HTTP layer uses `requests` when present and falls back to the standard
  library otherwise.

## Installation

1. Copy this folder into ComfyUI's `custom_nodes` directory.
2. Create the configuration from the template and add your key:
   - Windows: `copy config.ini.example config.ini`
   - macOS / Linux: `cp config.ini.example config.ini`

   ```ini
   [API]
   BASE_URL = https://api.vergora.ai/v1
   KEY = sk-your-key-here
   ```
   Every setting is documented inside `config.ini.example`. The environment variables
   `VERGORA_BASE_URL` and `VERGORA_API_KEY` override the file.
3. Restart ComfyUI and add **vergora minimax-h3 视频生成（参考图）** from the `vergora` category
   (search for `minimax`).

`config.ini` is gitignored, so your key never reaches the repository.

## Node reference

Node id: `VergoraMinimaxH3Video`
Category: `vergora`

| Input | Type | Default | Notes |
| --- | --- | --- | --- |
| `prompt` | STRING (multiline) | empty | What should happen in the clip; address inputs as `Image 1`, `Video 1` |
| `resolution` | COMBO | `1080p` | `720p` or `1080p` |
| `ratio` | COMBO | `16:9` | `16:9`, `9:16` or `1:1` |
| `duration` | INT | 5 | `-1` for smart duration, otherwise 2 to 30 seconds |
| `audio` | BOOLEAN | true | Whether the clip carries an audio track |
| `prompt_extend` | BOOLEAN | true | Let upstream rewrite the prompt |
| `seed` | INT | -1 | `-1` means "do not send a seed" |
| `reference_images` | IMAGE (optional) | - | Required in practice: the reference image(s); a batch of up to 10 works |
| `reference_video_urls` | STRING (multiline, optional) | empty | Reference videos, one URL per line (untested) |
| `reference_audio_urls` | STRING (multiline, optional) | empty | Reference audio, one URL per line (untested) |
| `extra_json` | STRING (multiline, optional) | empty | Extra request fields, merged last |

Outputs: `video_path` (local `.mp4`), `task_id`, `video_url`. The clip also appears in ComfyUI's
result panel, and the node registers as an output node.

## Usage

**Reference image to video.** Connect an `IMAGE` (a `LoadImage` node, an image-generation node, or a
batch) to `reference_images`, write what should happen in `prompt`, and press Run. The console prints
the submit call and one status line per poll, including the upstream's own progress percentage.

**Ready-made workflow.** Load `examples/minimax-h3-reference.json` (Workflow → Open): it wires a
`LoadImage` node into `reference_images` and already selects `1080p` / `16:9`. Pick any image of your
own and press Run.

## Cost

`minimax-h3` is billed **per request**, not per second, so changing `resolution` or `duration` does
not change the price of a successful job. The Vergora catalog listed it at 1.365 USD per request
(70% discount) when this package was written; confirm the current rate in your console. Failed jobs
are not billed.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `minimax-h3 必须提供参考图` (shown as invalid input, exactly one line) | Nothing is connected to `reference_images`. Wire a `LoadImage` node or an image generation node into it |
| `没有配置 API key` | `KEY` is empty in `config.ini` and `VERGORA_API_KEY` is not set |
| `503 No available channel for model minimax-h3` | This key has no channel for the model; ask the platform to enable it |
| `402 Insufficient balance` | The request costs more credits than the account holds; the message states both amounts |
| `invalid_resolution` in a task failure | The channel rejected the resolution. Use `720p` or `1080p`; clear any other `resolution` override in `extra_json` |
| `4002 Failed to download file` | The upstream could not fetch a reference URL. Use an `IMAGE` input (sent as Base64) or a stable public URL |
| `413 Request Entity Too Large` | Inline images exceeded the gateway body limit. The node budgets and compresses automatically; otherwise ask the platform to raise `client_max_body_size` |
| `SSLError` / `UNEXPECTED_EOF_WHILE_READING` | A dropped TLS connection, usually a local proxy or VPN. Submits are not retried automatically (a duplicate could be billed twice) — press Run again |
| The job completes but the file is 0 bytes | The CDN dropped the transfer; the node verifies and retries three times, then reports the video URL so you can fetch it by hand |

## Development

`python test_offline.py` runs the whole flow (submit → poll → download → preview) plus the input
rules against a stub HTTP layer. It needs no network, no key and spends nothing.

## License

MIT. See `LICENSE`.

---

# 中文说明

**ComfyUI Vergora minimax-h3 视频节点**：通过 Vergora API 调用 **minimax-h3** 生成视频。它与
Wan 3.0 不是同一套契约，所以单独成包（Wan 3.0 见 ComfyUI-Vergora-Wan3），两个包可以同时安装。

**这个模型的硬约束**（2026-10-15 实测，已固化到控件里）

- **必须给参考图**：纯文本会失败（上游报 `缺少必填参数：ref_image_0`），节点会在提交前拦下并提示
- **分辨率支持 720p / 1080p**：默认 1080p；已有工作流保持原分辨率
- **画幅只有 16:9 / 9:16 / 1:1**：这个通道没有 `adaptive`
- 时长 2–30 秒或 `-1`（智能时长）；`audio`、`prompt_extend`、`seed` 与 Wan3 包一致

**安装**：整个文件夹放进 `custom_nodes` → 把 `config.ini.example` 复制成 `config.ini` 并填上 `KEY`
→ 重启 ComfyUI → 在 `vergora` 分类下添加「vergora minimax-h3 视频生成（参考图）」。
也可以用环境变量 `VERGORA_API_KEY`；`config.ini` 已被 gitignore，不会提交密钥。

**用法**：把图片接到 `reference_images`（支持一批，最多 10 张），填好 `prompt`，点运行；
参考图**只能用 IMAGE 接进来**（`LoadImage` 或出图节点都可以，一批最多 10 张）。这里刻意不提供
"填图片链接"的输入：一是链接要由上游自己去抓，链接一失效就会以 `4002 Failed to download file`
失败；二是多一个图片输入会让 ComfyUI 把校验提示重复打印多次。想用现成图片文件，就用 `LoadImage`。
开箱即用的工作流在 `examples/minimax-h3-reference.json`，加载后换一张自己的图即可。

**计费**：按**请求**计费（不是按秒），改分辨率或时长都不影响价格；撰写本包时目录价 1.365 美元/次
（70% 折扣），以控制台当日价格为准。失败任务不计费。

**自测**：`python test_offline.py`，用假 HTTP 层跑通全流程与输入校验，不联网、不花钱、不需要密钥。
