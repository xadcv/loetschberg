"""Junction, zone and extrusion gates across the whole designspace.

These gates look at every glyph as the reader sees it: the union of its
pieces and the walls painted behind it. They hold at all twelve sources, in
both the Regular and the Handdrawn family.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from itertools import combinations, product
from pathlib import Path

import pytest
from shapely.affinity import translate
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.loetschberg import generator as gen
from src.loetschberg.fontbuild import COMPOSITES, DRAWN_CHARS

WEIGHTS = (100.0, 400.0, 700.0, 900.0)
WIDTHS = (75.0, 100.0, 125.0)
LOCATIONS = tuple(product(WEIGHTS, WIDTHS))
DEFAULT = (400.0, 100.0)

# Hairline strokes cross where heavier ones merge, which opens a counter.
# These are the only glyphs whose union changes shape class, and only at Thin.
THIN_ONLY_COUNTERS = {"&": 3, "{": 1, "}": 1}

# Largest uncovered wall area tolerated per glyph, in square units. A wall
# sliver this small lies under the keyline.
MAX_WALL_GAP = 120.0
KEYLINE = 7.5


def _label(char: str, location: tuple[float, float]) -> str:
    return f"{char!r} wght={location[0]:g},wdth={location[1]:g}"


def _polygon(outer, holes=()) -> Polygon:
    polygon = Polygon(outer, holes)
    return polygon if polygon.is_valid else polygon.buffer(0)


def _polygons(geometry) -> list[Polygon]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    return [part for part in getattr(geometry, "geoms", ()) if isinstance(part, Polygon)]


@lru_cache(maxsize=1)
def _topology() -> dict[str, gen.GlyphTopology]:
    return gen.freeze_topology(gen.GeneratorParams(), DRAWN_CHARS)


@lru_cache(maxsize=None)
def _recipe(char: str, hand: bool) -> gen.FrozenRecipe:
    return gen.freeze_recipe(
        char, gen.GeneratorParams(), hand=hand, topology=_topology()[char]
    )


@lru_cache(maxsize=None)
def _outline(char: str, location: tuple[float, float]) -> gen.GlyphOutline:
    return gen.build_contours(
        char, gen.design_params(*location), topology=_topology()[char]
    )


def _pieces(outline: gen.GlyphOutline, *, drawn: bool = False) -> list[Polygon]:
    result = []
    for piece in outline.pieces:
        outer = piece.outer.points if drawn else piece.outer.ideal
        holes = [hole.points if drawn else hole.ideal for hole in piece.holes]
        result.append(
            _polygon(
                [(point.x, point.y) for point in outer],
                [[(point.x, point.y) for point in hole] for hole in holes],
            )
        )
    return result


@lru_cache(maxsize=None)
def _union(char: str, location: tuple[float, float]):
    return unary_union(_pieces(_outline(char, location)))


def _shape_class(geometry) -> tuple[int, int]:
    """Return ``(components, counters)`` of a union."""

    parts = _polygons(geometry)
    return len(parts), sum(len(part.interiors) for part in parts)


def _bounds(char: str, location: tuple[float, float], piece: int | None = None):
    outline = _outline(char, location)
    pieces = outline.pieces if piece is None else (outline.pieces[piece],)
    xs = [point.x for built in pieces for point in built.outer.ideal]
    ys = [point.y for built in pieces for point in built.outer.ideal]
    return min(xs), min(ys), max(xs), max(ys)


# --------------------------------------------------------------- face shape
def test_default_cut_matches_the_structure_master() -> None:
    assert gen.design_params(*DEFAULT) == gen.GeneratorParams()
    assert gen.design_masters()[0] == gen.GeneratorParams()
    assert len(gen.design_masters()) == len(LOCATIONS)


def test_every_glyph_keeps_its_shape_class_at_every_source() -> None:
    """No junction opens, no counter closes, no part detaches."""

    failures = []
    for char in DRAWN_CHARS:
        expected = _shape_class(_union(char, DEFAULT))
        for location in LOCATIONS:
            actual = _shape_class(_union(char, location))
            if actual == expected:
                continue
            if (
                location[0] == 100.0
                and char in THIN_ONLY_COUNTERS
                and actual == (expected[0], THIN_ONLY_COUNTERS[char])
            ):
                continue
            failures.append(f"{_label(char, location)}: {actual}, default {expected}")
    assert not failures, "\n".join(failures)


def test_touching_pieces_overlap_instead_of_abutting() -> None:
    """An abutting joint opens into a hairline once it is jittered or rounded."""

    failures = []
    for char in DRAWN_CHARS:
        for location in LOCATIONS:
            pieces = _pieces(_outline(char, location))
            for (i, first), (j, second) in combinations(enumerate(pieces), 2):
                if first.distance(second) > 1e-6:
                    continue
                if first.intersection(second).area >= 1.0:
                    continue
                # A seam that a third piece covers is not on the surface.
                seam = first.boundary.intersection(second.boundary)
                cover = unary_union(
                    [piece for k, piece in enumerate(pieces) if k not in (i, j)]
                )
                if seam.difference(cover.buffer(0.01)).length > 1.0:
                    failures.append(
                        f"{_label(char, location)}: pieces {i} and {j} only abut"
                    )
    assert not failures, "\n".join(failures[:60])


@pytest.mark.parametrize(
    ("chars", "top", "bottom"),
    [
        ("HEFILTBDPRKNMVWXYZJ", 0.0, 700.0),
        ("OCG0", -12.0, 712.0),
        ("U", 0.0, 712.0),
        ("vwxzıu", 200.0, None),
        ("oce", 188.0, 712.0),
        ("bdhkl", 0.0, None),
        ("pqgjy", None, 900.0),
        ("1457", 0.0, 700.0),
        ("23", None, 700.0),
    ],
)
def test_alignment_zones_hold_at_every_weight_and_width(
    chars: str, top: float | None, bottom: float | None
) -> None:
    """Heavy cuts grow into the counter, never out of the zone."""

    for char in chars:
        for location in LOCATIONS:
            _x0, y0, _x1, y1 = _bounds(char, location)
            if top is not None:
                assert y0 == pytest.approx(top, abs=0.75), _label(char, location)
            if bottom is not None:
                assert y1 == pytest.approx(bottom, abs=0.75), _label(char, location)


@pytest.mark.parametrize(
    ("char", "stem", "bowl", "side"),
    [
        ("b", 0, 1, "left"),
        ("p", 0, 1, "left"),
        ("þ", 0, 1, "left"),
        ("h", 0, 1, "left"),
        ("n", 0, 1, "left"),
        ("r", 0, 1, "left"),
        ("a", 1, 0, "right"),
        ("d", 1, 0, "right"),
        ("q", 1, 0, "right"),
        ("g", 1, 0, "right"),
        ("h", 2, 1, "right"),
        ("n", 2, 1, "right"),
        ("u", 0, 1, "left"),
        ("u", 2, 1, "right"),
        ("U", 0, 2, "left"),
        ("U", 1, 2, "right"),
        ("J", 0, 1, "right"),
        ("6", 1, 0, "left"),
        ("6", 1, 2, "left"),
    ],
)
def test_stem_and_bowl_share_one_edge(
    char: str, stem: int, bowl: int, side: str
) -> None:
    """A bowl must neither bulge past its stem nor sit inside it."""

    index = 0 if side == "left" else 2
    for location in LOCATIONS:
        stem_edge = _bounds(char, location, stem)[index]
        bowl_edge = _bounds(char, location, bowl)[index]
        # Junction-aligned samples lie on the curve's chords, which sit up
        # to a sagitta inside the true extreme.
        assert stem_edge == pytest.approx(bowl_edge, abs=0.3), _label(char, location)


def test_m_arches_meet_on_the_middle_stem() -> None:
    for location in LOCATIONS:
        first, arch_one, middle, arch_two, last = (
            _bounds("m", location, index) for index in range(5)
        )
        assert arch_one[0] == pytest.approx(first[0], abs=0.3)
        assert arch_one[2] == pytest.approx(middle[2], abs=0.3)
        assert arch_two[0] == pytest.approx(middle[0], abs=0.3)
        assert arch_two[2] == pytest.approx(last[2], abs=0.3)


def test_seven_diagonal_leaves_from_the_bar_corner() -> None:
    """The diagonal used to run past the bar end away from Regular."""

    for location in LOCATIONS:
        outline = _outline("7", location)
        bar = _bounds("7", location, 0)
        diagonal = [(point.x, point.y) for point in outline.pieces[1].outer.ideal]
        assert max(x for x, _y in diagonal) == pytest.approx(bar[2], abs=0.05)
        # The outer edge turns exactly at the bar's lower right corner.
        assert any(
            abs(x - bar[2]) < 0.05 and abs(y - bar[3]) < 0.05 for x, y in diagonal
        ), _label("7", location)
        assert min(y for _x, y in diagonal) > bar[1]
        assert min(y for _x, y in diagonal) < bar[3]


def test_six_stem_matches_the_strokes_it_joins() -> None:
    """Ring, stem and hook of the 6 were three different widths."""

    for location in LOCATIONS:
        params = gen.design_params(*location)
        ring = _bounds("6", location, 0)
        stem = _bounds("6", location, 1)
        hook = _bounds("6", location, 2)
        assert stem[2] - stem[0] == pytest.approx(params.s, abs=0.05)
        assert stem[0] == pytest.approx(ring[0], abs=0.3)
        assert stem[0] == pytest.approx(hook[0], abs=0.3)
        assert _shape_class(_union("6", location)) == (1, 1)


def test_accents_clear_their_base_letter() -> None:
    """An accent keeps its clearance; it grows upward, not into the letter."""

    failures = []
    for char, (base, accent) in COMPOSITES.items():
        if accent == "ced":
            continue
        for location in LOCATIONS:
            base_pieces = len(_outline(base, location).pieces)
            pieces = _pieces(_outline(char, location))
            letter = unary_union(pieces[:base_pieces])
            mark = unary_union(pieces[base_pieces:])
            gap = letter.distance(mark)
            if gap < 12.0:
                failures.append(f"{_label(char, location)}: clearance {gap:.1f}")
    assert not failures, "\n".join(failures)


def test_dots_keep_pace_with_the_stem() -> None:
    """A dot must not be lighter than the stem it sits on."""

    for location in LOCATIONS:
        params = gen.design_params(*location)
        stem = _bounds("i", location, 0)
        dot = _bounds("i", location, 1)
        diameter = dot[2] - dot[0]
        assert 0.98 * params.s <= diameter <= 1.45 * params.s, _label("i", location)
        # The dot is centred on its stem at every weight.
        assert (dot[0] + dot[2]) / 2 == pytest.approx((stem[0] + stem[2]) / 2, abs=0.05)
        # Baseline punctuation stays on the baseline (to a chord's sagitta).
        assert _bounds(".", location)[3] == pytest.approx(700.0, abs=0.3)
        assert _bounds("!", location, 1)[3] == pytest.approx(700.0, abs=0.3)


# ----------------------------------------------------------------- extrusion
def _sweep(union, vector: tuple[float, float]):
    """Return everything the face covers while it travels along ``vector``."""

    parts = [union, translate(union, vector[0], vector[1])]
    for polygon in _polygons(union):
        for ring in (polygon.exterior, *polygon.interiors):
            coords = list(ring.coords)
            for a, b in zip(coords, coords[1:]):
                quad = Polygon(
                    [a, b, (b[0] + vector[0], b[1] + vector[1]), (a[0] + vector[0], a[1] + vector[1])]
                )
                if quad.area > 1e-6:
                    parts.append(quad if quad.is_valid else quad.buffer(0))
    return unary_union(parts)


@lru_cache(maxsize=None)
def _wall_gap(char: str, location: tuple[float, float], hand: bool) -> float:
    params = gen.design_params(*location, hand=hand)
    layers = gen.replay_recipe(_recipe(char, hand), params)
    union = unary_union(_pieces(layers.outline, drawn=True))

    def raised(pieces) -> list[Polygon]:
        return [
            _polygon([(point.x, point.y) for point in piece.outer]).buffer(0.05)
            for piece in pieces
            if not piece.flat
        ]

    walls = unary_union(raised(layers.wall_dark) + raised(layers.wall_bronze))
    needed = _sweep(union, params.v).difference(union)
    # The keyline band hides a wall sliver narrower than its own offset.
    uncovered = needed.difference(walls.buffer(0.75)).difference(
        union.buffer(KEYLINE + 0.5)
    )
    return sum(part.area for part in _polygons(uncovered) if part.area > 15.0)


@pytest.mark.parametrize("hand", [False, True], ids=["regular", "handdrawn"])
def test_walls_cover_the_extruded_shadow_everywhere(hand: bool) -> None:
    """Every edge that faces the extrusion at a source owns a wall there."""

    failures = []
    for char in DRAWN_CHARS:
        for location in LOCATIONS:
            gap = _wall_gap(char, location, hand)
            if gap > MAX_WALL_GAP:
                failures.append(f"{_label(char, location)}: {gap:.0f} square units")
    assert not failures, "\n".join(failures[:60])


def test_walls_are_never_wound_against_their_neighbours() -> None:
    """A raised wall and a flat wall never cancel under the nonzero fill."""

    for char in "ßkC9´«X":
        for location in LOCATIONS:
            layers = gen.replay_recipe(_recipe(char, False), gen.design_params(*location))
            for piece in (*layers.wall_dark, *layers.wall_bronze):
                points = [(point.x, point.y) for point in piece.outer]
                area = sum(
                    a[0] * b[1] - b[0] * a[1]
                    for a, b in zip(points, points[1:] + points[:1])
                ) / 2
                if piece.flat:
                    assert abs(area) < 25.0, _label(char, location)
                else:
                    assert area < 0, _label(char, location)


def test_sample_points_follow_a_moving_junction() -> None:
    """The stem of E carries a sample point on every bar edge at each source."""

    for location in LOCATIONS:
        params = gen.design_params(*location)
        outline = _outline("E", location)
        stem = outline.pieces[0].outer.ideal
        right = max(point.x for point in stem)
        levels = {round(point.y, 6) for point in stem if abs(point.x - right) < 1e-6}
        for expected in (
            params.sh,
            360 - params.sh / 2,
            360 + params.sh / 2,
            700 - params.sh,
        ):
            assert any(abs(level - expected) < HIDE for level in levels), (
                _label("E", location),
                expected,
            )


HIDE = gen.HIDE_OFFSET + 0.5
