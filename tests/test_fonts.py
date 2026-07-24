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
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables._g_l_y_f import flagOverlapSimple
from fontTools.varLib.instancer import instantiateVariableFont


ROOT = Path(__file__).resolve().parents[1]
PRIMARY_PATH = ROOT / "Loetschberg-VF[wght,wdth].ttf"
SIDECAR_PATH = ROOT / "Loetschberg-Text-VF[wght,wdth].otf"
REGULAR_COMPAT_PATH = ROOT / "Loetschberg-Regular-VF[wght,wdth].ttf"
WOFF_PATH = ROOT / "Loetschberg-VF.woff"
WOFF2_PATH = ROOT / "Loetschberg-VF.woff2"
TOPOLOGY_PATH = ROOT / "sources" / "topology-report.json"
INTERPOLATABLE_PATH = ROOT / "interpolatable-report.json"

ARTIFACTS = (
    PRIMARY_PATH,
    SIDECAR_PATH,
    REGULAR_COMPAT_PATH,
    WOFF_PATH,
    WOFF2_PATH,
    TOPOLOGY_PATH,
    INTERPOLATABLE_PATH,
)

AXES = {
    "wght": (100.0, 400.0, 900.0),
    "wdth": (75.0, 100.0, 125.0),
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


@pytest.fixture(scope="session")
def regular_compat_font() -> TTFont:
    font = TTFont(REGULAR_COMPAT_PATH, lazy=False)
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


def _glyf_polygons(font: TTFont, glyph_name: str) -> list[tuple[tuple[float, float], ...]]:
    glyf = font["glyf"]
    coordinates, end_points, _flags = glyf[glyph_name].getCoordinates(glyf)
    polygons: list[tuple[tuple[float, float], ...]] = []
    start = 0
    for end in end_points:
        polygons.append(
            tuple((float(x), float(y)) for x, y in coordinates[start : end + 1])
        )
        start = end + 1
    return polygons


def _compiled_polygons_attach(
    first: tuple[tuple[float, float], ...],
    second: tuple[tuple[float, float], ...],
) -> bool:
    epsilon = 1e-6

    def cross(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (
            b[1] - a[1]
        ) * (c[0] - a[0])

    def on_segment(
        a: tuple[float, float],
        b: tuple[float, float],
        point: tuple[float, float],
    ) -> bool:
        return (
            abs(cross(a, b, point)) <= epsilon
            and min(a[0], b[0]) - epsilon <= point[0] <= max(a[0], b[0]) + epsilon
            and min(a[1], b[1]) - epsilon <= point[1] <= max(a[1], b[1]) + epsilon
        )

    def intersects(
        a: tuple[float, float],
        b: tuple[float, float],
        c: tuple[float, float],
        d: tuple[float, float],
    ) -> bool:
        values = (cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b))
        if (
            ((values[0] > epsilon and values[1] < -epsilon)
             or (values[0] < -epsilon and values[1] > epsilon))
            and ((values[2] > epsilon and values[3] < -epsilon)
                 or (values[2] < -epsilon and values[3] > epsilon))
        ):
            return True
        return (
            on_segment(a, b, c)
            or on_segment(a, b, d)
            or on_segment(c, d, a)
            or on_segment(c, d, b)
        )

    return any(
        intersects(a, b, c, d)
        for a, b in zip(first, first[1:] + first[:1], strict=True)
        for c, d in zip(second, second[1:] + second[:1], strict=True)
    )


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


def test_desktop_font_table_contracts(
    primary_font: TTFont,
    sidecar_font: TTFont,
    regular_compat_font: TTFont,
) -> None:
    common = {"head", "hhea", "maxp", "OS/2", "hmtx", "cmap", "name", "post", "fvar", "HVAR", "STAT", "GSUB"}
    primary_required = common | {"glyf", "loca", "gvar", "COLR", "CPAL"}
    sidecar_required = common | {"CFF2"}
    compat_required = common | {"glyf", "loca", "gvar"}

    assert primary_required <= set(primary_font.keys())
    assert {"CFF ", "CFF2"}.isdisjoint(primary_font.keys())
    assert sidecar_required <= set(sidecar_font.keys())
    assert {"glyf", "loca", "gvar", "COLR", "CPAL", "CFF "}.isdisjoint(
        sidecar_font.keys()
    )
    assert compat_required <= set(regular_compat_font.keys())
    assert {"COLR", "CPAL", "CFF ", "CFF2"}.isdisjoint(
        regular_compat_font.keys()
    )


@pytest.mark.parametrize(
    "fixture_name",
    [
        "primary_font",
        "sidecar_font",
        "regular_compat_font",
    ],
)
def test_variable_axes_and_stat(request: pytest.FixtureRequest, fixture_name: str) -> None:
    font: TTFont = request.getfixturevalue(fixture_name)
    _assert_axes(font)

    design_axes = font["STAT"].table.DesignAxisRecord
    assert design_axes is not None
    tags = [axis.AxisTag for axis in design_axes.Axis]
    assert len(tags) == 2
    assert set(tags) == set(AXES)


def test_default_instance_version_and_family_names(
    primary_font: TTFont,
    sidecar_font: TTFont,
    regular_compat_font: TTFont,
) -> None:
    for font in (
        primary_font,
        sidecar_font,
        regular_compat_font,
    ):
        defaults = {axis.axisTag: float(axis.defaultValue) for axis in font["fvar"].axes}
        matching = [
            instance
            for instance in font["fvar"].instances
            if {tag: float(value) for tag, value in instance.coordinates.items()}
            == defaults
        ]
        assert len(matching) == 1
        assert font["name"].getDebugName(matching[0].subfamilyNameID) == "Regular"
        assert font["name"].getDebugName(5) == "Version 1.003"
        assert font["head"].fontRevision == pytest.approx(1.003, abs=0.00002)

    assert primary_font["name"].getDebugName(1) == "Lötschberg"
    assert regular_compat_font["name"].getDebugName(1) == "Lötschberg"
    assert sidecar_font["name"].getDebugName(1) == "Lötschberg Text"
    assert primary_font["name"].getDebugName(16) == "Lötschberg"
    assert regular_compat_font["name"].getDebugName(16) == "Lötschberg"
    assert sidecar_font["name"].getDebugName(16) == "Lötschberg Text"
    assert regular_compat_font["name"].getDebugName(17) == "Regular"
    assert sidecar_font["name"].getDebugName(17) == "Regular"
    assert primary_font["name"].getDebugName(6) == "LoetschbergVF"
    assert regular_compat_font["name"].getDebugName(6) == "LoetschbergVF"
    assert sidecar_font["name"].getDebugName(6) == "LoetschbergTextVF"


@pytest.mark.parametrize(
    ("fixture_name", "expected_prefix"),
    [
        ("primary_font", "Loetschberg"),
        ("sidecar_font", "LoetschbergText"),
        ("regular_compat_font", "Loetschberg"),
    ],
)
def test_variable_postscript_prefix_is_present(
    request: pytest.FixtureRequest,
    fixture_name: str,
    expected_prefix: str,
) -> None:
    font: TTFont = request.getfixturevalue(fixture_name)
    assert font["name"].getDebugName(25) == expected_prefix


@pytest.mark.parametrize(
    ("fixture_name", "postscript_prefix"),
    [
        ("primary_font", "Loetschberg"),
        ("sidecar_font", "LoetschbergText"),
        ("regular_compat_font", "Loetschberg"),
    ],
)
def test_named_instances_have_loadable_postscript_names(
    request: pytest.FixtureRequest,
    fixture_name: str,
    postscript_prefix: str,
) -> None:
    """Figma and other font brokers address variable instances by PS name."""
    font: TTFont = request.getfixturevalue(fixture_name)
    names: list[str] = []
    for instance in font["fvar"].instances:
        assert instance.postscriptNameID != 0xFFFF
        style_name = font["name"].getDebugName(instance.subfamilyNameID)
        postscript_name = font["name"].getDebugName(instance.postscriptNameID)
        assert style_name is not None
        expected = (
            f"{postscript_prefix}VF"
            if style_name == "Regular"
            else f"{postscript_prefix}-{style_name.replace(' ', '')}"
        )
        assert postscript_name == expected
        names.append(postscript_name)
    assert len(names) == len(set(names))


@pytest.mark.parametrize(
    "fixture_name",
    [
        "primary_font",
        "sidecar_font",
        "regular_compat_font",
    ],
)
def test_vertical_metrics(request: pytest.FixtureRequest, fixture_name: str) -> None:
    font: TTFont = request.getfixturevalue(fixture_name)
    assert font["head"].unitsPerEm == 1000

    os2 = font["OS/2"]
    assert os2.fsType == 0
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


@pytest.mark.parametrize(
    "fixture_name",
    [
        "primary_font",
        "sidecar_font",
        "regular_compat_font",
    ],
)
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


def _colr_layer_children(font: TTFont, paint: object) -> tuple[object, ...]:
    if paint.Format != ot.PaintFormat.PaintColrLayers:
        return ()
    layer_list = font["COLR"].table.LayerList
    assert layer_list is not None
    start = paint.FirstLayerIndex
    return tuple(layer_list.Paint[start : start + paint.NumLayers])


def _walk_colr_paints(font: TTFont, paint: object) -> tuple[object, ...]:
    descendants: list[object] = [paint]
    if paint.Format == ot.PaintFormat.PaintColrLayers:
        for child in _colr_layer_children(font, paint):
            descendants.extend(_walk_colr_paints(font, child))
    elif paint.Format == ot.PaintFormat.PaintComposite:
        descendants.extend(_walk_colr_paints(font, paint.SourcePaint))
        descendants.extend(_walk_colr_paints(font, paint.BackdropPaint))
    elif paint.Format == ot.PaintFormat.PaintGlyph:
        descendants.extend(_walk_colr_paints(font, paint.Paint))
    return tuple(descendants)


def _flatten_colr_layer_sequence(font: TTFont, paint: object) -> tuple[object, ...]:
    if paint.Format != ot.PaintFormat.PaintColrLayers:
        return (paint,)
    layers: list[object] = []
    for child in _colr_layer_children(font, paint):
        layers.extend(_flatten_colr_layer_sequence(font, child))
    return tuple(layers)


def test_hatches_use_runtime_src_in_wall_clipping(primary_font: TTFont) -> None:
    assert not any(
        ".hatchSupport" in name for name in primary_font.getGlyphOrder()
    )
    base_list = primary_font["COLR"].table.BaseGlyphList
    assert base_list is not None
    records = base_list.BaseGlyphPaintRecord
    assert len(records) == 380

    for record in records:
        base = record.BaseGlyph
        layers = _flatten_colr_layer_sequence(primary_font, record.Paint)
        assert [paint.Format for paint in layers] == [
            ot.PaintFormat.PaintGlyph,
            ot.PaintFormat.PaintGlyph,
            ot.PaintFormat.PaintComposite,
            ot.PaintFormat.PaintGlyph,
            ot.PaintFormat.PaintGlyph,
        ]
        wall_dark, wall_bronze, composite, keyline, face = layers
        for paint, role, palette_index in (
            (wall_dark, "wallDark", 2),
            (wall_bronze, "wallBronze", 1),
            (keyline, "keyline", 3),
            (face, "face", 0),
        ):
            assert paint.Glyph == f"{base}.{role}"
            assert paint.Paint.Format == ot.PaintFormat.PaintSolid
            assert paint.Paint.PaletteIndex == palette_index
            assert paint.Paint.Alpha == 1.0

        assert composite.CompositeMode == ot.CompositeMode.SRC_IN

        source = composite.SourcePaint
        assert source.Format == ot.PaintFormat.PaintGlyph
        assert source.Glyph == f"{base}.hatch"
        assert source.Paint.Format == ot.PaintFormat.PaintSolid
        assert source.Paint.PaletteIndex == 2
        assert source.Paint.Alpha == 1.0

        backdrop = _flatten_colr_layer_sequence(
            primary_font,
            composite.BackdropPaint,
        )
        assert len(backdrop) == 2
        for paint, role, palette_index in (
            (backdrop[0], "wallDark", 2),
            (backdrop[1], "wallBronze", 1),
        ):
            assert paint.Format == ot.PaintFormat.PaintGlyph
            assert paint.Glyph == f"{base}.{role}"
            assert paint.Paint.Format == ot.PaintFormat.PaintSolid
            assert paint.Paint.PaletteIndex == palette_index
            assert paint.Paint.Alpha == 1.0


def test_primary_marks_piecewise_outlines_as_overlapping(primary_font: TTFont) -> None:
    glyf = primary_font["glyf"]
    for codepoint in map(ord, "BGH"):
        for suffix in (None, "hand"):
            name = (
                _cmap_name(primary_font, codepoint)
                if suffix is None
                else _variant_name(primary_font, codepoint, suffix)
            )
            glyph = glyf[name]
            glyph.expand(glyf)
            assert glyph.numberOfContours > 1
            assert glyph.flags[0] & flagOverlapSimple


def test_regular_compat_unions_piecewise_face_geometry(
    primary_font: TTFont,
    regular_compat_font: TTFont,
) -> None:
    """The local TTF keeps the web face metrics but removes overlap semantics."""

    for codepoint in map(ord, "BGH"):
        name = _cmap_name(regular_compat_font, codepoint)
        regular = regular_compat_font["glyf"][name]
        regular.expand(regular_compat_font["glyf"])
        assert not (regular.flags[0] & flagOverlapSimple)
        assert regular_compat_font["hmtx"][name] == primary_font["hmtx"][name]


def test_gsub_feature_contract(
    primary_font: TTFont,
    sidecar_font: TTFont,
    regular_compat_font: TTFont,
) -> None:
    primary_features = _feature_tags(primary_font)
    assert {"ss01", "ss02"} <= primary_features
    for mono_font in (
        sidecar_font,
        regular_compat_font,
    ):
        mono_features = _feature_tags(mono_font)
        assert "ss01" in mono_features
        assert "ss02" not in mono_features


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


def test_regular_compat_shapes_handdrawn_as_ss01_only(
    regular_compat_font: TTFont,
) -> None:
    font = regular_compat_font
    base = _cmap_name(font, ord("A"))
    hand = _variant_name(font, ord("A"), "hand")
    assert _shape_names(REGULAR_COMPAT_PATH, font, "A", {}) == [base]
    assert _shape_names(
        REGULAR_COMPAT_PATH, font, "A", {"ss01": True}
    ) == [hand]
    assert _shape_names(
        REGULAR_COMPAT_PATH, font, "A", {"ss02": True}
    ) == [base]


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


def test_heavy_strokes_use_width_aware_ink_budget(primary_font: TTFont) -> None:
    thin = _static_primary(wght=100.0, wdth=125.0)
    black_condensed = _static_primary(wght=900.0, wdth=75.0)
    black_normal = _static_primary(wght=900.0, wdth=100.0)
    black_expanded = _static_primary(wght=900.0, wdth=125.0)
    try:
        assert _left_h_stem(thin) == pytest.approx(40, abs=1.0)
        condensed = _left_h_stem(black_condensed)
        normal = _left_h_stem(black_normal)
        expanded = _left_h_stem(black_expanded)
        assert 160 <= condensed < normal < expanded <= 180
    finally:
        thin.close()
        black_condensed.close()
        black_normal.close()
        black_expanded.close()


def test_thin_structural_joins_survive_interpolated_width(
    primary_font: TTFont,
) -> None:
    for width in (87.5, 112.5):
        instance = _static_primary(
            wght=100.0,
            wdth=width,
        )
        try:
            for suffix in (None, "hand"):
                names = {
                    character: (
                        _cmap_name(instance, ord(character))
                        if suffix is None
                        else _variant_name(instance, ord(character), suffix)
                    )
                    for character in ("R", "N", "1")
                }
                r_polygons = _glyf_polygons(instance, names["R"])
                assert any(
                    _compiled_polygons_attach(body, r_polygons[-1])
                    for body in r_polygons[:-1]
                )

                n_polygons = _glyf_polygons(instance, names["N"])
                assert _compiled_polygons_attach(n_polygons[0], n_polygons[2])
                assert _compiled_polygons_attach(n_polygons[1], n_polygons[2])

                one_polygons = _glyf_polygons(instance, names["1"])
                assert _compiled_polygons_attach(
                    one_polygons[0],
                    one_polygons[1],
                )
        finally:
            instance.close()


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


def test_interpolatable_report_contains_only_advisory_rematching() -> None:
    report = json.loads(INTERPOLATABLE_PATH.read_text(encoding="utf-8"))
    problem_types: set[str] = set()

    def visit(node: object) -> None:
        if isinstance(node, Mapping):
            problem_type = node.get("type")
            if isinstance(problem_type, str):
                problem_types.add(problem_type)
            for value in node.values():
                visit(value)
        elif isinstance(node, Sequence) and not isinstance(
            node, (str, bytes, bytearray)
        ):
            for value in node:
                visit(value)

    visit(report)
    assert problem_types <= {"wrong_start_point", "contour_order"}
