"""A complete local network per test: gateway, mock-TEE workers and SDK clients."""

from __future__ import annotations

import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import uvicorn

from kuno_gateway.app import create_app
from kuno_gateway.settings import Settings
from kuno_protocol import devkit
from kuno_protocol.attestation import GoldenManifest, MockTEE
from kuno_protocol.canonical import b64d
from kuno_protocol.crypto import signing_key_from_bytes
from kuno_worker.backends.mock import MockBackend, _ffmpeg
from kuno_worker.config import WorkerConfig
from kuno_worker.worker import Worker
from kunoworld import KunoClient


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class Network:
    url: str
    env: dict[str, str]
    data_dir: Path
    stop: threading.Event
    workers: list[Worker] = field(default_factory=list)

    def start_worker(self, profiles: list[str], hotkey: str = "5MinerHotkey01", image_digest: str = devkit.DEV_IMAGE_DIGEST) -> Worker:
        quote_key = signing_key_from_bytes(b64d((self.data_dir / "mock_quote.key").read_text()))
        config = WorkerConfig(
            gateway_url=self.url,
            profiles=profiles,
            image_digest=image_digest,
            miner_hotkey=hotkey,
            pull_wait_s=1.0,
        )
        worker = Worker(config, MockTEE(quote_key, image_digest), {"*": MockBackend()})
        threading.Thread(target=worker.run, args=(self.stop,), daemon=True).start()
        assert worker.ready.wait(10), "worker failed to register"
        self.workers.append(worker)
        return worker

    def client(self, country: str = "JP", key: str | None = None) -> KunoClient:
        manifest = GoldenManifest.model_validate_json((self.data_dir / "manifest.json").read_text())
        return KunoClient(key or self.env["KUNO_DEV_API_KEY"], self.url, manifest=manifest, country=country)

    def owner_key(self):
        return signing_key_from_bytes(b64d((self.data_dir / "owner.key").read_text()))


@pytest.fixture
def network(tmp_path: Path):
    data_dir = tmp_path / "data"
    env = devkit.init(data_dir)
    settings = Settings.from_env({"KUNO_DATA_DIR": str(data_dir)})
    settings.allow_country_override = True
    settings.pull_wait_s = 2.0
    settings.janitor_interval_s = 0.5
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(create_app(settings), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started:
        assert time.time() < deadline, "gateway failed to start"
        time.sleep(0.05)
    net = Network(url=f"http://127.0.0.1:{port}", env=env, data_dir=data_dir, stop=threading.Event())
    yield net
    net.stop.set()
    server.should_exit = True
    thread.join(10)


@pytest.fixture(scope="session")
def sample_audio(tmp_path_factory) -> bytes:
    """Two seconds of tone, for audio-to-video and audio references."""
    path = tmp_path_factory.mktemp("media") / "tone.wav"
    subprocess.run(
        [_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "sine=frequency=440:sample_rate=48000:duration=2", "-ac", "2", str(path)],
        check=True,
    )
    return path.read_bytes()


@pytest.fixture(scope="session")
def sample_video(tmp_path_factory) -> bytes:
    """A short clip, for edit, extend and retake."""
    path = tmp_path_factory.mktemp("media") / "clip.mp4"
    subprocess.run(
        [_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x176:rate=24:duration=2",
         "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000:duration=2", "-c:v", "libx264", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)],
        check=True,
    )
    return path.read_bytes()


@pytest.fixture(scope="session")
def images(tmp_path_factory) -> dict[str, bytes]:
    """Two small solid-color PNGs made with ffmpeg."""
    out = tmp_path_factory.mktemp("images")
    result = {}
    for name, color in (("red", "red"), ("blue", "blue")):
        path = out / f"{name}.png"
        subprocess.run(
            [_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color={color}:s=320x180", "-frames:v", "1", str(path)],
            check=True,
        )
        result[name] = path.read_bytes()
    return result
