from __future__ import annotations

import json
from pathlib import Path

from cli.main import _parse_manifest_payload


def test_parse_manifest_payload_includes_options_section(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "wallet": {"set": {"gold": 123}},
                "options": {
                    "set": {"language": "english", "fullscreen": 1},
                    "expect": {"language": "german", "fullscreen": 0},
                },
            }
        ),
        encoding="utf-8",
    )

    payload = _parse_manifest_payload(manifest_path)

    options_updates = payload.get("options_updates")
    options_expected = payload.get("options_expected")
    assert isinstance(options_updates, dict)
    assert isinstance(options_expected, dict)
    assert options_updates.get("language") == "english"
    assert int(options_updates.get("fullscreen", -1)) == 1
    assert options_expected.get("language") == "german"
    assert int(options_expected.get("fullscreen", -1)) == 0
