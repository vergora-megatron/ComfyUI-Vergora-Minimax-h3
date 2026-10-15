# -*- coding: utf-8 -*-
"""Offline self-test for the minimax-h3 node: submit -> poll -> download -> preview,
plus the input rules. No network, no API key, no cost.

Run with any Python that has numpy:  python test_offline.py
"""

import inspect
import base64
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import nodes  # noqa: E402

STATE = {"polls": 0, "payload": None, "headers": None, "get_headers": None,
         "fail_first": 0, "short_downloads": 0}
OUT_DIR = tempfile.mkdtemp(prefix="vergora_minimax_test_")


class FakeFolderPaths:
    @staticmethod
    def get_output_directory():
        return OUT_DIR


def fake_post_json(url, headers, payload, timeout=120):
    STATE["post_url"] = url
    STATE["payload"] = payload
    STATE["headers"] = headers
    return 200, '{"task_info": {"id": "test-task-minimax", "status": "pending"}}'


def fake_get_json(url, headers, timeout=60):
    STATE["get_headers"] = headers
    STATE["polls"] += 1
    if STATE["fail_first"] > 0:
        STATE["fail_first"] -= 1
        return 400, '{"error":{"message":"common.UnmarshalBodyReusable failed"}}'
    if STATE["polls"] < 2:
        return 200, ('{"task_info":{"status":"processing"},'
                     '"data":{"progress":55,"progress_text":"55%"}}')
    return 200, ('{"task_info": {"status": "completed"},'
                 ' "videos": ["https://example.invalid/result_00.mp4"]}')


def fake_download(url, dest_path, timeout=600):
    if STATE["short_downloads"] > 0:
        STATE["short_downloads"] -= 1
        open(dest_path, "wb").close()
        return
    with open(dest_path, "wb") as handle:
        handle.write(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 9000)


def setup():
    nodes.http_post_json = fake_post_json
    nodes.http_get_json = fake_get_json
    nodes.http_download = fake_download
    nodes.folder_paths = FakeFolderPaths()
    nodes.load_config = lambda: {
        "base_url": "https://api.vergora.ai/v1",
        "api_key": "sk-test",
        "poll_interval": 0.01,
        "timeout": 30,
        "output_dir": "",
    }
    return nodes.VergoraMinimaxH3Video()


def run_case(node, **kwargs):
    out = node.run(**kwargs)
    return out, (out.get("result") if isinstance(out, dict) else out)


def expect_error(node, needle, **kwargs):
    try:
        run_case(node, **kwargs)
    except RuntimeError as exc:
        assert needle in str(exc), "expected %r in %r" % (needle, str(exc))
        return
    raise AssertionError("expected RuntimeError containing %r" % needle)


