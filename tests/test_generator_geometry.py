"""Geometric regression gates for the parametric source outlines.

These checks deliberately exercise the Python generator rather than compiled
font binaries.  Stable point topology is necessary for variation, but it does
not by itself prevent a contour from folding over, reversing, or collapsing.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from pathlib import Path
from typing import TypeAlias

import pytest
from fontTools.misc.roundTools import otRound

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.loetschberg import generator as gen
from src.loetschberg.fontbuild import (
    MasterSpec,
    _font_contours,
    _grid_safe_wall_contours,
    _shift_and_width,
    master_specs,
)


Point: TypeAlias = tuple[float, float]
Box: TypeAlias = tuple[float, float, float, float]

WEIGHTS = (100.0, 400.0, 700.0, 900.0)
WIDTHS = (75.0, 100.0, 125.0)
LOCATIONS = tuple(product(WEIGHTS, WIDTHS))

COORD_EPSILON = 1e-7
AREA_EPSILON = 1e-4
MIN_HOLE_BBOX = 24.0
JOIN_EPSILON = 1e-6
CONTAINMENT_EPSILON = 1e-5
MAX_REPORTED_FAILURES = 80


@dataclass(frozen=True, slots=True)
class AuditResult:
    contour_failures: tuple[str, ...]
    junction_failures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LayerAuditResult:
    wall_failures: tuple[str, ...]
    hatch_failures: tuple[str, ...]


def _location_label(weight: float, width: float) -> str:
    return f"wght={weight:g},wdth={width:g}"


def _points(contour: gen.BuiltContour) -> tuple[Point, ...]:
    return tuple((point.x, point.y) for point in contour.ideal)


def _bbox(points: tuple[Point, ...]) -> Box:
    xs = tuple(point[0] for point in points)
    ys = tuple(point[1] for point in points)
    return min(xs), min(ys), max(xs), max(ys)


def _cross(first: Point, second: Point, third: Point) -> float:
    return (second[0] - first[0]) * (third[1] - first[1]) - (
        second[1] - first[1]
    ) * (third[0] - first[0])


def _on_segment(first: Point, second: Point, point: Point) -> bool:
    if abs(_cross(first, second, point)) > COORD_EPSILON:
        return False
    return (
        min(first[0], second[0]) - COORD_EPSILON
        <= point[0]
        <= max(first[0], second[0]) + COORD_EPSILON
        and min(first[1], second[1]) - COORD_EPSILON
        <= point[1]
        <= max(first[1], second[1]) + COORD_EPSILON
    )


def _segments_intersect(
    first_a: Point,
    first_b: Point,
    second_a: Point,
    second_b: Point,
) -> bool:
    orientations = (
        _cross(first_a, first_b, second_a),
        _cross(first_a, first_b, second_b),
        _cross(second_a, second_b, first_a),
        _cross(second_a, second_b, first_b),
    )
    first_straddles = (
        orientations[0] > COORD_EPSILON
        and orientations[1] < -COORD_EPSILON
    ) or (
        orientations[0] < -COORD_EPSILON
        and orientations[1] > COORD_EPSILON
    )
    second_straddles = (
        orientations[2] > COORD_EPSILON
        and orientations[3] < -COORD_EPSILON
    ) or (
        orientations[2] < -COORD_EPSILON
        and orientations[3] > COORD_EPSILON
    )
    if first_straddles and second_straddles:
        return True
    return (
        _on_segment(first_a, first_b, second_a)
        or _on_segment(first_a, first_b, second_b)
        or _on_segment(second_a, second_b, first_a)
        or _on_segment(second_a, second_b, first_b)
    )


def _nonadjacent_crossing(points: tuple[Point, ...]) -> tuple[int, int] | None:
    """Return the first crossing pair using an x-sorted bounding-box sweep."""

    count = len(points)
    segments = []
    for index, (first, second) in enumerate(
        zip(points, points[1:] + points[:1], strict=True)
    ):
        segments.append(
            (
                min(first[0], second[0]),
                max(first[0], second[0]),
                min(first[1], second[1]),
                max(first[1], second[1]),
                index,
                first,
                second,
            )
        )
    segments.sort(key=lambda segment: segment[0])

    for position, segment in enumerate(segments):
        min_x, max_x, min_y, max_y, index, first, second = segment
        for other in segments[position + 1 :]:
            other_min_x, other_max_x, other_min_y, other_max_y, other_index, *_ = (
                other
            )
            if other_min_x > max_x + COORD_EPSILON:
                break
            if other_max_x < min_x - COORD_EPSILON:
                continue
            if other_max_y < min_y - COORD_EPSILON:
                continue
            if other_min_y > max_y + COORD_EPSILON:
                continue
            if (
                other_index == (index + 1) % count
                or index == (other_index + 1) % count
            ):
                continue
            other_first, other_second = other[-2:]
            if _segments_intersect(first, second, other_first, other_second):
                return min(index, other_index), max(index, other_index)
    return None


def _polygons_attach(first: tuple[Point, ...], second: tuple[Point, ...]) -> bool:
    for first_a, first_b in zip(first, first[1:] + first[:1], strict=True):
        for second_a, second_b in zip(second, second[1:] + second[:1], strict=True):
            if _segments_intersect(first_a, first_b, second_a, second_b):
                return True
    return any(gen.point_in(*point, first) for point in second) or any(
        gen.point_in(*point, second) for point in first
    )


def _close(first: float, second: float) -> bool:
    return math.isclose(first, second, rel_tol=0.0, abs_tol=JOIN_EPSILON)


def _polygon_area(points: tuple[Point, ...]) -> float:
    return sum(
        first[0] * second[1] - second[0] * first[1]
        for first, second in zip(points, points[1:] + points[:1], strict=True)
    ) / 2


@pytest.mark.parametrize("width", WIDTHS)
def test_thin_round_strokes_are_balanced(width: float) -> None:
    params = MasterSpec("thin-round-probe", wght=100, wdth=width).params()
    topology = gen.freeze_topology(params, ("O", "Ö"))
    o_outline = gen.build_contours("O", params, topology=topology["O"])
    odieresis_outline = gen.build_contours(
        "Ö",
        params,
        topology=topology["Ö"],
    )

    outer = _bbox(_points(o_outline.pieces[0].contours[0]))
    inner = _bbox(_points(o_outline.pieces[0].contours[1]))
    horizontal_stroke = inner[0] - outer[0]
    vertical_stroke = inner[1] - outer[1]
    assert horizontal_stroke == pytest.approx(params.s, abs=0.75)
    assert vertical_stroke == pytest.approx(params.s, abs=0.75)

    dot = _bbox(_points(odieresis_outline.pieces[1].contours[0]))
    dot_diameter = dot[2] - dot[0]
    assert 1.15 <= dot_diameter / params.s <= 1.3


@pytest.mark.parametrize("width", WIDTHS)
def test_thin_digit_joins_have_positive_overlap(width: float) -> None:
    params = MasterSpec("thin-digit-probe", wght=100, wdth=width).params()
    topology = gen.freeze_topology(params, ("1", "5"))
    one = gen.build_contours("1", params, topology=topology["1"])
    five = gen.build_contours("5", params, topology=topology["5"])

    one_stem = _bbox(_points(one.pieces[0].contours[0]))
    one_flag = _bbox(_points(one.pieces[1].contours[0]))
    assert one_flag[2] - one_stem[0] >= 8

    bowl = _bbox(_points(five.pieces[3].contours[0]))
    for bar_index in (2, 4):
        bar = _bbox(_points(five.pieces[bar_index].contours[0]))
        assert bar[2] - bowl[0] >= 4.5


def _ordered_wall_polygons(
    recipe: gen.FrozenRecipe,
    layers: gen.ReplayedLayers,
) -> tuple[tuple[Point, ...], ...]:
    """Restore recipe-run order from the two colour-specific layer streams."""

    dark_index = 0
    bronze_index = 0
    polygons: list[tuple[Point, ...]] = []
    for run in recipe.runs:
        if run.color == "bronze":
            piece = layers.wall_bronze[bronze_index]
            bronze_index += 1
        else:
            piece = layers.wall_dark[dark_index]
            dark_index += 1
        polygons.append(tuple((point.x, point.y) for point in piece.outer))

    assert dark_index == len(layers.wall_dark)
    assert bronze_index == len(layers.wall_bronze)
    return tuple(polygons)


def _append_contour_failures(
    failures: list[str],
    glyph_name: str,
    location: str,
    outline: gen.GlyphOutline,
) -> None:
    for piece_index, piece in enumerate(outline.pieces):
        for contour_index, contour in enumerate(piece.contours):
            label = f"{glyph_name!r} {location} p{piece_index}c{contour_index}"
            points = _points(contour)

            non_finite = [
                index
                for index, point in enumerate(points)
                if not all(math.isfinite(value) for value in point)
            ]
            if non_finite:
                failures.append(f"{label}: non-finite points {non_finite[:4]}")
                continue

            repeated = [
                index
                for index, (first, second) in enumerate(
                    zip(points, points[1:] + points[:1], strict=True)
                )
                if math.dist(first, second) <= COORD_EPSILON
            ]
            if repeated:
                failures.append(
                    f"{label}: repeated consecutive points at {repeated[:4]}"
                )

            area = gen.signed_area(contour.ideal)
            expected_sign = -1 if contour.is_hole else 1
            if (
                abs(area) <= AREA_EPSILON
                or math.copysign(1.0, area) != expected_sign
            ):
                role = "hole" if contour.is_hole else "outer"
                failures.append(f"{label}: {role} winding/area is {area:.6g}")

            crossing = _nonadjacent_crossing(points)
            if crossing is not None:
                failures.append(
                    f"{label}: nonadjacent segments {crossing[0]}/{crossing[1]} cross"
                )

            if contour.is_hole:
                min_x, min_y, max_x, max_y = _bbox(points)
                width, height = max_x - min_x, max_y - min_y
                if width < MIN_HOLE_BBOX or height < MIN_HOLE_BBOX:
                    failures.append(
                        f"{label}: collapsed hole bbox {width:.3f}x{height:.3f}"
                    )


def _append_junction_failures(
    failures: list[str],
    location: str,
    params: gen.GeneratorParams,
    h_outline: gen.GlyphOutline,
    g_outline: gen.GlyphOutline,
    o_outline: gen.GlyphOutline,
) -> None:
    left_stem, right_stem, crossbar = (
        _bbox(_points(piece.outer)) for piece in h_outline.pieces
    )
    left_width = left_stem[2] - left_stem[0]
    right_width = right_stem[2] - right_stem[0]
    if not _close(left_width, params.s) or not _close(right_width, params.s):
        failures.append(
            f"'H' {location}: stem widths {left_width:.6g}/{right_width:.6g}, "
            f"expected {params.s:.6g}"
        )
    if not _close(left_stem[2], crossbar[0]):
        failures.append(
            f"'H' {location}: left junction {left_stem[2]:.6g} != "
            f"{crossbar[0]:.6g}"
        )
    if not _close(crossbar[2], right_stem[0]):
        failures.append(
            f"'H' {location}: right junction {crossbar[2]:.6g} != "
            f"{right_stem[0]:.6g}"
        )

    g_round = _points(g_outline.pieces[0].outer)
    g_terminal = _points(g_outline.pieces[1].outer)
    g_connector = _points(g_outline.pieces[2].outer)
    o_round = _points(o_outline.pieces[0].outer)
    terminal_box = _bbox(g_terminal)
    o_box = _bbox(o_round)
    if not _close(terminal_box[2], o_box[2]):
        failures.append(
            f"'G' {location}: terminal right {terminal_box[2]:.6g} != "
            f"round silhouette {o_box[2]:.6g}"
        )
    if not _polygons_attach(g_round, g_connector):
        failures.append(f"'G' {location}: connector is detached from the bowl")
    if not _polygons_attach(g_connector, g_terminal):
        failures.append(f"'G' {location}: terminal is detached from its connector")


def _append_attachment_failures(
    failures: list[str],
    location: str,
    r_outline: gen.GlyphOutline,
    n_outline: gen.GlyphOutline,
    one_outline: gen.GlyphOutline,
) -> None:
    r_leg = _points(r_outline.pieces[-1].outer)
    if not any(
        _polygons_attach(_points(piece.outer), r_leg)
        for piece in r_outline.pieces[:-1]
    ):
        failures.append(f"'R' {location}: leg is detached from its bowl/body")

    if not _polygons_attach(
        _points(one_outline.pieces[0].outer),
        _points(one_outline.pieces[1].outer),
    ):
        failures.append(f"'1' {location}: flag is detached from its stem")

    n_diagonal = _points(n_outline.pieces[2].outer)
    if not _polygons_attach(_points(n_outline.pieces[0].outer), n_diagonal):
        failures.append(f"'N' {location}: diagonal is detached from left stem")
    if not _polygons_attach(_points(n_outline.pieces[1].outer), n_diagonal):
        failures.append(f"'N' {location}: diagonal is detached from right stem")


@lru_cache(maxsize=1)
def _audit_generator_geometry() -> AuditResult:
    glyph_names = tuple(sorted(gen.glyph_defs(gen.GeneratorParams()), key=ord))
    topology = gen.freeze_topology(gen.GeneratorParams(), glyph_names)
    contour_failures: list[str] = []
    junction_failures: list[str] = []

    for weight, width in LOCATIONS:
        location = _location_label(weight, width)
        params = MasterSpec(
            "geometry-probe",
            wght=weight,
            wdth=width,
        ).params()
        outlines: dict[str, gen.GlyphOutline] = {}
        for glyph_name in glyph_names:
            outline = gen.build_contours(
                glyph_name,
                params,
                topology=topology[glyph_name],
            )
            outlines[glyph_name] = outline
            _append_contour_failures(
                contour_failures,
                glyph_name,
                location,
                outline,
            )

        _append_junction_failures(
            junction_failures,
            location,
            params,
            outlines["H"],
            outlines["G"],
            outlines["O"],
        )
        _append_attachment_failures(
            junction_failures,
            location,
            outlines["R"],
            outlines["N"],
            outlines["1"],
        )

    for hand in (False, True):
        family = "hand" if hand else "regular"
        for width in (75.0, 87.5, 100.0, 112.5, 125.0):
            params = MasterSpec(
                "thin-attachment-probe",
                wght=100,
                wdth=width,
            ).params(hand=hand)
            outlines = {
                glyph_name: gen.build_contours(
                    glyph_name,
                    params,
                    topology=topology[glyph_name],
                )
                for glyph_name in ("R", "N", "1")
            }
            for glyph_name, outline in outlines.items():
                _append_contour_failures(
                    contour_failures,
                    glyph_name,
                    f"wght=100,wdth={width:g},{family}",
                    outline,
                )
            _append_attachment_failures(
                junction_failures,
                f"wght=100,wdth={width:g},{family}",
                outlines["R"],
                outlines["N"],
                outlines["1"],
            )

    return AuditResult(tuple(contour_failures), tuple(junction_failures))


@lru_cache(maxsize=1)
def _audit_replayed_layer_geometry() -> LayerAuditResult:
    glyph_names = tuple(sorted(gen.glyph_defs(gen.GeneratorParams()), key=ord))
    topology = gen.freeze_topology(gen.GeneratorParams(), glyph_names)
    recipes = {
        glyph_name: gen.freeze_recipes(
            glyph_name,
            gen.GeneratorParams(),
            topology=topology[glyph_name],
        )
        for glyph_name in glyph_names
    }
    wall_failures: list[str] = []
    hatch_failures: list[str] = []

    for master in master_specs():
        for hand in (False, True):
            params = master.params(hand=hand)
            family = "hand" if hand else "regular"
            layer_map = {
                glyph_name: gen.replay_recipe(
                    recipes[glyph_name][1 if hand else 0],
                    params,
                )
                for glyph_name in glyph_names
            }
            outlines = {
                glyph_name: layers.outline
                for glyph_name, layers in layer_map.items()
            }
            for glyph_name in glyph_names:
                recipe = recipes[glyph_name][1 if hand else 0]
                layers = layer_map[glyph_name]
                shift, _width = _shift_and_width(
                    glyph_name,
                    outlines,
                    master.track,
                )
                wall_polygons = _ordered_wall_polygons(recipe, layers)
                for run_index, polygon in enumerate(wall_polygons):
                    if polygon:
                        raw_area = _polygon_area(polygon)
                        font_polygon = _font_contours(
                            [
                                tuple(
                                    gen.SamplePoint(x, y)
                                    for x, y in polygon
                                )
                            ],
                            shift_x=shift,
                        )
                        transformed_raw_area = _polygon_area(
                            tuple(font_polygon[0])
                        )
                        original_rounded_area = _polygon_area(
                            tuple(
                                (otRound(x), otRound(y))
                                for x, y in font_polygon[0]
                            )
                        )
                        safe_polygon = _grid_safe_wall_contours(font_polygon)[0]
                        rounded_polygon = tuple(
                            (otRound(x), otRound(y))
                            for x, y in safe_polygon
                        )
                        rounded_area = _polygon_area(rounded_polygon)
                        if abs(raw_area) <= AREA_EPSILON:
                            wall_failures.append(
                                f"{glyph_name!r} master={master.key} family={family} "
                                f"run={run_index}: nonempty wall raw area "
                                f"{raw_area:.6g}"
                            )
                        if abs(rounded_area) <= AREA_EPSILON:
                            wall_failures.append(
                                f"{glyph_name!r} master={master.key} family={family} "
                                f"run={run_index}: transformed quantization "
                                "collapses "
                                f"(raw {transformed_raw_area:.6g}, "
                                f"rounded {rounded_area:.6g})"
                            )
                        if original_rounded_area == 0 and not (
                            transformed_raw_area * rounded_area > 0
                            and abs(rounded_area) >= 8
                        ):
                            wall_failures.append(
                                f"{glyph_name!r} master={master.key} family={family} "
                                f"run={run_index}: grid repair lacks winding/area "
                                f"margin (raw {transformed_raw_area:.6g}, "
                                f"rounded {rounded_area:.6g})"
                            )
                        if (
                            original_rounded_area != 0
                            and safe_polygon != font_polygon[0]
                        ):
                            wall_failures.append(
                                f"{glyph_name!r} master={master.key} family={family} "
                                f"run={run_index}: noncollapsed wall was modified"
                            )

                expected_hatches = sum(group.count for group in recipe.hatch_groups)
                if len(layers.hatch) != expected_hatches:
                    hatch_failures.append(
                        f"{glyph_name!r} master={master.key} family={family}: "
                        f"{len(layers.hatch)} hatches, expected {expected_hatches}"
                    )
                    continue

                hatch_index = 0
                for group_index, group in enumerate(recipe.hatch_groups):
                    contour = layers.outline.pieces[group.piece_index].contours[
                        group.contour_index
                    ].points
                    before_run = recipe.runs[group.before_run]
                    after_run = recipe.runs[group.after_run]
                    before_length = gen._polyline_length(
                        gen._run_points(
                            contour,
                            before_run.start,
                            before_run.end,
                        )
                    )
                    after_length = gen._polyline_length(
                        gen._run_points(
                            contour,
                            after_run.start,
                            after_run.end,
                        )
                    )
                    half = group.count // 2
                    guard = params.hatch_t / 2
                    before_spacing = min(
                        params.hatch_sp,
                        max(0.0, (before_length - guard) / half),
                    )
                    after_spacing = min(
                        params.hatch_sp,
                        max(0.0, (after_length - guard) / half),
                    )
                    for mark_index in range(group.count):
                        hatch = layers.hatch[hatch_index]
                        quad = tuple((point.x, point.y) for point in hatch.outer)
                        if len(quad) != 4:
                            hatch_failures.append(
                                f"{glyph_name!r} master={master.key} family={family} "
                                f"group={group_index} mark={mark_index}: hatch has "
                                f"{len(quad)} points, expected 4"
                            )
                            hatch_index += 1
                            continue

                        signed_mark = mark_index - half
                        spacing = (
                            after_spacing if signed_mark >= 0 else before_spacing
                        )
                        boundary = gen._walk_contour(
                            contour,
                            group.anchor_edge,
                            abs(signed_mark) * spacing,
                            1 if signed_mark >= 0 else -1,
                        )
                        expected_center = (
                            boundary.x + params.v[0] * 0.5,
                            boundary.y + params.v[1] * 0.5,
                        )
                        actual_center = (
                            sum(point[0] for point in quad) / 4,
                            sum(point[1] for point in quad) / 4,
                        )
                        if not (
                            math.isclose(
                                actual_center[0],
                                expected_center[0],
                                rel_tol=0,
                                abs_tol=CONTAINMENT_EPSILON,
                            )
                            and math.isclose(
                                actual_center[1],
                                expected_center[1],
                                rel_tol=0,
                                abs_tol=CONTAINMENT_EPSILON,
                            )
                        ):
                            hatch_failures.append(
                                f"{glyph_name!r} master={master.key} family={family} "
                                f"group={group_index} mark={mark_index}: center "
                                f"{actual_center!r}, expected {expected_center!r}"
                            )
                        long_side = math.dist(quad[0], quad[1])
                        short_side = math.dist(quad[0], quad[3])
                        expected_length = 0.8 * math.hypot(*params.v)
                        if not math.isclose(
                            long_side,
                            expected_length,
                            rel_tol=0,
                            abs_tol=CONTAINMENT_EPSILON,
                        ):
                            hatch_failures.append(
                                f"{glyph_name!r} master={master.key} family={family} "
                                f"group={group_index} mark={mark_index}: hatch length "
                                f"{long_side:.6g}, expected {expected_length:.6g}"
                            )
                        if not math.isclose(
                            short_side,
                            params.hatch_t,
                            rel_tol=0,
                            abs_tol=CONTAINMENT_EPSILON,
                        ):
                            hatch_failures.append(
                                f"{glyph_name!r} master={master.key} family={family} "
                                f"group={group_index} mark={mark_index}: hatch thickness "
                                f"{short_side:.6g}, expected {params.hatch_t:.6g}"
                            )
                        hatch_index += 1

    return LayerAuditResult(tuple(wall_failures), tuple(hatch_failures))


def _failure_message(title: str, failures: tuple[str, ...]) -> str:
    shown = failures[:MAX_REPORTED_FAILURES]
    remainder = len(failures) - len(shown)
    suffix = f"\n... and {remainder} more" if remainder else ""
    return f"{title} ({len(failures)}):\n" + "\n".join(shown) + suffix


def test_generator_contours_are_valid_across_registered_axis_grid() -> None:
    failures = _audit_generator_geometry().contour_failures
    assert not failures, _failure_message("generator contour failures", failures)


def test_h_junctions_and_g_terminal_remain_attached() -> None:
    failures = _audit_generator_geometry().junction_failures
    assert not failures, _failure_message("generator junction failures", failures)


def test_weight_width_ink_budget_is_coordinated() -> None:
    thin = MasterSpec("probe", wght=100, wdth=125).params()
    black_condensed = MasterSpec("probe", wght=900, wdth=75).params()
    black_normal = MasterSpec("probe", wght=900, wdth=100).params()
    black_expanded = MasterSpec("probe", wght=900, wdth=125).params()
    assert thin.s == pytest.approx(40)
    assert thin.w == pytest.approx(1.25)
    assert (
        black_condensed.s
        < black_normal.s
        < black_expanded.s
    )
    assert black_normal.s == pytest.approx(176)
    assert black_normal.sh == pytest.approx(170)


def test_family_has_a_complete_weight_width_interaction_plane() -> None:
    specs = master_specs()
    assert len(specs) == 12
    assert {(spec.wght, spec.wdth) for spec in specs} == set(
        product((100, 400, 700, 900), (75, 100, 125))
    )


def test_replayed_wall_contours_have_nonzero_area_at_every_master() -> None:
    failures = _audit_replayed_layer_geometry().wall_failures
    assert not failures, _failure_message("replayed wall failures", failures)


def test_hatch_quads_keep_nominal_geometry_at_every_master() -> None:
    failures = _audit_replayed_layer_geometry().hatch_failures
    assert not failures, _failure_message("replayed hatch failures", failures)
