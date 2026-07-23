"""Reproducible UFO, variable-font, COLRv1, and web-font build pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from fontTools import agl
from fontTools.colorLib.builder import buildCOLR, buildCPAL
from fontTools.designspaceLib import (
    AxisDescriptor,
    DesignSpaceDocument,
    InstanceDescriptor,
    SourceDescriptor,
)
from fontTools.misc.roundTools import otRound
from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.ttLib.tables._g_l_y_f import flagOverlapSimple
from ufoLib2 import Font

from . import generator as gen


ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "sources"
COLOR_SOURCES = SOURCES / "color"
TEXT_SOURCES = SOURCES / "text"
BUILD = ROOT / "build"

PRIMARY_NAME = "Loetschberg-VF[wght,wdth,opsz,slnt].ttf"
SIDECAR_NAME = "Loetschberg-Text-VF[wght,wdth,opsz,slnt].otf"
PRIMARY = ROOT / PRIMARY_NAME
SIDECAR = ROOT / SIDECAR_NAME
WOFF = ROOT / "Loetschberg-VF.woff"
WOFF2 = ROOT / "Loetschberg-VF.woff2"

COLOR_DESIGNSPACE = SOURCES / "Loetschberg.designspace"
TEXT_DESIGNSPACE = SOURCES / "Loetschberg-Text.designspace"

UPM = 1000
CAP_HEIGHT = 700
X_HEIGHT = 500
ASCENDER = 960
DESCENDER = -300
HATCH_N = 7
FIXED_OT_TIMESTAMP = 3867523200  # 2026-07-22 00:00:00 UTC, seconds from 1904.


@dataclass(frozen=True, slots=True)
class MasterSpec:
    """One generated interpolation source."""

    key: str
    wght: float = 400
    wdth: float = 100
    opsz: float = 12
    slnt: float = 0

    @property
    def location(self) -> dict[str, float]:
        return {
            "Weight": self.wght,
            "Width": self.wdth,
            "Optical size": self.opsz,
            "Slant": self.slnt,
        }

    @property
    def design_location(self) -> dict[str, float]:
        return {
            "wght": self.wght,
            "wdth": self.wdth,
            "opsz": self.opsz,
            "slnt": self.slnt,
        }

    @property
    def style_name(self) -> str:
        return f"Master {self.key}"

    @property
    def track(self) -> float:
        return _opsz_value(self.opsz, 140, 196)

    @property
    def kern(self) -> float:
        return _opsz_value(self.opsz, -40, -55)

    def params(self, *, hand: bool = False) -> gen.GeneratorParams:
        s, sh = _weight_strokes(self.wght)
        # Optical-size compensation scales the selected weight instead of
        # subtracting a fixed amount. A fixed subtraction made Caption Thin
        # disproportionately fragile (24 units versus 184 at Black), whereas
        # the donor's 88/104 and 85/100 ratios describe a coherent optical cut
        # at every weight.
        s *= _opsz_value(self.opsz, 88 / 104, 1)
        sh *= _opsz_value(self.opsz, 85 / 100, 1)
        return gen.GeneratorParams(
            s=s,
            sh=sh,
            # The donor's Caption cut uses an 81% skeleton. Multiplying it by
            # the registered width location keeps the two controls orthogonal:
            # wdth chooses the family width, opsz applies the optical cut.
            w=(self.wdth / 100) * _opsz_value(self.opsz, 0.81, 1),
            v=(
                _opsz_value(self.opsz, 46, 60),
                _opsz_value(self.opsz, 54, 70),
            ),
            hatch_n=HATCH_N,
            hatch_t=_opsz_value(self.opsz, 10, 9),
            hatch_sp=_opsz_value(self.opsz, 21, 17),
            jit=3.4 if hand else 0,
        )


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _weight_strokes(weight: float) -> tuple[float, float]:
    if weight <= 400:
        t = (weight - 100) / 300
        return _lerp(40, 104, t), _lerp(36, 100, t)
    t = (weight - 400) / 500
    return _lerp(104, 200, t), _lerp(100, 196, t)


def _opsz_value(opsz: float, small: float, display: float) -> float:
    # The donor has two exact cuts. The transition is completed at the default;
    # 12..144 retains the display construction and provides a named endpoint.
    t = min(1.0, max(0.0, (opsz - 8) / 4))
    return _lerp(small, display, t)


def master_specs() -> list[MasterSpec]:
    """Return exact 4x3 core and Caption planes plus support sources."""

    specs = [MasterSpec("default")]
    for weight in (100, 400, 700, 900):
        for width in (75, 100, 125):
            if (weight, width) == (400, 100):
                continue
            specs.append(MasterSpec(f"w{weight}-d{width}", weight, width))
    for weight in (100, 400, 700, 900):
        for width in (75, 100, 125):
            key = (
                "caption"
                if (weight, width) == (400, 100)
                else f"caption-w{weight}-d{width}"
            )
            specs.append(MasterSpec(key, weight, width, opsz=8))
    specs.extend([MasterSpec("display", opsz=144), MasterSpec("slanted", slnt=-12)])
    return specs


def glyph_name(char: str) -> str:
    cp = ord(char)
    return agl.UV2AGL.get(cp, f"uni{cp:04X}" if cp <= 0xFFFF else f"u{cp:05X}")


def drawn_chars() -> tuple[str, ...]:
    chars = tuple(sorted(gen.glyph_defs(gen.GeneratorParams()), key=ord))
    if len(chars) != 190:
        raise AssertionError(f"expected 190 generated glyphs, found {len(chars)}")
    expected = {chr(cp) for cp in range(0x21, 0x7F)}
    expected.update(chr(cp) for cp in range(0xA1, 0x100))
    expected.add("ı")
    missing = expected.difference(chars)
    if missing:
        raise AssertionError(f"generator coverage is incomplete: {sorted(missing)!r}")
    return chars


DRAWN_CHARS = drawn_chars()
CHAR_TO_NAME = {char: glyph_name(char) for char in DRAWN_CHARS}
COMPOSITES = {**gen.CAP_COMPOSITES, **gen.LC_COMPOSITES}


def hand_name(name: str) -> str:
    return f"{name}.hand"


def ext_name(name: str, hand: bool = False) -> str:
    return f"{name}.hand.ext" if hand else f"{name}.ext"


def layer_name(name: str, role: str, hand: bool = False) -> str:
    return f"{ext_name(name, hand)}.{role}"


def mark_name(char: str, hand: bool = False) -> str:
    base, accent = COMPOSITES[char]
    name = f"_mark.{glyph_name(char)}.{glyph_name(base)}.{accent}"
    return f"{name}.hand" if hand else name


def _all_layer_names() -> list[str]:
    roles = (
        "wallDark",
        "wallBronze",
        "hatch",
        "keyline",
        "face",
    )
    return [
        layer_name(CHAR_TO_NAME[char], role, hand)
        for char in DRAWN_CHARS
        for hand in (False, True)
        for role in roles
    ]


def _feature_text(*, text_only: bool, kern: float) -> str:
    base = [CHAR_TO_NAME[char] for char in DRAWN_CHARS]
    hand = [hand_name(name) for name in base]
    lines = [
        "languagesystem DFLT dflt;",
        "languagesystem latn dflt;",
        f"@base = [{' '.join(base)}];",
        f"@hand = [{' '.join(hand)}];",
    ]
    if not text_only:
        ext = [ext_name(name) for name in base]
        hand_ext = [ext_name(name, True) for name in base]
        lines.extend(
            [
                f"@ext = [{' '.join(ext)}];",
                f"@hand_ext = [{' '.join(hand_ext)}];",
            ]
        )
    lines.extend(
        [
            "feature ss01 {",
            '  featureNames { name "Handdrawn"; };',
            "  sub @base by @hand;",
        ]
    )
    if not text_only:
        lines.append("  sub @ext by @hand_ext;")
    lines.append("} ss01;")
    if not text_only:
        lines.extend(
            [
                "feature ss02 {",
                '  featureNames { name "Extruded"; };',
                "  sub @base by @ext;",
                "  sub @hand by @hand_ext;",
                "} ss02;",
            ]
        )

    pair_chars = (("L", "Ö"), ("T", "S"), ("R", "G"))
    lines.append("feature kern {")
    for left_char, right_char in pair_chars:
        left, right = CHAR_TO_NAME[left_char], CHAR_TO_NAME[right_char]
        families = [(left, right), (hand_name(left), hand_name(right))]
        if not text_only:
            families.extend(
                [
                    (ext_name(left), ext_name(right)),
                    (ext_name(left, True), ext_name(right, True)),
                ]
            )
        for l_name, r_name in families:
            lines.append(f"  pos {l_name} {r_name} {kern:g};")
    lines.append("} kern;")
    return "\n".join(lines) + "\n"


def _font_info(font: Font, spec: MasterSpec, *, text_only: bool) -> None:
    info = font.info
    info.familyName = "Lötschberg Text" if text_only else "Lötschberg"
    info.styleName = spec.style_name
    info.styleMapFamilyName = "Lötschberg Text" if text_only else "Lötschberg"
    info.styleMapStyleName = "regular"
    info.unitsPerEm = UPM
    info.ascender = ASCENDER
    info.descender = DESCENDER
    info.capHeight = CAP_HEIGHT
    info.xHeight = X_HEIGHT
    info.italicAngle = spec.slnt
    info.versionMajor = 1
    info.versionMinor = 0
    info.year = 2026
    info.openTypeNameVersion = "Version 1.000"
    info.openTypeNameUniqueID = f"1.000;ADCV;Loetschberg-{spec.key}"
    info.openTypeNameDesigner = "ADCV"
    info.openTypeNameManufacturer = "ADCV"
    info.openTypeNameDescription = (
        "Lötschberg parametric variable colour railway sans"
        if not text_only
        else "Lötschberg mono CFF2 text sidecar"
    )
    info.openTypeOS2VendorID = "ADCV"
    info.openTypeOS2WeightClass = int(round(spec.wght))
    info.openTypeOS2WidthClass = max(1, min(9, round(5 + (spec.wdth - 100) / 12.5)))
    info.openTypeOS2TypoAscender = ASCENDER
    info.openTypeOS2TypoDescender = DESCENDER
    info.openTypeOS2TypoLineGap = 0
    info.openTypeOS2WinAscent = ASCENDER
    info.openTypeOS2WinDescent = abs(DESCENDER)
    info.openTypeHheaAscender = ASCENDER
    info.openTypeHheaDescender = DESCENDER
    info.openTypeHheaLineGap = 0
    info.postscriptFontName = f"Loetschberg-{spec.key.replace('-', '')}"
    info.postscriptFullName = f"Lötschberg {spec.style_name}"
    info.postscriptWeightName = "Regular"
    info.postscriptUnderlinePosition = -100
    info.postscriptUnderlineThickness = 50


def _outline_contours(outline: gen.GlyphOutline) -> list[tuple[gen.SamplePoint, ...]]:
    return [contour.points for contour in outline.contours]


def _layer_contours(pieces: Sequence[gen.LayerPiece]) -> list[tuple[gen.SamplePoint, ...]]:
    return [contour for piece in pieces for contour in piece.contours]


def _source_bbox(contours: Sequence[Sequence[gen.SamplePoint]]) -> tuple[float, float, float, float]:
    points = [point for contour in contours for point in contour]
    if not points:
        return 0, 0, 0, 0
    return (
        min(point.x for point in points),
        min(point.y for point in points),
        max(point.x for point in points),
        max(point.y for point in points),
    )


def _font_contours(
    contours: Sequence[Sequence[gen.SamplePoint]],
    *,
    slnt: float,
    shift_x: float,
) -> list[list[tuple[float, float]]]:
    # Registered `slnt` uses negative values for a clockwise/right lean.  Font
    # coordinates are y-up, so negate the tangent to move cap points right.
    shear = -math.tan(math.radians(slnt))
    result: list[list[tuple[float, float]]] = []
    for contour in contours:
        transformed: list[tuple[float, float]] = []
        for point in contour:
            y = CAP_HEIGHT - point.y
            transformed.append((point.x + shift_x + shear * y, y))
        result.append(transformed)
    return result


def _polygon_area(points: Sequence[tuple[float, float]]) -> float:
    return (
        sum(
            first[0] * second[1] - second[0] * first[1]
            for first, second in zip(
                points,
                (*points[1:], points[0]),
                strict=True,
            )
        )
        / 2
    )


def _grid_safe_wall_contours(
    contours: Sequence[Sequence[tuple[float, float]]],
    *,
    minimum_area: float = 8.0,
) -> list[list[tuple[float, float]]]:
    """Keep edge-on wall planes nonzero after the compiler's integer rounding.

    A wall contour is a face-side run followed by the reversed, translated
    rear run. When that run is nearly parallel to the depth vector, a valid
    floating plane can quantize onto one line. In that exact case only, move
    the complete rear run by the smallest integer lattice vector that retains
    the raw winding and an explicit rounded-area margin. The shared face edge
    and the contour topology remain untouched.

    This protects generated source masters. A wall whose tangent genuinely
    crosses the extrusion direction between masters may still pass smoothly
    through an edge-on state; the frozen-recipe model intentionally permits
    that physical transition instead of forcing a different visibility run.
    """

    result: list[list[tuple[float, float]]] = []
    for source in contours:
        contour = list(source)
        if len(contour) < 4 or len(contour) % 2:
            raise AssertionError(
                f"wall contour must contain paired front/rear paths: {len(contour)}"
            )
        rounded = [(otRound(x), otRound(y)) for x, y in contour]
        raw_area = _polygon_area(contour)
        rounded_area = _polygon_area(rounded)
        if raw_area and rounded_area == 0:
            half = len(contour) // 2
            candidates: list[
                tuple[int, float, int, int, list[tuple[float, float]]]
            ] = []
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx == dy == 0:
                        continue
                    candidate = [
                        *contour[:half],
                        *((x + dx, y + dy) for x, y in contour[half:]),
                    ]
                    candidate_area = _polygon_area(
                        [(otRound(x), otRound(y)) for x, y in candidate]
                    )
                    if (
                        candidate_area * raw_area > 0
                        and abs(candidate_area) >= minimum_area
                    ):
                        candidates.append(
                            (
                                dx * dx + dy * dy,
                                -abs(candidate_area),
                                dx,
                                dy,
                                candidate,
                            )
                        )
            if not candidates:
                raise AssertionError(
                    "unable to preserve a quantized wall plane within two units"
                )
            selected = min(candidates, key=lambda candidate: candidate[:4])
            contour = selected[4]
            rounded_area = _polygon_area(
                [(otRound(x), otRound(y)) for x, y in contour]
            )
        if raw_area and rounded_area == 0:
            raise AssertionError("quantized wall plane collapsed")
        result.append(contour)
    return result


def _signature(contours: Sequence[Sequence[object]]) -> tuple[int, tuple[int, ...]]:
    return len(contours), tuple(len(contour) for contour in contours)


def _draw_contours(glyph, contours: Sequence[Sequence[tuple[float, float]]]) -> None:
    pen = glyph.getPen()
    for contour in contours:
        if len(contour) < 3:
            continue
        pen.moveTo(contour[0])
        for point in contour[1:]:
            pen.lineTo(point)
        pen.closePath()


def _add_component(glyph, base: str) -> None:
    glyph.getPen().addComponent(base, (1, 0, 0, 1, 0, 0))


def _new_glyph(
    font: Font,
    name: str,
    width: float,
    contours: Sequence[Sequence[tuple[float, float]]] = (),
    *,
    unicodes: Sequence[int] = (),
    components: Sequence[str] = (),
) -> None:
    glyph = font.newGlyph(name)
    glyph.width = round(width, 6)
    glyph.unicodes = list(unicodes)
    _draw_contours(glyph, contours)
    for component in components:
        _add_component(glyph, component)


def _notdef(font: Font) -> None:
    contours = [
        [(50, -200), (450, -200), (450, 700), (50, 700)],
        [(140, -110), (140, 610), (360, 610), (360, -110)],
    ]
    _new_glyph(font, ".notdef", 500, contours)


def _component_base(char: str) -> str:
    return COMPOSITES.get(char, (char, ""))[0]


def _shift_and_width(
    char: str,
    outlines: Mapping[str, gen.GlyphOutline],
    track: float,
) -> tuple[float, float]:
    base = _component_base(char)
    contours = _outline_contours(outlines[base])
    x_min, _y_min, x_max, _y_max = _source_bbox(contours)
    return track / 2 - x_min, x_max - x_min + track


def _component_mark_contours(
    char: str,
    full: gen.GlyphOutline,
    base: gen.GlyphOutline,
) -> list[tuple[gen.SamplePoint, ...]]:
    accent_pieces = full.pieces[len(base.pieces) :]
    return [contour.points for piece in accent_pieces for contour in piece.contours]


def _glyph_order(*, text_only: bool) -> list[str]:
    base_names = [CHAR_TO_NAME[char] for char in DRAWN_CHARS]
    marks = [mark_name(char, hand) for char in COMPOSITES for hand in (False, True)]
    order = [".notdef", "space", "nbspace", *base_names]
    order.extend(hand_name(name) for name in base_names)
    order.extend(marks)
    if not text_only:
        order.extend(ext_name(name) for name in base_names)
        order.extend(ext_name(name, True) for name in base_names)
        order.extend(_all_layer_names())
    return order


def _freeze_default() -> tuple[
    dict[str, gen.GlyphTopology],
    dict[str, gen.FrozenRecipe],
    dict[str, gen.FrozenRecipe],
]:
    default = gen.GeneratorParams()
    topologies = gen.freeze_topology(default, DRAWN_CHARS)
    regular: dict[str, gen.FrozenRecipe] = {}
    hand: dict[str, gen.FrozenRecipe] = {}
    for index, char in enumerate(DRAWN_CHARS, 1):
        regular[char], hand[char] = gen.freeze_recipes(
            char,
            default,
            topology=topologies[char],
        )
        if index % 40 == 0:
            print(f"  froze colour recipes {index}/{len(DRAWN_CHARS)}", flush=True)
    return topologies, regular, hand


def _build_master_fonts(
    spec: MasterSpec,
    topologies: Mapping[str, gen.GlyphTopology],
    regular_recipes: Mapping[str, gen.FrozenRecipe],
    hand_recipes: Mapping[str, gen.FrozenRecipe],
) -> tuple[Font, Font, dict[str, tuple[int, tuple[int, ...]]]]:
    color = Font()
    text = Font()
    _font_info(color, spec, text_only=False)
    _font_info(text, spec, text_only=True)
    color.features.text = _feature_text(text_only=False, kern=spec.kern)
    text.features.text = _feature_text(text_only=True, kern=spec.kern)
    _notdef(color)
    _notdef(text)
    _new_glyph(color, "space", 430 * spec.wdth / 100, unicodes=[0x20])
    _new_glyph(text, "space", 430 * spec.wdth / 100, unicodes=[0x20])
    _new_glyph(color, "nbspace", 430 * spec.wdth / 100, unicodes=[0xA0])
    _new_glyph(text, "nbspace", 430 * spec.wdth / 100, unicodes=[0xA0])

    regular_params = spec.params(hand=False)
    hand_params = spec.params(hand=True)
    regular_outlines = {
        char: gen.build_contours(char, regular_params, topology=topologies[char])
        for char in DRAWN_CHARS
    }
    hand_outlines = {
        char: gen.build_contours(char, hand_params, topology=topologies[char])
        for char in DRAWN_CHARS
    }

    signatures: dict[str, tuple[int, tuple[int, ...]]] = {
        ".notdef": (2, (4, 4)),
        "space": (0, ()),
        "nbspace": (0, ()),
    }
    mark_categories: dict[str, str] = {}

    for char in DRAWN_CHARS:
        name = CHAR_TO_NAME[char]
        shift, width = _shift_and_width(char, regular_outlines, spec.track)
        hand_shift, _ = _shift_and_width(char, hand_outlines, spec.track)
        regular_source = _outline_contours(regular_outlines[char])
        hand_source = _outline_contours(hand_outlines[char])
        regular_font = _font_contours(regular_source, slnt=spec.slnt, shift_x=shift)
        hand_font = _font_contours(hand_source, slnt=spec.slnt, shift_x=hand_shift)

        if char in COMPOSITES:
            base_char, _accent = COMPOSITES[char]
            base_name = CHAR_TO_NAME[base_char]
            reg_mark = mark_name(char)
            hnd_mark = mark_name(char, True)
            regular_mark_source = _component_mark_contours(
                char, regular_outlines[char], regular_outlines[base_char]
            )
            hand_mark_source = _component_mark_contours(
                char, hand_outlines[char], hand_outlines[base_char]
            )
            regular_mark_font = _font_contours(
                regular_mark_source, slnt=spec.slnt, shift_x=shift
            )
            hand_mark_font = _font_contours(
                hand_mark_source, slnt=spec.slnt, shift_x=hand_shift
            )
            for font in (color, text):
                _new_glyph(font, reg_mark, 0, regular_mark_font)
                _new_glyph(font, hnd_mark, 0, hand_mark_font)
            mark_categories[reg_mark] = mark_categories[hnd_mark] = "mark"
            _new_glyph(
                color,
                name,
                width,
                unicodes=[ord(char)],
                components=[base_name, reg_mark],
            )
            _new_glyph(
                text,
                name,
                width,
                unicodes=[ord(char)],
                components=[base_name, reg_mark],
            )
            _new_glyph(
                color,
                hand_name(name),
                width,
                components=[hand_name(base_name), hnd_mark],
            )
            _new_glyph(
                text,
                hand_name(name),
                width,
                components=[hand_name(base_name), hnd_mark],
            )
            signatures[name] = signatures[hand_name(name)] = (0, ())
            signatures[reg_mark] = _signature(regular_mark_source)
            signatures[hnd_mark] = _signature(hand_mark_source)
        else:
            _new_glyph(color, name, width, regular_font, unicodes=[ord(char)])
            _new_glyph(text, name, width, regular_font, unicodes=[ord(char)])
            _new_glyph(color, hand_name(name), width, hand_font)
            _new_glyph(text, hand_name(name), width, hand_font)
            signatures[name] = _signature(regular_source)
            signatures[hand_name(name)] = _signature(hand_source)

        # COLR base glyphs keep a mono face component as a graceful fallback.
        _new_glyph(color, ext_name(name), width, components=[name])
        _new_glyph(color, ext_name(name, True), width, components=[hand_name(name)])
        signatures[ext_name(name)] = signatures[ext_name(name, True)] = (0, ())

        for is_hand, recipe, params, layer_shift in (
            (False, regular_recipes[char], regular_params, shift),
            (True, hand_recipes[char], hand_params, hand_shift),
        ):
            layers = gen.replay_recipe(recipe, params)
            roles = {
                "wallDark": layers.wall_dark,
                "wallBronze": layers.wall_bronze,
                "hatch": layers.hatch,
                "keyline": layers.keyline,
                "face": layers.face,
            }
            for role, pieces in roles.items():
                source_contours = _layer_contours(pieces)
                font_contours = _font_contours(
                    source_contours, slnt=spec.slnt, shift_x=layer_shift
                )
                if role in {"wallDark", "wallBronze"}:
                    font_contours = _grid_safe_wall_contours(font_contours)
                lname = layer_name(name, role, is_hand)
                _new_glyph(color, lname, width, font_contours)
                signatures[lname] = _signature(source_contours)

    for font, text_only in ((color, False), (text, True)):
        font.lib["public.glyphOrder"] = _glyph_order(text_only=text_only)
        font.lib["public.openTypeCategories"] = mark_categories
    return color, text, signatures


def _write_designspace(specs: Sequence[MasterSpec], *, text_only: bool) -> Path:
    document = DesignSpaceDocument()
    family_name = "Lötschberg Text" if text_only else "Lötschberg"
    axes = [
        ("wght", "Weight", 100, 400, 900),
        ("wdth", "Width", 75, 100, 125),
        ("opsz", "Optical size", 8, 12, 144),
        ("slnt", "Slant", -12, 0, 0),
    ]
    for tag, name, minimum, default, maximum in axes:
        axis = AxisDescriptor()
        axis.tag = tag
        axis.name = name
        axis.minimum = minimum
        axis.default = default
        axis.maximum = maximum
        axis.labelNames = {"en": name}
        document.addAxis(axis)

    source_dir = "text" if text_only else "color"
    for spec in specs:
        source = SourceDescriptor()
        source.name = spec.key
        source.familyName = family_name
        source.styleName = spec.style_name
        source.filename = f"{source_dir}/{spec.key}.ufo"
        source.designLocation = spec.location
        if spec.key == "default":
            source.copyInfo = True
            source.copyLib = True
            source.copyGroups = True
            source.copyFeatures = True
        document.addSource(source)

    width_names = ((75, "Condensed"), (100, "Normal"), (125, "Expanded"))
    weight_names = ((100, "Thin"), (400, "Regular"), (700, "Bold"), (900, "Black"))
    for weight, weight_name in weight_names:
        for width, width_name in width_names:
            instance = InstanceDescriptor()
            instance.familyName = family_name
            instance.styleName = (
                weight_name if width == 100 else f"{weight_name} {width_name}"
            )
            instance.designLocation = {
                "Weight": weight,
                "Width": width,
                "Optical size": 12,
                "Slant": 0,
            }
            document.addInstance(instance)
    for optical, name in ((8, "Caption"), (144, "Display")):
        instance = InstanceDescriptor()
        instance.familyName = family_name
        instance.styleName = name
        instance.designLocation = {
            "Weight": 400,
            "Width": 100,
            "Optical size": optical,
            "Slant": 0,
        }
        document.addInstance(instance)

    path = TEXT_DESIGNSPACE if text_only else COLOR_DESIGNSPACE
    document.write(path)
    return path


def generate_sources() -> dict[str, object]:
    print("Freezing default topology and COLRv1 recipes…", flush=True)
    topologies, regular_recipes, hand_recipes = _freeze_default()
    specs = master_specs()
    expected: dict[str, tuple[int, tuple[int, ...]]] | None = None
    mismatches: list[dict[str, object]] = []
    master_summary: list[dict[str, object]] = []

    for number, spec in enumerate(specs, 1):
        print(f"Generating source {number}/{len(specs)}: {spec.key}", flush=True)
        color, text, signatures = _build_master_fonts(
            spec, topologies, regular_recipes, hand_recipes
        )
        if expected is None:
            expected = signatures
        else:
            for name, signature in signatures.items():
                if expected.get(name) != signature:
                    mismatches.append(
                        {
                            "master": spec.key,
                            "glyph": name,
                            "expected": expected.get(name),
                            "actual": signature,
                        }
                    )
        color_path = COLOR_SOURCES / f"{spec.key}.ufo"
        text_path = TEXT_SOURCES / f"{spec.key}.ufo"
        color.save(color_path, overwrite=True)
        text.save(text_path, overwrite=True)
        master_summary.append({"name": spec.key, "location": spec.design_location})

    if mismatches:
        raise AssertionError(f"interpolation topology mismatches: {mismatches[:5]!r}")
    _write_designspace(specs, text_only=False)
    _write_designspace(specs, text_only=True)
    signature_payload = {
        name: [signature[0], list(signature[1])]
        for name, signature in sorted((expected or {}).items())
    }
    signature_hash = hashlib.sha256(
        json.dumps(signature_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    report: dict[str, object] = {
        "schemaVersion": 1,
        "status": "compatible",
        "compatible": True,
        "mismatchCount": 0,
        "mismatches": [],
        "canonicalScriptSHA256": gen.GRID_SOURCE_SHA256,
        "masterCount": len(specs),
        "masters": master_summary,
        "generatedGlyphCount": len(DRAWN_CHARS),
        "ufoGlyphCount": len(expected or {}),
        "hatchCountPerGroup": HATCH_N,
        "signatureSHA256": signature_hash,
        "signatures": signature_payload,
    }
    (SOURCES / "topology-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def _run(command: Sequence[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def compile_fonts() -> None:
    uncolored = BUILD / "Loetschberg-uncolored.ttf"
    _run(
        [
            sys.executable,
            "-m",
            "fontmake",
            "-m",
            str(COLOR_DESIGNSPACE),
            "-o",
            "variable",
            "--output-path",
            str(uncolored),
            "--validate-ufo",
            "--check-compatibility",
            "--no-production-names",
            "--no-subset",
            "--keep-overlaps",
            "--ttf-curves",
            "cu2qu",
        ]
    )
    _run(
        [
            sys.executable,
            "-m",
            "fontmake",
            "-m",
            str(TEXT_DESIGNSPACE),
            "-o",
            "variable-cff2",
            "--output-path",
            str(SIDECAR),
            "--validate-ufo",
            "--check-compatibility",
            "--no-production-names",
            "--no-subset",
            "--keep-overlaps",
            "--subroutinizer",
            "cffsubr",
        ]
    )
    _postprocess_primary(uncolored)
    _postprocess_sidecar()
    _write_web_fonts()


def _set_name(font: TTFont, name_id: int, value: str) -> None:
    names = font["name"]
    names.setName(value, name_id, 3, 1, 0x409)
    try:
        names.setName(value, name_id, 1, 0, 0)
    except UnicodeEncodeError:
        pass


def _ensure_cmap12(font: TTFont) -> None:
    cmap = font["cmap"]
    if any(table.format == 12 for table in cmap.tables):
        return
    table = CmapSubtable.newSubtable(12)
    table.platformID = 3
    table.platEncID = 10
    table.language = 0
    table.cmap = dict(font.getBestCmap())
    cmap.tables.append(table)


def _stat(font: TTFont) -> None:
    axes = [
        {
            "tag": "wght",
            "name": "Weight",
            "ordering": 0,
            "values": [
                {"value": 100, "name": "Thin"},
                {"value": 400, "name": "Regular", "flags": 0x2},
                {"value": 700, "name": "Bold"},
                {"value": 900, "name": "Black"},
            ],
        },
        {
            "tag": "wdth",
            "name": "Width",
            "ordering": 1,
            "values": [
                {"value": 75, "name": "Condensed"},
                {"value": 100, "name": "Normal", "flags": 0x2},
                {"value": 125, "name": "Expanded"},
            ],
        },
        {
            "tag": "opsz",
            "name": "Optical size",
            "ordering": 2,
            "values": [
                {"value": 8, "name": "Caption"},
                {"value": 12, "name": "Text", "flags": 0x2},
                {"value": 144, "name": "Display"},
            ],
        },
        {
            "tag": "slnt",
            "name": "Slant",
            "ordering": 3,
            "values": [
                {"value": -12, "name": "Slanted"},
                {"value": 0, "name": "Upright", "flags": 0x2},
            ],
        },
    ]
    buildStatTable(font, axes, elidedFallbackName="Regular")


def _common_postprocess(font: TTFont, *, text: bool) -> None:
    font.recalcTimestamp = False
    head = font["head"]
    head.created = FIXED_OT_TIMESTAMP
    head.modified = FIXED_OT_TIMESTAMP
    head.fontRevision = 1.0
    head.unitsPerEm = UPM
    head.macStyle = 0
    hhea = font["hhea"]
    hhea.ascent = ASCENDER
    hhea.descent = DESCENDER
    hhea.lineGap = 0
    os2 = font["OS/2"]
    os2.sTypoAscender = ASCENDER
    os2.sTypoDescender = DESCENDER
    os2.sTypoLineGap = 0
    os2.usWinAscent = ASCENDER
    os2.usWinDescent = abs(DESCENDER)
    os2.sCapHeight = CAP_HEIGHT
    os2.sxHeight = X_HEIGHT
    os2.fsSelection &= ~((1 << 0) | (1 << 5))
    os2.fsSelection |= (1 << 6) | (1 << 7) | (1 << 8)
    font["post"].italicAngle = 0
    # The sidecar gets a distinct install family so both upright Regular fonts
    # can coexist in applications without style-link collisions.
    family = "Lötschberg Text" if text else "Lötschberg"
    subfamily = "Regular"
    _set_name(font, 1, family)
    _set_name(font, 2, subfamily)
    _set_name(font, 3, f"1.000;ADCV;{'LoetschbergTextVF' if text else 'LoetschbergVF'}")
    _set_name(font, 4, f"{family} {subfamily}")
    _set_name(font, 5, "Version 1.000")
    _set_name(font, 6, "LoetschbergTextVF" if text else "LoetschbergVF")
    _set_name(font, 16, family)
    _set_name(font, 17, subfamily)
    _ensure_cmap12(font)
    _stat(font)
    if "DSIG" in font:
        del font["DSIG"]


def _hex_rgba(value: str) -> tuple[float, float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)) + (1.0,)


def _postprocess_primary(uncolored: Path) -> None:
    font = TTFont(uncolored, recalcTimestamp=False)
    _common_postprocess(font, text=False)
    glyf = font["glyf"]
    # The source deliberately keeps compatible pieces separate. Advertise
    # those overlaps to rasterizers so heavy junctions use the intended
    # non-zero fill instead of dropping coincident regions.
    for glyph in glyf.glyphs.values():
        glyph.expand(glyf)
        if glyph.numberOfContours <= 0:
            continue
        if len(glyph.flags):
            glyph.flags[0] |= flagOverlapSimple
    palette = [
        _hex_rgba(gen.COLORS["face"]),
        _hex_rgba(gen.COLORS["bronze"]),
        _hex_rgba(gen.COLORS["dark"]),
        _hex_rgba(gen.COLORS["key"]),
    ]
    color_glyphs: dict[str, dict[str, object]] = {}

    def solid(palette_index: int) -> dict[str, object]:
        return {
            "Format": ot.PaintFormat.PaintSolid,
            "PaletteIndex": palette_index,
            "Alpha": 1.0,
        }

    def glyph_paint(glyph: str, palette_index: int) -> dict[str, object]:
        return {
            "Format": ot.PaintFormat.PaintGlyph,
            "Glyph": glyph,
            "Paint": solid(palette_index),
        }

    for char in DRAWN_CHARS:
        name = CHAR_TO_NAME[char]
        for is_hand in (False, True):
            base = ext_name(name, is_hand)
            wall_dark = layer_name(name, "wallDark", is_hand)
            wall_bronze = layer_name(name, "wallBronze", is_hand)
            hatch = layer_name(name, "hatch", is_hand)
            keyline = layer_name(name, "keyline", is_hand)
            face = layer_name(name, "face", is_hand)
            # The nominal hatch outlines stay full-thickness, four-point quads
            # at every master. SRC_IN clips their rendered footprint to the
            # union of the live wall outlines, so clipping remains exact at
            # arbitrary interpolated locations without changing topology.
            hatch_clipped = {
                "Format": ot.PaintFormat.PaintComposite,
                "SourcePaint": glyph_paint(hatch, 2),
                "CompositeMode": ot.CompositeMode.SRC_IN,
                "BackdropPaint": {
                    "Format": ot.PaintFormat.PaintColrLayers,
                    "Layers": [
                        glyph_paint(wall_dark, 2),
                        glyph_paint(wall_bronze, 1),
                    ],
                },
            }
            paints = [
                glyph_paint(wall_dark, 2),
                glyph_paint(wall_bronze, 1),
                hatch_clipped,
                glyph_paint(keyline, 3),
                glyph_paint(face, 0),
            ]
            color_glyphs[base] = {
                "Format": ot.PaintFormat.PaintColrLayers,
                "Layers": paints,
            }
    font["CPAL"] = buildCPAL([palette])
    font["COLR"] = buildCOLR(
        color_glyphs,
        version=1,
        glyphMap=font.getReverseGlyphMap(),
    )
    font.save(PRIMARY, reorderTables=False)


def _postprocess_sidecar() -> None:
    font = TTFont(SIDECAR, recalcTimestamp=False)
    _common_postprocess(font, text=True)
    for table in ("COLR", "CPAL", "glyf", "gvar"):
        if table in font:
            del font[table]
    font.save(SIDECAR, reorderTables=False)


def _write_web_fonts() -> None:
    for flavor, path in (("woff", WOFF), ("woff2", WOFF2)):
        font = TTFont(PRIMARY, recalcTimestamp=False)
        font.flavor = flavor
        font.save(path, reorderTables=False)


def validate_outputs(topology_report: Mapping[str, object]) -> dict[str, object]:
    primary = TTFont(PRIMARY)
    sidecar = TTFont(SIDECAR)
    required_primary = {
        "glyf",
        "gvar",
        "COLR",
        "CPAL",
        "GSUB",
        "fvar",
        "STAT",
        "HVAR",
    }
    required_sidecar = {"CFF2", "GSUB", "fvar", "STAT", "HVAR"}
    errors: list[str] = []
    if missing := required_primary.difference(primary.keys()):
        errors.append(f"primary missing {sorted(missing)}")
    if missing := required_sidecar.difference(sidecar.keys()):
        errors.append(f"sidecar missing {sorted(missing)}")
    if {"COLR", "CPAL", "glyf"}.intersection(sidecar.keys()):
        errors.append("sidecar contains forbidden colour/glyf tables")
    if "COLR" in primary and primary["COLR"].version != 1:
        errors.append("primary COLR is not version 1")
    axis_ranges = {
        axis.axisTag: (axis.minValue, axis.defaultValue, axis.maxValue)
        for axis in primary["fvar"].axes
    }
    expected_axes = {
        "wght": (100, 400, 900),
        "wdth": (75, 100, 125),
        "opsz": (8, 12, 144),
        "slnt": (-12, 0, 0),
    }
    if axis_ranges != expected_axes:
        errors.append(f"axis ranges differ: {axis_ranges!r}")
    cmap = primary.getBestCmap()
    required_codepoints = set(range(0x20, 0x7F)) | set(range(0xA0, 0x100)) | {0x131}
    if missing := required_codepoints.difference(cmap):
        errors.append(f"cmap missing {len(missing)} codepoints")
    for path in (WOFF, WOFF2):
        web = TTFont(path)
        if "COLR" not in web or web["COLR"].version != 1:
            errors.append(f"{path.name} did not preserve COLRv1")
    report = {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "topologyCompatible": topology_report.get("compatible") is True,
        "primaryTables": sorted(primary.keys()),
        "sidecarTables": sorted(sidecar.keys()),
        "axes": axis_ranges,
        "cmapCount": len(cmap),
        "primaryBytes": PRIMARY.stat().st_size,
        "sidecarBytes": SIDECAR.stat().st_size,
        "woffBytes": WOFF.stat().st_size,
        "woff2Bytes": WOFF2.stat().st_size,
    }
    (ROOT / "validation-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if errors:
        raise AssertionError("; ".join(errors))
    return report


def _prepare_directories() -> None:
    for path in (SOURCES, BUILD):
        if path.exists():
            shutil.rmtree(path)
    COLOR_SOURCES.mkdir(parents=True)
    TEXT_SOURCES.mkdir(parents=True)
    BUILD.mkdir(parents=True)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-only", action="store_true")
    args = parser.parse_args(argv)
    _prepare_directories()
    topology = generate_sources()
    if args.sources_only:
        return
    compile_fonts()
    report = validate_outputs(topology)
    print(
        f"Built {PRIMARY.name}, {SIDECAR.name}, {WOFF.name}, and {WOFF2.name} "
        f"({report['status']}).",
        flush=True,
    )