def main():
    node = setup()
    image = np.zeros((64, 96, 3), dtype=np.float32)
    image[:, :, 0] = 1.0
    batch = np.zeros((2, 64, 96, 3), dtype=np.float32)

    # ---- the model is fixed by the package, and the image is required ----
    assert "model" not in node.INPUT_TYPES()["required"], "the model widget is gone by design"
    assert node.INPUT_TYPES()["required"]["resolution"][0] == ["1080p"]
    assert node.INPUT_TYPES()["required"]["ratio"][0] == ["16:9", "9:16", "1:1"]

    # ---- happy path: reference batch plus a prompt ----
    out, result = run_case(node, prompt="Image 1 drifts on a calm lake", resolution="1080p",
                           ratio="16:9", duration=5, audio=False, prompt_extend=True,
                           seed=42, reference_images=batch)
    path, task_id, url = result
    payload = STATE["payload"]
    assert payload["model"] == "minimax-h3", payload
    assert payload["resolution"] == "1080p" and payload["ratio"] == "16:9", payload
    assert payload["duration"] == 5 and payload["audio"] is False, payload
    assert payload["seed"] == 42 and len(payload["reference_images"]) == 2, payload
    assert payload["reference_images"][0].startswith("data:image/"), payload["reference_images"][0][:30]
    assert "Content-Type" not in STATE["get_headers"], STATE["get_headers"]
    assert task_id == "test-task-minimax" and url.endswith("result_00.mp4")
    assert os.path.getsize(path) > 8192, path
    assert nodes.VergoraMinimaxH3Video.OUTPUT_NODE is True
    assert out["ui"]["images"][0]["format"] == "video/mp4", out["ui"]

    # ---- reference image via URL only ----
    run_case(node, prompt="x", resolution="1080p", ratio="9:16", duration=5,
             audio=True, prompt_extend=True, seed=-1, reference_images=batch)
    assert STATE["payload"]["ratio"] == "9:16", STATE["payload"]
    assert "seed" not in STATE["payload"], STATE["payload"]

    # ---- the one rule that matters, checked before submitting ----
    expect_error(node, "必须提供参考图", prompt="x", resolution="1080p", ratio="16:9",
                 duration=5, audio=True, prompt_extend=True, seed=-1)
    assert "必须提供参考图" in node.VALIDATE_INPUTS()
    assert node.VALIDATE_INPUTS(reference_images=["tensor"]) is True
    # the signature must stay narrow: ComfyUI repeats a message once per input it passes
    params = inspect.signature(nodes.VergoraMinimaxH3Video.VALIDATE_INPUTS).parameters
    assert list(params) == ["reference_images"], list(params)
    assert not any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()), \
        "**kwargs would duplicate the message for every widget"
    # the URL field is gone on purpose: one image input keeps the message to a single line
    assert "reference_image_urls" not in node.INPUT_TYPES()["optional"], \
        "a second image input would duplicate the validation message"

    # ---- values only extra_json could push out of range are re-checked ----
    expect_error(node, "只支持", prompt="x", resolution="1080p", ratio="adaptive",
                 duration=5, audio=True, prompt_extend=True, seed=-1,
                 reference_images=batch, extra_json='{"ratio": "4:3"}')
    expect_error(node, "1080p", prompt="x", resolution="1080p", ratio="16:9",
                 duration=5, audio=True, prompt_extend=True, seed=-1,
                 reference_images=batch, extra_json='{"resolution": "720p"}')

    # ---- targeted failure hints for this model ----
    ref_fail = {"task_info": {"status": "failed"},
                "data": {"fail_reason": '{"code":"task_failed","message":"缺少必填参数：ref_image_0"}'}}
    assert "参考图" in nodes.explain_task_failure(ref_fail, "")
    res_fail = {"task_info": {"status": "failed"},
                "data": {"fail_reason": '{"code":"invalid_resolution","message":'
                                        '"model minimax-h3-f does not support resolution 720p"}'}}
    assert "1080p" in nodes.explain_task_failure(res_fail, "")

    # ---- shared robustness: retries, sized downloads, gateway hints ----
    STATE["polls"] = 0
    STATE["fail_first"] = 2
    _, retried = run_case(node, prompt="x", resolution="1080p", ratio="16:9", duration=5,
                          audio=True, prompt_extend=True, seed=-1, reference_images=batch)
    assert os.path.getsize(retried[0]) > 8192

    STATE["polls"] = 0
    STATE["short_downloads"] = 1
    _, recovered = run_case(node, prompt="x", resolution="1080p", ratio="16:9", duration=5,
                            audio=True, prompt_extend=True, seed=-1, reference_images=batch)
    assert os.path.getsize(recovered[0]) > 8192, recovered
    assert not os.path.exists(recovered[0] + ".part")

    nodes.http_post_json = lambda url, headers, payload, timeout=120: (
        503, '{"error":{"code":"model_not_found","message":"No available channel for model '
             'minimax-h3 under group minimax-h3 (distributor)"}}')
    try:
        nodes.submit_task(nodes.load_config(), {"model": "minimax-h3", "prompt": "x"})
    except RuntimeError as exc:
        assert "没有可用通道" in str(exc) and "minimax-h3" in str(exc), exc
    else:
        raise AssertionError("a missing channel should raise")

    nodes.http_post_json = lambda url, headers, payload, timeout=120: (
        402, '{"status":402,"title":"Insufficient balance","detail":"Required: 1000000 amount '
             '(100.0 credits), Available: 750000 amount (75.0 credits)"}')
    try:
        nodes.submit_task(nodes.load_config(), {"model": "minimax-h3", "prompt": "x"})
    except RuntimeError as exc:
        assert "100.0" in str(exc) and "75.0" in str(exc), exc
    else:
        raise AssertionError("an insufficient balance should raise")

    print("OK 全部通过 / all checks passed")
    print("  payload keys :", sorted(payload.keys()))
    print("  node id      :", list(nodes.NODE_CLASS_MAPPINGS))
    print("  saved file   :", path, os.path.getsize(path), "bytes")


if __name__ == "__main__":
    main()
