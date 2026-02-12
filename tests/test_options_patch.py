from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from core.codec.options import OptionsSaveCodec
from core.patch.options import OptionsPatchError, apply_options_updates


def _fixture_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "tests" / "fixtures" / "raw" / "smoke_profile_1"


def _make_options_copy(tmp_path: Path) -> Path:
    """Copy options file to temp location."""
    options_file = tmp_path / "persist.options.json"
    src = _fixture_dir().parent.parent / "persist.options.json"
    if src.exists():
        shutil.copy2(src, options_file)
    else:
        # Create minimal options file if source doesn't exist
        options_file.write_text(
            '{"version": 1, "data": {"values": {"language": "english", "subtitles": "on", '
            '"fullscreen": [1], "tutorial": [1], "allow_analytics_and_multiplayer": [0], '
            '"resolution": [1920, 1080]}}}\n'
        )
    return options_file


def test_apply_options_updates_changes_language(tmp_path: Path) -> None:
    options_file = _make_options_copy(tmp_path)
    codec = OptionsSaveCodec()
    parsed = codec.parse(options_file)

    changes = apply_options_updates(parsed, updates={"language": "polish"}, expected={})

    assert len(changes) == 1
    assert changes[0].key == "language"
    assert changes[0].new_value == "polish"
    assert parsed.fields["options.language"].value == "polish"


def test_apply_options_updates_changes_resolution(tmp_path: Path) -> None:
    options_file = _make_options_copy(tmp_path)
    codec = OptionsSaveCodec()
    parsed = codec.parse(options_file)

    changes = apply_options_updates(
        parsed, updates={"resolution_width": 2560, "resolution_height": 1440}, expected={}
    )

    assert len(changes) == 2
    width_change = next(c for c in changes if c.key == "resolution_width")
    height_change = next(c for c in changes if c.key == "resolution_height")
    assert width_change.new_value == 2560
    assert height_change.new_value == 1440


def test_apply_options_updates_validates_expect(tmp_path: Path) -> None:
    options_file = _make_options_copy(tmp_path)
    codec = OptionsSaveCodec()
    parsed = codec.parse(options_file)

    current_language = parsed.fields["options.language"].value

    # Should succeed when expect matches
    changes = apply_options_updates(
        parsed, updates={"language": "german"}, expected={"language": current_language}
    )
    assert changes[0].new_value == "german"


def test_apply_options_updates_rejects_mismatched_expect(tmp_path: Path) -> None:
    options_file = _make_options_copy(tmp_path)
    codec = OptionsSaveCodec()
    parsed = codec.parse(options_file)

    with pytest.raises(OptionsPatchError, match="Current mismatch"):
        apply_options_updates(
            parsed, updates={"language": "german"}, expected={"language": "wrong_value"}
        )


def test_apply_options_updates_rejects_unsupported_key(tmp_path: Path) -> None:
    options_file = _make_options_copy(tmp_path)
    codec = OptionsSaveCodec()
    parsed = codec.parse(options_file)

    with pytest.raises(OptionsPatchError, match="Unsupported or unsafe options key"):
        apply_options_updates(parsed, updates={"unsupported_key": 123}, expected={})


def test_apply_options_updates_rejects_invalid_type(tmp_path: Path) -> None:
    options_file = _make_options_copy(tmp_path)
    codec = OptionsSaveCodec()
    parsed = codec.parse(options_file)

    # Language should be string, not int
    with pytest.raises(OptionsPatchError, match="must be str"):
        apply_options_updates(parsed, updates={"language": 123}, expected={})


def test_apply_options_updates_rejects_empty_updates(tmp_path: Path) -> None:
    options_file = _make_options_copy(tmp_path)
    codec = OptionsSaveCodec()
    parsed = codec.parse(options_file)

    with pytest.raises(OptionsPatchError, match="No options updates provided"):
        apply_options_updates(parsed, updates={}, expected={})


def test_apply_options_updates_changes_fullscreen(tmp_path: Path) -> None:
    options_file = _make_options_copy(tmp_path)
    codec = OptionsSaveCodec()
    parsed = codec.parse(options_file)

    changes = apply_options_updates(parsed, updates={"fullscreen": 0}, expected={})

    assert len(changes) == 1
    assert changes[0].key == "fullscreen"
    assert changes[0].new_value == 0


def test_apply_options_updates_persists_to_raw_bytes(tmp_path: Path) -> None:
    options_file = _make_options_copy(tmp_path)
    codec = OptionsSaveCodec()
    parsed = codec.parse(options_file)

    apply_options_updates(parsed, updates={"language": "french", "fullscreen": 0}, expected={})

    # Write and re-parse
    output_path = tmp_path / "output.options.json"
    codec.write(parsed, output_path)

    reparsed = codec.parse(output_path)
    assert reparsed.fields["options.language"].value == "french"
    assert reparsed.fields["options.fullscreen"].value == 0
