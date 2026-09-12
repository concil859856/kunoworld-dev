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
