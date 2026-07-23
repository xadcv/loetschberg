"""Release-contract tests for the generated Loetschberg fonts."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
import uharfbuzz as hb
from fontTools import agl
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


ROOT = Path(__file__).resolve().parents[1]
PRIMARY_PATH = ROOT / "Loetschberg-VF[wght,wdth,opsz,slnt].ttf"
SIDECAR_PATH = ROOT / "Loetschberg-Text-VF[wght,wdth,opsz,slnt].otf"
WOFF_PATH = ROOT / "Loetschberg-VF.woff"
WOFF2_PATH = ROOT / "Loetschberg-VF.woff2"
TOPOLOGY_PATH = ROOT / "sources" / "topology-report.json"

ARTIFACTS = (PRIMARY_PATH, SIDECAR_PATH, WOFF_PATH, WOFF2_PATH, TOPOLOGY_PATH)

AXES = {
    "wght": (100.0, 400.0, 900.0),
    "wdth": (75.0, 100.0, 125.0),
    "opsz": (8.0, 12.0, 144.0),
    "slnt": (-12.0, 0.0, 0.0),
}

PALETTE = (
    (0xE2, 0xA2, 0x50, 0xFF),
    (0xB0, 0x7A, 0x41, 0xFF),
    (0x3A, 0x33, 0x2A, 0xFF),
    (0x2A, 0x20, 0x16, 0xFF),
)

# The conventional printable spans exclude the Basic Latin/C1 control ranges
# while retaining spacing and formatting characters needed by real text.
VISIBLE_BASIC_LATIN = set(range(0x20, 0x7F))
VISIBLE_LATIN_1 = set(range(0xA0, 0x100))
REQUIRED_CODEPOINTS = VISIBLE_BASIC_LATIN | VISIBLE_LATIN_1 | {0x0131}


@pytest.fixture(scope="session")
def primary_font() -> TTFont:
    font = TTFont(PRIMARY_PATH, lazy=False)
    yield font
    font.close()


@pytest.fixture(scope="session")
def sidecar_font() -> TTFont:
    font = TTFont(SIDECAR_PATH, lazy=False)
    yield font
    font.close()


def _feature_tags(font: TTFont) -> set[str]:
    feature_list = font["GSUB"].table.FeatureList
    if feature_list is None:
        return set()
    return {record.FeatureTag for record in feature_list.FeatureRecord}


def _assert_axes(font: TTFont) -> None:
    actual = {
        axis.axisTag: (
            float(axis.minValue),
            float(axis.defaultValue),
            float(axis.maxValue),
        )
        for axis in font["fvar"].axes
    }
    assert actual == AXES


def _assert_palette(font: TTFont) -> None:
    palettes = font["CPAL"].palettes
    assert palettes, "CPAL must contain at least the production palette"
    actual = tuple(
        (color.red, color.green, color.blue, color.alpha) for color in palettes[0]
    )
    assert actual == PALETTE


def _cmap_name(font: TTFont, codepoint: int) -> str:
    cmap = font.getBestCmap()
    assert cmap is not None and codepoint in cmap
    return cmap[codepoint]


def _variant_name(font: TTFont, codepoint: int, suffix: str) -> str:
    """Resolve a variant while allowing AGL or uniXXXX production naming."""

    base = _cmap_name(font, codepoint)
    agl_name = agl.UV2AGL.get(codepoint)
    stems = [base]
    if agl_name:
        stems.append(agl_name)
    stems.extend((f"uni{codepoint:04X}", f"u{codepoint:04X}"))
    glyphs = set(font.getGlyphOrder())
    for stem in dict.fromkeys(stems):
        candidate = f"{stem}.{suffix}"
        if candidate in glyphs:
            return candidate
    pytest.fail(f"no .{suffix} variant found for U+{codepoint:04X} ({base})")


def _shape_names(path: Path, font: TTFont, text: str, features: dict[str, bool]) -> list[str]:
    face = hb.Face(path.read_bytes())
    hb_font = hb.Font(face)
    hb.ot_font_set_funcs(hb_font)
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(hb_font, buffer, features)
    return [font.getGlyphName(info.codepoint) for info in buffer.glyph_infos]


def _static_primary(**overrides: float) -> TTFont:
    location = {tag: values[1] for tag, values in AXES.items()}
    location.update(overrides)
    source = TTFont(PRIMARY_PATH, lazy=False)
    try:
        return instantiateVariableFont(source, location, inplace=False)
    finally:
        source.close()


def _recording(font: TTFont, glyph_name: str) -> tuple[Any, ...]:
    pen = RecordingPen()
    font.getGlyphSet()[glyph_name].draw(pen)
    return tuple(pen.value)


def _horizontal_intersections(font: TTFont, glyph_name: str, y: float) -> list[float]:
    """Return unique x crossings through an on-curve glyf outline."""

    glyf = font["glyf"]
    coordinates, end_points, flags = glyf[glyph_name].getCoordinates(glyf)
    assert all(flag & 1 for flag in flags), "H stem probe expects line/on-curve points"

    intersections: list[float] = []
    start = 0
    for end in end_points:
        contour = coordinates[start : end + 1]
        start = end + 1
        for first, second in zip(contour, contour[1:] + contour[:1]):
            x1, y1 = first
            x2, y2 = second
            if (y1 <= y < y2) or (y2 <= y < y1):
                intersections.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))

    intersections.sort()
    unique: list[float] = []
    for value in intersections:
        if not unique or not math.isclose(value, unique[-1], abs_tol=0.01):
            unique.append(float(value))
    return unique


def _left_h_stem(font: TTFont) -> float:
    glyph_name = _cmap_name(font, ord("H"))
    crossings = _horizontal_intersections(font, glyph_name, y=550.5)
    assert len(crossings) >= 4, f"unexpected H intersections: {crossings}"
    return crossings[1] - crossings[0]


def _normalise_key(key: object) -> str:
    return "".join(character for character in str(key).lower() if character.isalnum())


def _negative_value_has_failure(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "none", "ok", "pass", "passed"}
    if isinstance(value, Mapping):
        return any(_negative_value_has_failure(item) for item in value.values())
    if isinstance(value, Sequence):
        return len(value) != 0
    return True


def _topology_signals(report: object) -> tuple[list[str], list[str]]:
    """Find zero-mismatch evidence across common report JSON schemas."""

    signals: list[str] = []
    failures: list[str] = []
    positive_keys = {"ok", "passed", "success", "valid", "compatible"}
    negative_keys = {"errors", "errorcount", "failures", "failurecount", "failed"}
    positive_strings = {"ok", "pass", "passed", "success", "valid", "compatible"}

    def visit(node: object, path: str = "$") -> None:
        if isinstance(node, Mapping):
            for raw_key, value in node.items():
                key = _normalise_key(raw_key)
                item_path = f"{path}.{raw_key}"
                if key in positive_keys:
                    signals.append(item_path)
                    if isinstance(value, bool) and not value:
                        failures.append(item_path)
                    elif isinstance(value, str) and value.strip().lower() not in positive_strings:
                        failures.append(item_path)
                elif (
                    "mismatch" in key
                    or "incompatib" in key
                    or key in negative_keys
                ):
                    signals.append(item_path)
                    if _negative_value_has_failure(value):
                        failures.append(item_path)
                elif key in {"status", "result"} and isinstance(value, str):
                    signals.append(item_path)
                    if value.strip().lower() not in positive_strings:
                        failures.append(item_path)
                visit(value, item_path)
        elif isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
            for index, value in enumerate(node):
                visit(value, f"{path}[{index}]")

    visit(report)
    return signals, failures


def test_expected_root_artifacts_exist() -> None:
    missing = [str(path.relative_to(ROOT)) for path in ARTIFACTS if not path.is_file()]
    assert not missing, f"missing build artifacts: {missing}"


def test_primary_and_sidecar_table_contracts(
    primary_font: TTFont, sidecar_font: TTFont
) -> None:
    common = {"head", "hhea", "maxp", "OS/2", "hmtx", "cmap", "name", "post", "fvar", "HVAR", "STAT", "GSUB"}
    primary_required = common | {"glyf", "loca", "gvar", "COLR", "CPAL"}
    sidecar_required = common | {"CFF2"}

    assert primary_required <= set(primary_font.keys())
    assert {"CFF ", "CFF2"}.isdisjoint(primary_font.keys())
    assert sidecar_required <= set(sidecar_font.keys())
    assert {"glyf", "loca", "gvar", "COLR", "CPAL", "CFF "}.isdisjoint(
        sidecar_font.keys()
    )


@pytest.mark.parametrize("fixture_name", ["primary_font", "sidecar_font"])
def test_variable_axes_and_stat(request: pytest.FixtureRequest, fixture_name: str) -> None:
    font: TTFont = request.getfixturevalue(fixture_name)
    _assert_axes(font)

    design_axes = font["STAT"].table.DesignAxisRecord
    assert design_axes is not None
    tags = [axis.AxisTag for axis in design_axes.Axis]
    assert len(tags) == 4
    assert set(tags) == set(AXES)


def test_default_instance_is_regular_and_installable_families_do_not_collide(
    primary_font: TTFont, sidecar_font: TTFont
) -> None:
    for font in (primary_font, sidecar_font):
        defaults = {axis.axisTag: float(axis.defaultValue) for axis in font["fvar"].axes}
        matching = [
            instance
            for instance in font["fvar"].instances
            if {tag: float(value) for tag, value in instance.coordinates.items()}
            == defaults
        ]
        assert len(matching) == 1
        assert font["name"].getDebugName(matching[0].subfamilyNameID) == "Regular"

    assert primary_font["name"].getDebugName(1) == "Lötschberg"
    assert sidecar_font["name"].getDebugName(1) == "Lötschberg Text"
    assert primary_font["name"].getDebugName(16) == "Lötschberg"
    assert sidecar_font["name"].getDebugName(16) == "Lötschberg Text"
    assert sidecar_font["name"].getDebugName(17) == "Regular"


@pytest.mark.parametrize("fixture_name", ["primary_font", "sidecar_font"])
def test_vertical_metrics(request: pytest.FixtureRequest, fixture_name: str) -> None:
    font: TTFont = request.getfixturevalue(fixture_name)
    assert font["head"].unitsPerEm == 1000

    os2 = font["OS/2"]
    assert os2.sCapHeight == 700
    assert os2.sxHeight == 500
    assert os2.sTypoAscender == 960
    assert os2.sTypoDescender == -300
    assert os2.sTypoLineGap == 0
    assert os2.usWinAscent == 960
    assert os2.usWinDescent == 300

    hhea = font["hhea"]
    assert hhea.ascent == 960
    assert hhea.descent == -300
    assert hhea.lineGap == 0


@pytest.mark.parametrize("fixture_name", ["primary_font", "sidecar_font"])
def test_unicode_cmap_coverage(request: pytest.FixtureRequest, fixture_name: str) -> None:
    font: TTFont = request.getfixturevalue(fixture_name)
    unicode_formats = {table.format for table in font["cmap"].tables if table.isUnicode()}
    assert {4, 12} <= unicode_formats

    cmap = font.getBestCmap()
    assert cmap is not None
    missing = sorted(REQUIRED_CODEPOINTS - set(cmap))
    assert not missing, "missing codepoints: " + ", ".join(f"U+{cp:04X}" for cp in missing)


def test_primary_colrv1_palette_and_color_bases(primary_font: TTFont) -> None:
    assert primary_font["COLR"].version == 1
    _assert_palette(primary_font)

    base_list = primary_font["COLR"].table.BaseGlyphList
    assert base_list is not None
    color_bases = {record.BaseGlyph for record in base_list.BaseGlyphPaintRecord}
    assert _variant_name(primary_font, ord("A"), "ext") in color_bases
    assert _variant_name(primary_font, ord("A"), "hand.ext") in color_bases


def test_gsub_feature_contract(primary_font: TTFont, sidecar_font: TTFont) -> None:
    primary_features = _feature_tags(primary_font)
    sidecar_features = _feature_tags(sidecar_font)
    assert {"ss01", "ss02"} <= primary_features
    assert "ss01" in sidecar_features
    assert "ss02" not in sidecar_features


def test_primary_shapes_all_four_variant_states(primary_font: TTFont) -> None:
    base = _cmap_name(primary_font, ord("A"))
    expected = {
        (): base,
        ("ss01",): _variant_name(primary_font, ord("A"), "hand"),
        ("ss02",): _variant_name(primary_font, ord("A"), "ext"),
        ("ss01", "ss02"): _variant_name(primary_font, ord("A"), "hand.ext"),
    }
    for enabled, glyph_name in expected.items():
        features = {tag: True for tag in enabled}
        assert _shape_names(PRIMARY_PATH, primary_font, "A", features) == [glyph_name]


def test_sidecar_shapes_handdrawn_but_has_no_extruded_state(sidecar_font: TTFont) -> None:
    base = _cmap_name(sidecar_font, ord("A"))
    hand = _variant_name(sidecar_font, ord("A"), "hand")
    assert _shape_names(SIDECAR_PATH, sidecar_font, "A", {}) == [base]
    assert _shape_names(SIDECAR_PATH, sidecar_font, "A", {"ss01": True}) == [hand]


def test_slnt_axis_changes_outlines(primary_font: TTFont) -> None:
    glyph_name = _cmap_name(primary_font, ord("A"))
    upright = _static_primary(slnt=0.0)
    slanted = _static_primary(slnt=-12.0)
    try:
        assert _recording(upright, glyph_name) != _recording(slanted, glyph_name)
    finally:
        upright.close()
        slanted.close()


def test_negative_slnt_leans_clockwise(primary_font: TTFont) -> None:
    glyph_name = _cmap_name(primary_font, ord("H"))
    slanted = _static_primary(slnt=-12.0)
    try:
        glyf = slanted["glyf"]
        coordinates, _end_points, _flags = glyf[glyph_name].getCoordinates(glyf)
        baseline_x = [x for x, y in coordinates if y == 0]
        cap_x = [x for x, y in coordinates if y == 700]
        assert baseline_x and cap_x
        assert min(cap_x) > min(baseline_x)
    finally:
        slanted.close()


def test_h_left_stem_is_invariant_across_width(primary_font: TTFont) -> None:
    narrow = _static_primary(wdth=75.0)
    wide = _static_primary(wdth=125.0)
    try:
        narrow_stem = _left_h_stem(narrow)
        wide_stem = _left_h_stem(wide)
        assert narrow_stem == pytest.approx(wide_stem, abs=1.0)
    finally:
        narrow.close()
        wide.close()


@pytest.mark.parametrize(
    ("path", "flavor"),
    [(WOFF_PATH, "woff"), (WOFF2_PATH, "woff2")],
)
def test_webfonts_reopen_and_preserve_colrv1(path: Path, flavor: str) -> None:
    font = TTFont(path, lazy=False)
    try:
        assert font.flavor == flavor
        assert {"COLR", "CPAL", "glyf", "gvar", "fvar", "GSUB"} <= set(font.keys())
        assert font["COLR"].version == 1
        _assert_palette(font)
        _assert_axes(font)
        assert {"ss01", "ss02"} <= _feature_tags(font)
    finally:
        font.close()


def test_topology_report_has_zero_mismatches() -> None:
    report = json.loads(TOPOLOGY_PATH.read_text(encoding="utf-8"))
    signals, failures = _topology_signals(report)
    assert signals, "topology report has no explicit compatibility/mismatch result"
    assert not failures, "topology report records failures at: " + ", ".join(failures)
