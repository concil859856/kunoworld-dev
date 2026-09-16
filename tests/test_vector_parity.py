"""Both repos carry the protocol vectors so each can be tested standalone; they must
never drift. Regenerate with `uv run python subnet/protocol/tests/make_vectors.py`."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPIES = [ROOT / "subnet" / "protocol" / "tests" / "vectors.json", ROOT / "sdk" / "js" / "test" / "vectors.json"]


def test_the_two_vector_copies_are_identical():
    contents = [path.read_bytes() for path in COPIES]
    assert all(path.exists() for path in COPIES), "run make_vectors.py"
    assert contents[0] == contents[1], "vectors.json copies differ — regenerate them"


def test_the_websites_model_catalog_is_the_protocols():
    """platform/web renders /models, the studio and /llms-full.txt from its copy of profiles.json; it went stale once
    (the measured VCU weights and verified-mode classes were missing). Copy the protocol's file over it after a change."""
    protocol = ROOT / "subnet" / "protocol" / "src" / "kuno_protocol" / "profiles.json"
    website = ROOT / "platform" / "web" / "lib" / "profiles.json"
    assert website.read_bytes() == protocol.read_bytes(), "cp subnet/protocol/src/kuno_protocol/profiles.json platform/web/lib/profiles.json"


def test_both_copies_of_the_endorsement_vectors_are_identical():
    copies = [ROOT / "subnet" / "protocol" / "tests" / "endorsement_vectors.json", ROOT / "sdk" / "js" / "test" / "endorsement_vectors.json"]
    assert copies[0].read_bytes() == copies[1].read_bytes(), "regenerate with make_endorsement_vectors.py"
