"""The browser SDK and the Python enclave must agree byte-for-byte on HPKE, blobs,
canonical JSON (the AAD) and receipt signatures."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SDK = Path(__file__).resolve().parents[1] / "sdk" / "js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None or not (SDK / "dist" / "index.js").exists(), reason="build sdk/js first")


def test_js_sdk_round_trip_through_python_enclave(network, images, tmp_path):
    network.start_worker(["h3-turbo"])
    image = tmp_path / "first.png"
    image.write_bytes(images["red"])
    out = subprocess.run(
        ["node", str(SDK / "scripts" / "interop.mjs"), network.url, network.env["KUNO_DEV_API_KEY"], str(network.data_dir / "manifest.json"), str(image)],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert out.returncode == 0, out.stderr
    result = json.loads(out.stdout.strip().splitlines()[-1])
    assert result == {"profile": "h3-turbo", "mp4": True, "width": 768, "digestMatches": True, "provenanceValid": True}
