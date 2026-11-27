"""Canonical Lötschberg parametric glyph generator.

The default cut reproduces ``Loetschberg Character Grid.dc.html``.  All
coordinates remain in the source's y-down coordinate system; font-coordinate
conversion belongs to the build layer.  The specimen generator is deliberately
not consulted here.

Away from the default cut, three rules keep every glyph in one piece:

* builders place each stroke from the edges of the stroke it joins
  (``glyph_defs``);
* outlines are sampled between their junctions, so a wall starts and stops
  where two pieces meet at every source (``freeze_topology``);
* a wall that faces away from the extrusion, or is buried, at a source is
  kept flat there instead of being wound against its neighbours
  (``freeze_recipe``, ``replay_recipe``).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from math import asin, atan2, ceil, cos, inf, pi, sin, sqrt
from typing import Literal, TypeAlias


# SHA-256 of the decoded text inside the canonical ``data-dc-script`` element.
GRID_SOURCE_SHA256 = "b42ad1dfdf204d650da26e35624b3283466350efb0bf780ad0fb3777ee02f47a"
# SHA-256 of the complete containing HTML file, useful for source-governance CI.
GRID_HTML_SHA256 = "c0c10bb4c72138d3ebc13e2ba509899f57036c49afc1baecc6a0cf84fdf9c985"
HATCH_N = 7
SUBDIVISION_MAX_LENGTH = 28.0
# Sample spacing allowed at sources other than the structure master, and for
# curve chords anywhere. Counts are shared by all sources, so sizing every
# edge for the widest cut at 24 units would add a third more points.
RELAXED_MAX_LENGTH = 38.0

COLORS = {
    "ground": "#7C453B",
    "face": "#E2A250",
    "bronze": "#B07A41",
    "dark": "#3A332A",
    "key": "#2A2016",
}


def _js_hypot(*values: float) -> float:
    """Match V8 ``Math.hypot``'s scaled compensated summation."""

    magnitudes = [abs(value) for value in values]
    maximum = max(magnitudes, default=0.0)
    if maximum == inf:
        return inf
    if maximum == 0:
        return 0.0
    total = 0.0
    compensation = 0.0
    for magnitude in magnitudes:
        summand = (magnitude / maximum) ** 2 - compensation
        preliminary = total + summand
        compensation = (preliminary - total) - summand
        total = preliminary
    return sqrt(total) * maximum

RawPoint: TypeAlias = tuple[float, float, int]
Builder: TypeAlias = Callable[[], list["Piece"]]


@dataclass(slots=True)
class Contour:
    """A source contour whose point flag is 0, 1 (arc), or 2 (forced cap)."""

    pts: list[RawPoint]


@dataclass(slots=True)
class Piece:
    """One filled source piece, represented by an outer and optional holes."""

    outer: Contour
    holes: list[Contour]


@dataclass(frozen=True, slots=True)
class GeneratorParams:
    """Parameters consumed by the canonical grid generator."""

    s: float = 104.0
    sh: float = 100.0
    w: float = 1.0
    v: tuple[float, float] = (60.0, 70.0)
    hatch_n: int = HATCH_N
    hatch_t: float = 9.0
    hatch_sp: float = 17.0
    jit: float = 0.0

    @property
    def hatchN(self) -> int:  # noqa: N802 - source spelling
        return self.hatch_n

    @property
    def hatchT(self) -> float:  # noqa: N802 - source spelling
        return self.hatch_t

    @property
    def hatchSp(self) -> float:  # noqa: N802 - source spelling
        return self.hatch_sp


ParamsLike: TypeAlias = GeneratorParams | Mapping[str, object] | object


def _value(params: ParamsLike, snake: str, camel: str, default: object) -> object:
    if isinstance(params, Mapping):
        if snake in params:
            return params[snake]
        if camel in params:
            return params[camel]
        return default
    if hasattr(params, snake):
        return getattr(params, snake)
    if hasattr(params, camel):
        return getattr(params, camel)
    return default


def coerce_params(params: ParamsLike | None = None) -> GeneratorParams:
    """Accept dataclasses, objects, or mappings using Python or JS field names."""

    if params is None:
        return GeneratorParams()
    if isinstance(params, GeneratorParams):
        return params
    vector = _value(params, "v", "v", (60.0, 70.0))
    if not isinstance(vector, Sequence) or len(vector) != 2:
        raise TypeError("v must be a two-number sequence")
    return GeneratorParams(
        s=float(_value(params, "s", "s", 104.0)),
        sh=float(_value(params, "sh", "sh", 100.0)),
        w=float(_value(params, "w", "w", 1.0)),
        v=(float(vector[0]), float(vector[1])),
        hatch_n=int(_value(params, "hatch_n", "hatchN", HATCH_N)),
        hatch_t=float(_value(params, "hatch_t", "hatchT", 9.0)),
        hatch_sp=float(_value(params, "hatch_sp", "hatchSp", 17.0)),
        jit=float(_value(params, "jit", "jit", 0.0)),
    )


def cut(hand_painted: bool = False) -> GeneratorParams:
    """Return the grid generator's exact default cut."""

    return GeneratorParams(jit=3.4 if hand_painted else 0.0)


def arc_pts(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    a0: float,
    a1: float,
    steps: int | None = None,
) -> list[RawPoint]:
    """Port of ``arcPts``; sample count depends only on angular span.

    ``steps`` pins the count for arcs whose terminal angle moves with the
    axis location, which would otherwise change the point topology.
    """

    n = steps if steps is not None else max(2, ceil(abs(a1 - a0) / 4))
    out: list[RawPoint] = []
    for i in range(n + 1):
        t = (a0 + (a1 - a0) * i / n) * pi / 180
        out.append((cx + rx * cos(t), cy + ry * sin(t), 1))
    return out


def rect(x0: float, y0: float, x1: float, y1: float) -> Contour:
    """Return the source rectangle contour."""

    return Contour([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)])


def quad(points: Sequence[Sequence[float]]) -> Contour:
    """Return the source polygon helper's flag-zero contour."""

    return Contour([(float(q[0]), float(q[1]), 0) for q in points])


def ring_sector(
    cx: float,
    cy: float,
    ro: float,
    ri: float,
    oa0: float,
    oa1: float,
    ia0: float,
    ia1: float,
    sx: float | None = None,
    caps: object = None,
) -> Contour:
    """Port of ``ringSector``, including its truthy ``sx || 1`` behavior."""

    x_scale = sx if sx else 1.0
    outer = arc_pts(cx, cy, ro * x_scale, ro, oa0, oa1)
    inner = arc_pts(cx, cy, ri * x_scale, ri, ia0, ia1)
    if caps:
        outer[-1] = (outer[-1][0], outer[-1][1], 2)
        inner[-1] = (inner[-1][0], inner[-1][1], 2)
    return Contour(outer + inner)


def ellipse(cx: float, cy: float, rx: float, ry: float) -> Contour:
    """Return the grid generator's 90-segment ellipse."""

    points = arc_pts(cx, cy, rx, ry, 0, 360)
    points.pop()
    return Contour(points)


def _piece(outer: Contour, holes: Sequence[Contour] | None = None) -> Piece:
    return Piece(outer, list(holes or ()))


CAP_COMPOSITES: dict[str, tuple[str, str]] = {
    "À": ("A", "grave"),
    "Á": ("A", "acute"),
    "Â": ("A", "circ"),
    "Ã": ("A", "tilde"),
    "Ä": ("A", "dier"),
    "Å": ("A", "ring"),
    "Ç": ("C", "ced"),
    "È": ("E", "grave"),
    "É": ("E", "acute"),
    "Ê": ("E", "circ"),
    "Ë": ("E", "dier"),
    "Ì": ("I", "grave"),
    "Í": ("I", "acute"),
    "Î": ("I", "circ"),
    "Ï": ("I", "dier"),
    "Ñ": ("N", "tilde"),
    "Ò": ("O", "grave"),
    "Ó": ("O", "acute"),
    "Ô": ("O", "circ"),
    "Õ": ("O", "tilde"),
    "Ù": ("U", "grave"),
    "Ú": ("U", "acute"),
    "Û": ("U", "circ"),
    "Ü": ("U", "dier"),
    "Ý": ("Y", "acute"),
}

LC_COMPOSITES: dict[str, tuple[str, str]] = {
    "à": ("a", "grave"),
    "á": ("a", "acute"),
    "â": ("a", "circ"),
    "ã": ("a", "tilde"),
    "ä": ("a", "dier"),
    "å": ("a", "ring"),
    "ç": ("c", "ced"),
    "è": ("e", "grave"),
    "é": ("e", "acute"),
    "ê": ("e", "circ"),
    "ë": ("e", "dier"),
    "ì": ("ı", "grave"),
    "í": ("ı", "acute"),
    "î": ("ı", "circ"),
    "ï": ("ı", "dier"),
    "ñ": ("n", "tilde"),
    "ò": ("o", "grave"),
    "ó": ("o", "acute"),
    "ô": ("o", "circ"),
    "õ": ("o", "tilde"),
    "ö": ("o", "dier"),
    "ù": ("u", "grave"),
    "ú": ("u", "acute"),
    "û": ("u", "circ"),
    "ü": ("u", "dier"),
    "ý": ("y", "acute"),
    "ÿ": ("y", "dier"),
}


def glyph_defs(
    params: ParamsLike | None = None,
    *,
    _nested: bool = False,
) -> dict[str, Builder]:
    """Return all 138 direct grid builders plus the CAP/LC compositions.

    Every builder is written against one stroke model, so a junction that is
    clean at Regular stays clean at every weight and width:

    * skeleton x positions scale with ``w``; stroke thickness follows ``s``;
    * a stroke's outer edge sits ``max(canonical, actual) / 2`` from its
      skeleton, so light cuts carve the counter and heavy cuts grow evenly;
    * vertical extremes stay on the alignment zones at every weight;
    * attached pieces are derived from the edges of their parent stroke and
      overlap it instead of abutting it.

    At the default cut the union of every glyph equals the canonical grid.
    """

    p = coerce_params(params)
    S, SH, W = p.s, p.sh, p.w
    ratio = S / 104.0
    heavy = max(1.0, ratio)
    # 0 at Regular and lighter, 1 at the heaviest designed stroke.
    heavy_progress = min(1.0, max(0.0, (S - 104.0) / 72.0))
    JOIN = max(6.0, 0.15 * S)

    # ------------------------------------------------------------ primitives

    def X(x: float) -> float:
        """Scale a canonical skeleton x position."""

        return x * W

    def tk(b: float = 104.0) -> float:
        """Vertical-stroke thickness for a canonical thickness ``b``."""

        return b * ratio

    def reach(b: float = 104.0) -> float:
        """Distance from a stroke's skeleton to its outer edge."""

        return b * heavy / 2.0

    Span: TypeAlias = tuple[float, float]

    def left(c: float, b: float = 104.0) -> Span:
        """x range of a stroke on skeleton ``c`` whose outer edge faces left."""

        edge = X(c) - reach(b)
        return edge, edge + tk(b)

    def right(c: float, b: float = 104.0) -> Span:
        """x range of a stroke on skeleton ``c`` whose outer edge faces right."""

        edge = X(c) + reach(b)
        return edge - tk(b), edge

    def centre(c: float, b: float = 104.0) -> Span:
        """x range of an interior stroke centred on skeleton ``c``."""

        half = tk(b) / 2.0
        return X(c) - half, X(c) + half

    def mid(span: Span) -> float:
        return (span[0] + span[1]) / 2.0

    def bar_t(b: float = 100.0) -> float:
        """Horizontal-stroke thickness; 104-unit bars follow the stem."""

        return S if abs(b - 104.0) < 1e-9 else b * SH / 100.0

    def top(y: float, b: float = 100.0) -> Span:
        """y range of a bar hanging from zone ``y``."""

        return y, y + bar_t(b)

    def bottom(y: float, b: float = 100.0) -> Span:
        """y range of a bar standing on zone ``y``."""

        return y - bar_t(b), y

    def around(y: float, b: float = 100.0) -> Span:
        """y range of an interior bar centred on ``y``."""

        half = bar_t(b) / 2.0
        return y - half, y + half

    def box(xs: Span, ys: Span) -> Contour:
        return rect(xs[0], ys[0], xs[1], ys[1])

    def pc(outer: Contour, holes: Sequence[Contour] | None = None) -> Piece:
        return _piece(outer, holes)

    def band(first: Span, y_first: float, second: Span, y_second: float) -> Contour:
        """Stroke with horizontal terminals ``first`` and ``second``."""

        return quad(
            [
                (first[0], y_first),
                (first[1], y_first),
                (second[1], y_second),
                (second[0], y_second),
            ]
        )

    def cap_width(b: float, run: float, rise: float) -> float:
        """Horizontal cut that keeps the canonical perpendicular thickness.

        ``run`` and ``rise`` describe the canonical stroke; the width axis
        changes the run, which would otherwise thin or fatten the diagonal.
        """

        return b * ratio * _js_hypot(run * W, rise) / _js_hypot(run, rise)

    def cap_l(c: float, width: float) -> Span:
        edge = X(c) - width * max(1.0, 1.0 / ratio) / 2.0
        return edge, edge + width

    def cap_r(c: float, width: float) -> Span:
        edge = X(c) + width * max(1.0, 1.0 / ratio) / 2.0
        return edge - width, edge

    def cap_c(c: float, width: float) -> Span:
        return X(c) - width / 2.0, X(c) + width / 2.0

    def at_y(first: Span, y_first: float, second: Span, y_second: float, y: float) -> float:
        """Centreline x of a band at height ``y``."""

        t = (y - y_first) / (y_second - y_first)
        return mid(first) + (mid(second) - mid(first)) * t

    def slab(
        a: Sequence[float],
        b: Sequence[float],
        width: float,
        cut_a: float | None = None,
        cut_b: float | None = None,
    ) -> Contour:
        """Band of perpendicular ``width`` along ``a``→``b`` in master space.

        ``cut_a``/``cut_b`` request a horizontal terminal at that height;
        otherwise the terminal is a butt cap.
        """

        dx, dy = b[0] - a[0], b[1] - a[1]
        length = _js_hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        px, py = -uy * width / 2.0, ux * width / 2.0

        def end(point: Sequence[float], cut: float | None) -> tuple[
            tuple[float, float], tuple[float, float]
        ]:
            first = (point[0] + px, point[1] + py)
            second = (point[0] - px, point[1] - py)
            if cut is None:
                return first, second
            return (
                (first[0] + ux * (cut - first[1]) / uy, cut),
                (second[0] + ux * (cut - second[1]) / uy, cut),
            )

        a1, a2 = end(a, cut_a)
        b1, b2 = end(b, cut_b)
        return quad([a1, b1, b2, a2])

    def stroke_w(width: float) -> float:
        """Thickness of a free stroke whose canonical value is ``width``."""

        return width if abs(width - S) < 1e-9 else width * ratio

    def bar(x1: float, y1: float, x2: float, y2: float, width: float) -> Piece:
        return pc(slab((X(x1), y1), (X(x2), y2), stroke_w(width)))

    # ---------------------------------------------------------------- rounds

    def radii(
        ro: float,
        ri: float,
        *,
        ty: float | None = None,
        k: float = 1.0,
    ) -> tuple[float, float, float, float]:
        """Return master ``(outer_rx, inner_rx, outer_ry, inner_ry)``.

        Horizontally the stroke follows the same edge rule as a stem, so a
        bowl and the stem it joins share one silhouette. Vertically the outer
        radius never leaves its alignment zone; weight grows into the counter
        and is limited before the counter closes.
        """

        b = ro - ri
        thickness = tk(b) * k
        outer_rx = (ro + ri) / 2.0 * W + max(b, thickness) / 2.0
        inner_rx = max(
            min(ri * W, max(16.0, ri * W * 0.35)),
            outer_rx - thickness,
        )
        outer_ry = ro
        inner_ry = max(
            min(ri, max(18.0, 0.38 * ro)),
            ro - (thickness if ty is None else ty),
        )
        return outer_rx, inner_rx, outer_ry, inner_ry

    def hook_radii(ro: float, ri: float) -> tuple[float, float, float, float]:
        """Radii for a short terminal hook (f, t, j, J).

        A hook is too small to absorb a heavy stroke, so above Regular it
        keeps its canonical counter and grows outward; its horizontal part is
        eased toward 70% of the stem so the terminal stays readable.
        """

        b = ro - ri
        thickness = tk(b)
        if ratio <= 1.0:
            outer_rx = (ro + ri) / 2.0 * W + reach(b)
            return outer_rx, outer_rx - thickness, ro, ro - thickness
        inner_rx = (ro + ri) / 2.0 * W - b / 2.0
        flat = thickness * (1.0 - 0.3 * heavy_progress)
        return inner_rx + thickness, inner_rx, ri + flat, ri

    def tangent(rx: float, ry: float, angle: float, sweep: float) -> tuple[float, float]:
        radians = angle * pi / 180.0
        sign = 1.0 if sweep >= 0 else -1.0
        dx, dy = -rx * sin(radians) * sign, ry * cos(radians) * sign
        length = _js_hypot(dx, dy) or 1.0
        return dx / length, dy / length

    def sector(
        cx: float,
        cy: float,
        outer_rx: float,
        inner_rx: float,
        outer_ry: float,
        inner_ry: float,
        oa0: float,
        oa1: float,
        ia0: float,
        ia1: float,
        caps: tuple[object, object] = (0, 0),
        tails: tuple[float, float] = (0.0, 0.0),
        steps: int | None = None,
    ) -> Contour:
        """Ring sector in master space.

        ``caps`` marks the (end, start) terminals as free forced caps.
        ``tails`` extends the (end, start) terminals along their tangent so
        an attached end overlaps its parent stroke. ``steps`` pins the sample
        count when a terminal angle depends on the axis location.
        """

        outer = arc_pts(cx, cy, outer_rx, outer_ry, oa0, oa1, steps)
        inner = arc_pts(cx, cy, inner_rx, inner_ry, ia0, ia1, steps)
        points: list[RawPoint] = list(outer)
        if caps[0]:
            points[-1] = (points[-1][0], points[-1][1], 2)
        if tails[0]:
            dx, dy = tangent(outer_rx, outer_ry, oa1, oa1 - oa0)
            points.append((outer[-1][0] + dx * tails[0], outer[-1][1] + dy * tails[0], 0))
            points.append((inner[0][0] + dx * tails[0], inner[0][1] + dy * tails[0], 0))
        points.extend(inner)
        if caps[1]:
            points[-1] = (points[-1][0], points[-1][1], 2)
        if tails[1]:
            dx, dy = tangent(inner_rx, inner_ry, ia1, ia1 - ia0)
            points.append((inner[-1][0] + dx * tails[1], inner[-1][1] + dy * tails[1], 0))
            points.append((outer[0][0] + dx * tails[1], outer[0][1] + dy * tails[1], 0))
        return Contour(points)

    def RS(
        cx: float,
        cy: float,
        ro: float,
        ri: float,
        oa0: float,
        oa1: float,
        ia0: float,
        ia1: float,
        caps: tuple[object, object] = (0, 0),
        tails: tuple[float, float] = (0.0, 0.0),
        ty: float | None = None,
        steps: int | None = None,
    ) -> Contour:
        outer_rx, inner_rx, outer_ry, inner_ry = radii(ro, ri, ty=ty)
        return sector(
            X(cx), cy, outer_rx, inner_rx, outer_ry, inner_ry,
            oa0, oa1, ia0, ia1, caps, tails, steps,
        )

    def arch(
        x0: float,
        x1: float,
        cy: float,
        ro: float,
        ri: float,
        oa0: float = 180.0,
        oa1: float = 360.0,
    ) -> Contour:
        """Arch between two outer x extents, overlapping both supports."""

        thickness = tk(ro - ri)
        outer_rx = (x1 - x0) / 2.0
        inner_rx = max(min(16.0, 0.5 * outer_rx), outer_rx - thickness)
        inner_ry = max(min(ri, max(18.0, 0.38 * ro)), ro - thickness)
        return sector(
            (x0 + x1) / 2.0, cy, outer_rx, inner_rx, ro, inner_ry,
            oa0, oa1, oa1, oa0, tails=(JOIN, JOIN),
        )

    def half_bowl(
        cx: float,
        first_center: float,
        second_center: float,
        rox: float,
        rix: float,
        side: str,
        stroke: float | None = None,
    ) -> Contour:
        """Half bowl whose ends share the centres of the bars it connects."""

        thickness = S if stroke is None else stroke
        cy = (first_center + second_center) / 2.0
        skeleton_ry = abs(second_center - first_center) / 2.0
        outer_ry = skeleton_ry + thickness / 2.0
        inner_ry = max(
            min(10.0, 0.5 * skeleton_ry),
            skeleton_ry - thickness / 2.0,
        )
        outer_rx, inner_rx, _unused_y, _unused_iy = radii(rox, rix)
        angles = (-90, 90, 90, -90) if side == "right" else (90, 270, 270, 90)
        return sector(
            X(cx), cy, outer_rx, inner_rx, outer_ry, inner_ry,
            *angles, tails=(JOIN, JOIN),
        )

    def ring_p(
        cx: float,
        cy: float,
        ro: float,
        ri: float,
        ty: float | None = None,
        k: float = 1.0,
    ) -> Piece:
        outer_rx, inner_rx, outer_ry, inner_ry = radii(ro, ri, ty=ty, k=k)
        return pc(
            ellipse(X(cx), cy, outer_rx, outer_ry),
            [ellipse(X(cx), cy, inner_rx, inner_ry)],
        )

    def ellipse_ring_p(
        cx: float,
        cy: float,
        rox: float,
        rix: float,
        roy: float,
        riy: float,
    ) -> Piece:
        outer_rx, inner_rx, _unused_y, _unused_iy = radii(rox, rix)
        _unused_x, _unused_ix, outer_ry, inner_ry = radii(roy, riy)
        return pc(
            ellipse(X(cx), cy, outer_rx, outer_ry),
            [ellipse(X(cx), cy, inner_rx, inner_ry)],
        )

    # ------------------------------------------------------------------ dots

    def dot_radius(radius: float, light: float = 1.0) -> float:
        """Dot size that tracks the stem instead of lagging behind it."""

        if ratio <= 1.0:
            return max(8.0, radius * ratio**light)
        return radius * ratio**0.9

    def dot_at(cx: float, cy: float, radius: float) -> Piece:
        return pc(ellipse(cx, cy, radius, radius))

    def point(cx: float, cy: float, radius: float) -> Piece:
        """Punctuation dot centred on a canonical position."""

        return dot_at(X(cx), cy, dot_radius(radius, 0.8))

    def base_point(cx: float, radius: float = 63.0) -> Piece:
        """Punctuation dot that sits on the baseline at every weight."""

        size = dot_radius(radius, 0.8)
        return dot_at(cx, 700.0 - size, size)

    def accent_disc(
        cx: float,
        cy: float,
        radius: float,
        pair: float | None = None,
    ) -> Piece:
        """Dieresis dot; heavy dots grow upward from a fixed clearance."""

        size = dot_radius(radius)
        if pair is not None:
            size = min(size, 0.84 * pair * W)
        if ratio > 1.0:
            cy = cy + radius - size
        return dot_at(X(cx), cy, size)

    # ------------------------------------------------------------ transforms
    def settle(pieces: Sequence[Piece], floor: float) -> list[Piece]:
        """Shift an accent so its lowest point rests on ``floor``.

        Accents keep one clearance above their base and grow upward; a
        centred accent would sink into the letter as the weight rises.
        """

        low = max(q[1] for piece in pieces for q in piece.outer.pts)
        return map_pieces(pieces, lambda q: (q[0], q[1] + floor - low, q[2]))

    def accent_w(width: float) -> float:
        """Accent stroke: in step when light, eased when heavy."""

        return width * (ratio if ratio <= 1.0 else ratio**0.7)

    def accent_bar(x1: float, y1: float, x2: float, y2: float, width: float, floor: float) -> list[Piece]:
        return settle([pc(slab((X(x1), y1), (X(x2), y2), accent_w(width)))], floor)

    def accent_chev(
        ax: float,
        ay: float,
        b1: Sequence[float],
        b2: Sequence[float],
        width: float,
        floor: float,
    ) -> list[Piece]:
        piece = chev_abs(
            (X(ax), ay),
            (X(b1[0]), b1[1]),
            (X(b2[0]), b2[1]),
            accent_w(width),
        )
        return settle([piece], floor)


    def map_pieces(
        pieces: Sequence[Piece], transform: Callable[[RawPoint], RawPoint]
    ) -> list[Piece]:
        return [
            Piece(
                Contour([transform(q) for q in piece.outer.pts]),
                [Contour([transform(q) for q in hole.pts]) for hole in piece.holes],
            )
            for piece in pieces
        ]

    def translate(pieces: Sequence[Piece], dx: float, dy: float) -> list[Piece]:
        return map_pieces(pieces, lambda q: (q[0] + dx * W, q[1] + dy, q[2]))

    def rotate_180(pieces: Sequence[Piece], cx: float, cy: float) -> list[Piece]:
        return map_pieces(pieces, lambda q: (2 * cx * W - q[0], 2 * cy - q[1], q[2]))

    def mirror_x(pieces: Sequence[Piece], axis_sum: float) -> list[Piece]:
        return map_pieces(pieces, lambda q: (axis_sum * W - q[0], q[1], q[2]))

    def scale(pieces: Sequence[Piece], factor: float) -> list[Piece]:
        return map_pieces(pieces, lambda q: (q[0] * factor, q[1] * factor, q[2]))

    def extent(pieces: Sequence[Piece]) -> Span:
        xs = [q[0] for piece in pieces for q in piece.outer.pts]
        return min(xs), max(xs)

    def wave(cx: float, cy: float, half_len: float, amp: float, half_w: float) -> Piece:
        upper: list[RawPoint] = []
        lower: list[RawPoint] = []
        # Bound the offset by the sinusoid's minimum radius of curvature.
        # Without this cap, Black Condensed tildes fold back through themselves.
        curvature_radius = (half_len * W) ** 2 / (amp * pi**2)
        effective_half_w = min(
            accent_w(half_w),
            0.72 * curvature_radius,
        )
        for i in range(41):
            t = i / 40
            x = (cx - half_len + 2 * half_len * t) * W
            y = cy - amp * sin(2 * pi * t)
            d = -amp * cos(2 * pi * t) * pi / (half_len * W)
            length = _js_hypot(1, d)
            nx, ny = d / length, -1 / length
            upper.append((x + nx * effective_half_w, y + ny * effective_half_w, 1))
            lower.append((x - nx * effective_half_w, y - ny * effective_half_w, 1))
        return pc(Contour(upper + list(reversed(lower))))

    def chev_abs(
        apex: Sequence[float],
        b1: Sequence[float],
        b2: Sequence[float],
        width: float,
    ) -> Piece:
        """Mitred two-arm chevron in master space."""

        ax, ay = apex

        def arm(b: Sequence[float]) -> tuple[float, float]:
            dx, dy = b[0] - ax, b[1] - ay
            length = _js_hypot(dx, dy) or 1.0
            return dx / length, dy / length

        u1, u2 = arm(b1), arm(b2)
        # The contour path is b1 → apex → b2. With both helpers expressed as
        # apex → endpoint, the incoming arm's normal must be reversed.
        n1, n2 = (u1[1], -u1[0]), (-u2[1], u2[0])

        def intersect_offsets(
            first: tuple[float, float],
            first_direction: tuple[float, float],
            second: tuple[float, float],
            second_direction: tuple[float, float],
        ) -> tuple[float, float]:
            den = (
                first_direction[0] * second_direction[1]
                - first_direction[1] * second_direction[0]
            )
            if abs(den) < 1e-9:
                return (first[0] + second[0]) / 2, (first[1] + second[1]) / 2
            t = (
                (second[0] - first[0]) * second_direction[1]
                - (second[1] - first[1]) * second_direction[0]
            ) / den
            return (
                first[0] + first_direction[0] * t,
                first[1] + first_direction[1] * t,
            )

        incoming = (-u1[0], -u1[1])

        def joins(
            active_width: float,
        ) -> tuple[
            tuple[float, float],
            tuple[float, float],
            tuple[float, float],
            tuple[float, float],
        ]:
            first_normal = (
                n1[0] * active_width / 2,
                n1[1] * active_width / 2,
            )
            second_normal = (
                n2[0] * active_width / 2,
                n2[1] * active_width / 2,
            )
            plus = intersect_offsets(
                (ax + first_normal[0], ay + first_normal[1]),
                incoming,
                (ax + second_normal[0], ay + second_normal[1]),
                u2,
            )
            minus = intersect_offsets(
                (ax - first_normal[0], ay - first_normal[1]),
                incoming,
                (ax - second_normal[0], ay - second_normal[1]),
                u2,
            )
            return first_normal, second_normal, plus, minus

        nn1, nn2, plus_join, minus_join = joins(width)
        miter = max(
            _js_hypot(plus_join[0] - ax, plus_join[1] - ay),
            _js_hypot(minus_join[0] - ax, minus_join[1] - ay),
        )
        arm_limit = 0.8 * min(
            _js_hypot(b1[0] - ax, b1[1] - ay),
            _js_hypot(b2[0] - ax, b2[1] - ay),
        )
        if miter > arm_limit and miter > 0:
            nn1, nn2, plus_join, minus_join = joins(width * arm_limit / miter)

        points = [
            (b1[0] + nn1[0], b1[1] + nn1[1]),
            plus_join,
            (b2[0] + nn2[0], b2[1] + nn2[1]),
            (b2[0] - nn2[0], b2[1] - nn2[1]),
            minus_join,
            (b1[0] - nn1[0], b1[1] - nn1[1]),
        ]
        return pc(Contour([(x, y, 0) for x, y in points]))

    def chev(
        ax: float,
        ay: float,
        b1: Sequence[float],
        b2: Sequence[float],
        width: float,
    ) -> Piece:
        return chev_abs(
            (X(ax), ay),
            (X(b1[0]), b1[1]),
            (X(b2[0]), b2[1]),
            width * ratio,
        )

    def corner_diagonal(
        upper: Sequence[float],
        lower: Sequence[float],
        thickness: float,
        y_clip: Span,
    ) -> Contour:
        """Z diagonal whose edges pass through two inner bar corners.

        ``upper`` is the bottom-right corner of the top bar and ``lower`` the
        top-left corner of the bottom bar. The six vertices keep one
        semantic order at every axis location.
        """

        dx, dy = lower[0] - upper[0], lower[1] - upper[1]
        span = _js_hypot(dx, dy) or 1.0
        # Rotate the corner-to-corner chord until the two parallel edges are
        # exactly ``thickness`` apart.
        swing = asin(min(0.95, thickness / span))
        base = atan2(dy, dx)
        direction = base - swing
        ux, uy = cos(direction), sin(direction)

        def x_on(edge_point: Sequence[float], y: float) -> float:
            return edge_point[0] + ux * (y - edge_point[1]) / uy

        y0, y1 = y_clip
        return quad(
            [
                (x_on(lower, y0), y0),
                (upper[0], y0),
                (upper[0], upper[1]),
                (x_on(upper, y1), y1),
                (lower[0], y1),
                (lower[0], lower[1]),
            ]
        )

    G: dict[str, Builder] = {}

    # ============================================================= capitals
    G["O"] = lambda: [ring_p(362, 350, 362, 258)]
    G["Ö"] = lambda: G["O"]() + [
        accent_disc(225.5, -115, 63, 136.5),
        accent_disc(498.5, -115, 63, 136.5),
    ]
    G["C"] = lambda: [pc(RS(362, 350, 362, 258, -38, -322, -330, -30, caps=(1, 1)))]

    def glyph_g_cap() -> list[Piece]:
        outer_rx, inner_rx, outer_ry, inner_ry = radii(362, 258)
        outer_right = X(362) + outer_rx
        terminal_left = outer_right - tk(116)
        bury = max(4.0, 0.08 * S)

        def meets(radius_x: float, limit: float) -> float:
            # Largest angle at which this radius is still inside the terminal.
            cosine = min(1.0, max(0.0, (terminal_left + bury - X(362)) / radius_x))
            return min(limit, atan2(sqrt(1 - cosine * cosine), cosine) * 180 / pi)

        outer_end = meets(outer_rx, 38.0)
        inner_end = meets(inner_rx, 15.0)
        return [
            pc(
                sector(
                    X(362), 350, outer_rx, inner_rx, outer_ry, inner_ry,
                    -38, -360 + outer_end, -360 + inner_end, -30,
                    caps=(1, 1), steps=71,
                )
            ),
            pc(rect(terminal_left, 325, outer_right, 700)),
        ]

    G["G"] = glyph_g_cap

    def glyph_h_cap() -> list[Piece]:
        first, second = left(52), right(578)
        return [
            pc(box(first, (0, 700))),
            pc(box(second, (0, 700))),
            pc(box((mid(first), mid(second)), around(371))),
        ]

    G["H"] = glyph_h_cap

    def glyph_e_cap() -> list[Piece]:
        stem = left(52)
        return [
            pc(box(stem, (0, 700))),
            pc(box((mid(stem), X(590)), top(0))),
            pc(box((mid(stem), X(425)), around(360))),
            pc(box((mid(stem), X(596)), bottom(700))),
        ]

    G["E"] = glyph_e_cap

    def glyph_l_cap() -> list[Piece]:
        stem = left(52)
        return [pc(box(stem, (0, 700))), pc(box((mid(stem), X(615)), bottom(700)))]

    G["L"] = glyph_l_cap
    G["T"] = lambda: [
        pc(box((X(0), X(700)), top(0, 104))),
        pc(box(centre(350), (0, 700))),
    ]
    G["I"] = lambda: [pc(box(left(52), (0, 700)))]

    def glyph_s_cap() -> list[Piece]:
        top_center = S / 2
        middle_center = 345
        bottom_center = 700 - S / 2
        return [
            pc(box((X(198.5), X(690)), (0, S))),
            pc(half_bowl(198.5, top_center, middle_center, 198.5, 94.5, "left")),
            pc(box((X(198.5), X(501.5)), (middle_center - S / 2, middle_center + S / 2))),
            pc(half_bowl(501.5, middle_center, bottom_center, 203.5, 99.5, "right")),
            pc(box((X(10), X(501.5)), (700 - S, 700))),
        ]

    G["S"] = glyph_s_cap

    def glyph_b_cap() -> list[Piece]:
        stem = left(52)
        top_center = S / 2
        middle_center = 350
        bottom_center = 700 - S / 2
        return [
            pc(box(stem, (0, 700))),
            pc(box((mid(stem), X(404)), (0, S))),
            pc(box((mid(stem), X(419)), (350 - S / 2, 350 + S / 2))),
            pc(box((mid(stem), X(419)), (700 - S, 700))),
            pc(half_bowl(404, top_center, middle_center, 201, 97, "right")),
            pc(half_bowl(419, middle_center, bottom_center, 201, 97, "right")),
        ]

    G["B"] = glyph_b_cap

    def glyph_p_cap() -> list[Piece]:
        stem = left(52)
        top_center = S / 2
        lower_center = 371
        return [
            pc(box(stem, (0, 700))),
            pc(box((mid(stem), X(393.5)), (0, S))),
            pc(box((mid(stem), X(393.5)), (lower_center - S / 2, lower_center + S / 2))),
            pc(half_bowl(393.5, top_center, lower_center, 211.5, 107.5, "right")),
        ]

    G["P"] = glyph_p_cap

    def glyph_r() -> list[Piece]:
        # The leg keeps the canonical axis and thickness; its top is cut at
        # the upper edge of the middle bar, where it is buried in the bowl.
        axis_top = (X(480), 380.0)
        axis_bottom = (X(480) + 146.799 * W, 700.0)
        return G["P"]() + [
            pc(slab(axis_top, axis_bottom, S, cut_a=371 - S / 2, cut_b=700.0))
        ]

    G["R"] = glyph_r

    def glyph_m_cap() -> list[Piece]:
        first, second = left(52), right(718)
        center = X(385)
        left_inner, right_inner = first[1], second[0]
        top_inset = 49.48120950323974 * ratio
        inner_apex_y = 381.470462633452
        outer_apex_y = inner_apex_y + (
            487.9110320284698 - inner_apex_y
        ) * ratio
        outer_cap_half = 48 * ratio
        return [
            pc(box(first, (0, 700))),
            pc(box(second, (0, 700))),
            pc(
                quad(
                    [
                        (mid(first), 0),
                        (left_inner + top_inset, 0),
                        (center, inner_apex_y),
                        (right_inner - top_inset, 0),
                        (mid(second), 0),
                        (mid(second), S),
                        (right_inner, S),
                        (center + outer_cap_half, outer_apex_y),
                        (center - outer_cap_half, outer_apex_y),
                        (left_inner, S),
                        (mid(first), S),
                    ]
                )
            ),
        ]

    G["M"] = glyph_m_cap

    def glyph_n_cap() -> list[Piece]:
        first, second = left(52), right(573)
        width = cap_width(129.7, 495.3, 700)
        return [
            pc(box(first, (0, 700))),
            pc(box(second, (0, 700))),
            pc(band((first[0], first[0] + width), 0, (second[1] - width, second[1]), 700)),
        ]

    G["N"] = glyph_n_cap

    def glyph_a_cap() -> list[Piece]:
        width = cap_width(104, 302, 700)
        apex, foot_l, foot_r = cap_c(354, width), cap_l(52, width), cap_r(656, width)
        bar_y = around(490)
        return [
            pc(band(apex, 0, foot_l, 700)),
            pc(band(apex, 0, foot_r, 700)),
            pc(
                box(
                    (at_y(apex, 0, foot_l, 700, 490), at_y(apex, 0, foot_r, 700, 490)),
                    bar_y,
                )
            ),
        ]

    G["A"] = glyph_a_cap

    def glyph_d_cap() -> list[Piece]:
        stem = left(52)
        return [
            pc(box(stem, (0, 700))),
            pc(box((mid(stem), X(340)), (0, S))),
            pc(box((mid(stem), X(340)), (700 - S, 700))),
            pc(RS(340, 350, 350, 246, -90, 90, 90, -90, tails=(JOIN, JOIN))),
        ]

    G["D"] = glyph_d_cap

    def glyph_f_cap() -> list[Piece]:
        stem = left(52)
        return [
            pc(box(stem, (0, 700))),
            pc(box((mid(stem), X(590)), top(0))),
            pc(box((mid(stem), X(425)), around(360))),
        ]

    G["F"] = glyph_f_cap

    def glyph_j_cap() -> list[Piece]:
        stem = right(448)
        outer_rx, inner_rx, outer_ry, inner_ry = hook_radii(153, 49)
        cx, cy = stem[1] - outer_rx, 700 - outer_ry
        return [
            pc(box(stem, (0, cy + 3))),
            pc(
                sector(
                    cx, cy, outer_rx, inner_rx, outer_ry, inner_ry,
                    0, 180, 180, 0, caps=(1, 0), tails=(0.0, JOIN),
                )
            ),
        ]

    G["J"] = glyph_j_cap

    def kay(
        top_y: float,
        arm: tuple[float, float, float, float],
        leg: tuple[float, float, float],
    ) -> list[Piece]:
        """K/k: stem, upper arm with a butt terminal, and a baseline leg."""

        stem = left(52)
        ax, ay, bx, by = arm
        a = (mid(stem) + (ax - 52) * ratio, ay)
        run, drop = X(bx) - a[0], by - ay
        length = _js_hypot(run, drop) or 1.0
        nx, ny = abs(drop) / length, abs(run) / length
        canonical = _js_hypot(bx - ax, by - ay)
        tip_y = by - 52 * abs(bx - ax) / canonical
        slack = reach() - S / 2
        b = (X(bx) + slack * nx, tip_y + S / 2 * ny)
        fraction, offset, foot = leg
        leg_top = (
            a[0] + (b[0] - a[0]) * fraction,
            a[1] + (b[1] - a[1]) * fraction + offset,
        )
        foot_run = X(foot) - leg_top[0]
        cosine = (700 - leg_top[1]) / (_js_hypot(foot_run, 700 - leg_top[1]) or 1.0)
        leg_bottom = (X(foot) + slack / cosine, 700.0)
        return [
            pc(box(stem, (top_y, 700))),
            pc(slab(a, b, S)),
            pc(slab(leg_top, leg_bottom, S, cut_b=700.0)),
        ]

    G["K"] = lambda: kay(
        0,
        (50, 478, 590, 48),
        (190 / 540, 335 - (478 - 430 * 190 / 540), 620),
    )
    G["Q"] = lambda: G["O"]() + [bar(440, 460, 760, 790, S)]

    def glyph_u_cap() -> list[Piece]:
        return [
            pc(box(left(52), (0, 400))),
            pc(box(right(578), (0, 400))),
            pc(RS(315, 397, 315, 211, 180, 0, 0, 180, tails=(JOIN, JOIN))),
        ]

    G["U"] = glyph_u_cap

    def glyph_v_cap() -> list[Piece]:
        width = cap_width(104, 285, 700)
        apex = cap_c(337, width)
        return [
            pc(band(cap_l(52, width), 0, apex, 700)),
            pc(band(cap_r(622, width), 0, apex, 700)),
        ]

    G["V"] = glyph_v_cap

    def glyph_w_cap() -> list[Piece]:
        width = cap_width(104, 214, 670)
        low_l, low_r, peak = cap_c(240, width), cap_c(720, width), cap_c(480, width)
        return [
            pc(band(cap_l(52, width), 0, low_l, 700)),
            pc(band(low_l, 700, peak, 60)),
            pc(band(peak, 60, low_r, 700)),
            pc(band(low_r, 700, cap_r(908, width), 0)),
        ]

    G["W"] = glyph_w_cap

    def glyph_x_cap() -> list[Piece]:
        width = cap_width(104, 540, 700)
        return [
            pc(band(cap_l(52, width), 0, cap_r(592, width), 700)),
            pc(band(cap_r(592, width), 0, cap_l(52, width), 700)),
        ]

    G["X"] = glyph_x_cap

    def glyph_y_cap() -> list[Piece]:
        width = cap_width(104, 270, 380)
        stem = centre(320)
        return [
            pc(band(cap_l(52, width), 0, stem, 380)),
            pc(band(cap_r(588, width), 0, stem, 380)),
            pc(box(stem, (360, 700))),
        ]

    G["Y"] = glyph_y_cap

    def zed(x0: float, x1: float, y0: float, y1: float, b: float, thickness: float) -> list[Piece]:
        upper_bar, lower_bar = top(y0, b), bottom(y1, b)
        bury = 0.3 * bar_t(b)
        return [
            pc(box((X(x0), X(x1)), upper_bar)),
            pc(box((X(x0), X(x1)), lower_bar)),
            pc(
                corner_diagonal(
                    (X(x1), upper_bar[1]),
                    (X(x0), lower_bar[0]),
                    thickness * ratio,
                    (upper_bar[1] - bury, lower_bar[0] + bury),
                )
            ),
        ]

    G["Z"] = lambda: zed(0, 620, 0, 700, 100, 110.59591548657296)

    # =============================================================== digits
    G["0"] = lambda: [ellipse_ring_p(310, 350, 310, 206, 362, 258)]

    def glyph_one() -> list[Piece]:
        stem = centre(202)
        # The flag hangs from the stem's top-left corner at every weight.
        length = 150.0 + 0.5 * max(0.0, S - 104.0)
        ux, uy = -0.743 * W, 0.669
        norm = _js_hypot(ux, uy)
        ux, uy = ux / norm, uy / norm
        px, py = -uy, ux
        if py < 0:
            px, py = -px, -py
        a = (stem[0], 0.0)
        b = (a[0] + ux * length, a[1] + uy * length)
        c = (b[0] + px * S, b[1] + py * S)
        d = (a[0] + px * S, a[1] + py * S)
        return [pc(box(stem, (0, 700))), pc(quad([a, b, c, d]))]

    G["1"] = glyph_one

    def glyph_two() -> list[Piece]:
        outer_rx, inner_rx, outer_ry, inner_ry = radii(322, 218)
        cx = X(322)
        # A heavy base rises toward the hook; ending the hook sooner keeps
        # the wedge between neck and base open.
        end = 30 - 15 * heavy_progress
        angle = end * pi / 180
        inner_cap = (cx + inner_rx * cos(angle), 322 + inner_ry * sin(angle))
        outer_cap = (cx + outer_rx * cos(angle), 322 + outer_ry * sin(angle))
        base = bottom(700)
        x_left = cx - outer_rx
        # The neck tapers; a light cut keeps more of it so it does not vanish.
        foot = (x_left + 140 * (ratio**0.6 if ratio < 1.0 else ratio), base[0])
        heel = (x_left, base[0])
        nub = 0.4 * bar_t()

        def toward(a: tuple[float, float], b: tuple[float, float]) -> RawPoint:
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = _js_hypot(dx, dy) or 1.0
            return (a[0] + dx / length * JOIN, a[1] + dy / length * JOIN, 0)

        outer = arc_pts(cx, 322, outer_rx, outer_ry, 180, 360 + end, 53)
        inner = arc_pts(cx, 322, inner_rx, inner_ry, 360 + end, 180, 53)
        inner[-1] = (inner[-1][0], inner[-1][1], 2)
        hook = Contour(
            outer + [toward(outer_cap, foot), toward(inner_cap, heel)] + inner
        )
        return [
            pc(hook),
            pc(
                quad(
                    [
                        inner_cap,
                        outer_cap,
                        foot,
                        (foot[0], base[0] + nub),
                        (x_left, base[0] + nub),
                        heel,
                    ]
                )
            ),
            pc(box((x_left, cx + outer_rx - 4 * ratio), base)),
        ]

    G["2"] = glyph_two

    def glyph_three() -> list[Piece]:
        top_center = S / 2
        middle_center = 308
        bottom_center = 700 - S / 2
        return [
            pc(box((X(80), X(320)), (0, S))),
            pc(half_bowl(320, top_center, middle_center, 180, 76, "right")),
            pc(box((X(190), X(320)), (middle_center - S / 2, middle_center + S / 2))),
            pc(half_bowl(320, middle_center, bottom_center, 222, 118, "right")),
            pc(box((X(70), X(320)), (700 - S, 700))),
        ]

    G["3"] = glyph_three

    def glyph_four() -> list[Piece]:
        stem = centre(482)
        bar_y = around(530)
        half = S / 2
        foot_center = mid(stem) - 415 * W * 520 / 486

        def edge_x(side: float, y: float) -> float:
            return mid(stem) + (foot_center - mid(stem)) * y / 520 + side * half

        # The diagonal's outer edge lands on the crossbar's top-left corner.
        corner = edge_x(-1, bar_y[0])
        bury = bar_y[0] + 0.4 * bar_t()
        return [
            pc(box(stem, (0, 700))),
            pc(box((corner, X(620)), bar_y)),
            pc(
                quad(
                    [
                        (stem[0], 0),
                        (stem[1], 0),
                        (edge_x(1, bury), bury),
                        (corner, bury),
                        (corner, bar_y[0]),
                    ]
                )
            ),
        ]

    G["4"] = glyph_four

    def glyph_five() -> list[Piece]:
        stem = left(142)
        middle_center = 336
        bottom_center = 700 - S / 2
        return [
            pc(box((mid(stem), X(650)), top(0))),
            pc(box(stem, (0, middle_center + S / 2))),
            pc(box((mid(stem), X(470)), (middle_center - S / 2, middle_center + S / 2))),
            pc(half_bowl(470, middle_center, bottom_center, 208, 104, "right")),
            pc(box((X(96), X(470)), (700 - S, 700))),
        ]

    G["5"] = glyph_five
    G["6"] = lambda: [
        ring_p(322, 462, 250, 146),
        pc(box(left(124), (290, 462))),
        pc(RS(362, 290, 290, 186, 180, 310, 310, 180, caps=(1, 0), tails=(0.0, JOIN))),
    ]

    def glyph_seven() -> list[Piece]:
        bar_y = top(0)
        width = cap_width(142, 328, 600)
        foot = cap_c(221, width)
        corner = X(620)
        # The diagonal leaves from the bar's lower right corner; above it the
        # stroke is buried in the bar and shares the bar's vertical end.
        bury = bar_y[1] - 0.5 * bar_t()
        lean = (foot[1] - corner) / (700 - bar_y[1])
        return [
            pc(box((X(0), corner), bar_y)),
            pc(
                quad(
                    [
                        (corner - width + lean * (bury - bar_y[1]), bury),
                        (corner, bury),
                        (corner, bar_y[1]),
                        (foot[1], 700),
                        (foot[0], 700),
                    ]
                )
            ),
        ]

    G["7"] = glyph_seven
    G["8"] = lambda: [ring_p(310, 168, 180, 76), ring_p(310, 512, 200, 96)]
    G["9"] = lambda: rotate_180(G["6"](), 322, 356)

    # ============================================================ lowercase
    def bowl() -> Piece:
        return ring_p(262, 450, 262, 158)

    G["a"] = lambda: [bowl(), pc(box(right(472), (195, 700)))]
    G["b"] = lambda: [pc(box(left(52), (0, 700))), bowl()]
    G["c"] = lambda: [pc(RS(262, 450, 262, 158, -35, -325, -333, -27, caps=(1, 1)))]
    G["d"] = lambda: [bowl(), pc(box(right(472), (0, 700)))]

    def three_strokes(height: float, counters: float) -> float:
        """Stroke for three stacked horizontals inside ``height``."""

        return min(S, (height - 0.45 * counters) / 3.0)

    def e_parts(cx: float, ro: float, ri: float) -> list[Piece]:
        stroke = three_strokes(2 * ro, 2 * ri - 100.0)
        outer_rx, inner_rx, outer_ry, _inner_ry = radii(ro, ri, ty=stroke)
        bar_h = min(SH, stroke * 100.0 / 104.0)
        # The ring runs down to the underside of the bar, so the terminal
        # corner sits exactly on the outer curve at every weight.
        tuck_sin = (bar_h / 2) / outer_ry
        tuck = asin(tuck_sin) * 180 / pi
        return [
            pc(
                RS(
                    cx, 450, ro, ri, 38, 360 + tuck, 360 + tuck, 38,
                    caps=(1, 1), ty=stroke, steps=82,
                )
            ),
            pc(
                box(
                    (
                        X(cx) - (outer_rx + inner_rx) / 2,
                        X(cx) + outer_rx * sqrt(1 - tuck_sin * tuck_sin),
                    ),
                    (450 - bar_h / 2, 450 + bar_h / 2),
                )
            ),
        ]

    G["e"] = lambda: e_parts(262, 262, 158)

    def glyph_f() -> list[Piece]:
        stem = centre(252)
        outer_rx, inner_rx, outer_ry, inner_ry = hook_radii(150, 46)
        cx, cy = stem[0] + outer_rx, outer_ry
        return [
            pc(
                sector(
                    cx, cy, outer_rx, inner_rx, outer_ry, inner_ry,
                    180, 270, 270, 180, caps=(1, 0), tails=(0.0, JOIN),
                )
            ),
            pc(box(stem, (cy, 700))),
            pc(box((mid(stem) - 222 * W, mid(stem) + 218 * W), top(200))),
        ]

    G["f"] = glyph_f
    def glyph_g() -> list[Piece]:
        # An eased, shorter tail keeps clear of the bowl when heavy.
        end = 150 - 20 * heavy_progress
        flat = tk() * (1 - 0.25 * heavy_progress)
        return [
            bowl(),
            pc(box(right(472), (195, 660))),
            pc(
                RS(
                    284, 660, 240, 136, 0, end, end, 0,
                    caps=(1, 0), tails=(0.0, JOIN), ty=flat, steps=38,
                )
            ),
        ]

    G["g"] = glyph_g
    G["h"] = lambda: [
        pc(box(left(52), (0, 700))),
        pc(RS(262, 462, 262, 158, 180, 360, 360, 180, tails=(JOIN, JOIN))),
        pc(box(right(472), (462, 700))),
    ]

    def dotted(stem: Span, y0: float, y1: float) -> list[Piece]:
        return [
            pc(box(stem, (y0, y1))),
            dot_at(mid(stem), 75, dot_radius(55)),
        ]

    G["i"] = lambda: dotted(left(52), 200, 700)
    G["ı"] = lambda: [pc(box(left(52), (200, 700)))]

    def glyph_j() -> list[Piece]:
        stem = right(202)
        outer_rx, inner_rx, outer_ry, inner_ry = hook_radii(153, 49)
        cx, cy = stem[1] - outer_rx, 900 - outer_ry
        return [
            pc(box(stem, (200, cy + 13))),
            pc(
                sector(
                    cx, cy, outer_rx, inner_rx, outer_ry, inner_ry,
                    0, 150, 150, 0, caps=(1, 0), tails=(0.0, JOIN),
                )
            ),
            dot_at(mid(stem), 75, dot_radius(55)),
        ]

    G["j"] = glyph_j
    G["k"] = lambda: kay(
        0,
        (60, 485, 440, 205),
        (175 / 380, 345 - (485 - 280 * 175 / 380), 470),
    )
    G["l"] = lambda: [pc(box(left(52), (0, 700)))]

    def glyph_m() -> list[Piece]:
        first, middle, last = left(52), centre(414), right(776)
        return [
            pc(box(first, (200, 700))),
            pc(arch(first[0], middle[1], 433, 233, 129)),
            pc(box(middle, (433, 700))),
            pc(arch(middle[0], last[1], 433, 233, 129)),
            pc(box(last, (433, 700))),
        ]

    G["m"] = glyph_m
    G["n"] = lambda: [
        pc(box(left(52), (200, 700))),
        pc(RS(262, 462, 262, 158, 180, 360, 360, 180, tails=(JOIN, JOIN))),
        pc(box(right(472), (462, 700))),
    ]
    G["o"] = lambda: [bowl()]
    G["p"] = lambda: [pc(box(left(52), (200, 900))), bowl()]
    G["q"] = lambda: [bowl(), pc(box(right(472), (200, 900)))]
    G["r"] = lambda: [
        pc(box(left(52), (200, 700))),
        pc(RS(240, 440, 240, 136, 180, 310, 310, 180, caps=(1, 0), tails=(0.0, JOIN))),
    ]

    def glyph_s_lower() -> list[Piece]:
        stroke = three_strokes(508, 196)
        top_center = 204 + stroke / 2
        middle_center = 448
        bottom_center = 712 - stroke / 2
        half = stroke / 2
        return [
            pc(box((X(148), X(500)), (top_center - half, top_center + half))),
            pc(half_bowl(148, top_center, middle_center, 148, 44, "left", stroke)),
            pc(box((X(148), X(352)), (middle_center - half, middle_center + half))),
            pc(half_bowl(352, middle_center, bottom_center, 158, 54, "right", stroke)),
            pc(box((X(10), X(352)), (bottom_center - half, bottom_center + half))),
        ]

    G["s"] = glyph_s_lower

    def glyph_t() -> list[Piece]:
        stem = left(182)
        outer_rx, inner_rx, outer_ry, inner_ry = hook_radii(140, 36)
        cx, cy = stem[0] + outer_rx, 700 - outer_ry
        return [
            pc(box(stem, (80, cy))),
            pc(box((mid(stem) - 182 * W, mid(stem) + 238 * W), top(200))),
            pc(
                sector(
                    cx, cy, outer_rx, inner_rx, outer_ry, inner_ry,
                    180, 0, 0, 180, caps=(1, 0), tails=(0.0, JOIN),
                )
            ),
        ]

    G["t"] = glyph_t
    G["u"] = lambda: [
        pc(box(left(52), (200, 440))),
        pc(RS(262, 438, 262, 158, 180, 0, 0, 180, tails=(JOIN, JOIN))),
        pc(box(right(472), (200, 700))),
    ]

    def glyph_v() -> list[Piece]:
        width = cap_width(104, 208, 500)
        apex = cap_c(260, width)
        return [
            pc(band(cap_l(52, width), 200, apex, 700)),
            pc(band(cap_r(468, width), 200, apex, 700)),
        ]

    G["v"] = glyph_v

    def glyph_w() -> list[Piece]:
        width = cap_width(104, 174, 480)
        low_l, low_r, peak = cap_c(192, width), cap_c(608, width), cap_c(400, width)
        return [
            pc(band(cap_l(52, width), 200, low_l, 700)),
            pc(band(low_l, 700, peak, 240)),
            pc(band(peak, 240, low_r, 700)),
            pc(band(low_r, 700, cap_r(748, width), 200)),
        ]

    G["w"] = glyph_w

    def glyph_x() -> list[Piece]:
        width = cap_width(104, 396, 500)
        return [
            pc(band(cap_l(52, width), 200, cap_r(448, width), 700)),
            pc(band(cap_r(448, width), 200, cap_l(52, width), 700)),
        ]

    G["x"] = glyph_x

    def glyph_y() -> list[Piece]:
        width = cap_width(104, 356, 700)
        long_top, long_bottom = cap_r(468, width), cap_c(112, width)
        short_width = cap_width(104, 186, 455)
        joint = at_y(long_top, 200, long_bottom, 900, 655)
        return [
            pc(band(long_top, 200, long_bottom, 900)),
            pc(
                band(
                    cap_l(52, short_width),
                    200,
                    (joint - width / 2, joint + width / 2),
                    655,
                )
            ),
        ]

    G["y"] = glyph_y
    G["z"] = lambda: zed(20, 520, 200, 700, 96, 94.1409813428312)

    # ====================================================== ASCII punctuation
    def exclamation(stem: Span) -> list[Piece]:
        size = dot_radius(63, 0.8)
        gap = 104.0 - 30.0 * heavy_progress
        return [
            pc(box(stem, (0, 700 - 2 * size - gap))),
            dot_at(mid(stem), 700 - size, size),
        ]

    G["!"] = lambda: exclamation(left(52))

    def tick_width() -> float:
        return 90 * ratio if ratio <= 1.0 else 90 * ratio**0.8

    def glyph_quotedbl() -> list[Piece]:
        width = tick_width()
        gap = 80 * ratio**0.3 * W
        return [
            pc(rect(0, 0, width, 210)),
            pc(rect(width + gap, 0, 2 * width + gap, 210)),
        ]

    G['"'] = glyph_quotedbl

    def glyph_hash() -> list[Piece]:
        return [
            pc(box(centre(195, 90), (60, 640))),
            pc(box(centre(425, 90), (60, 640))),
            pc(box((X(0), X(620)), around(240, 80))),
            pc(box((X(0), X(620)), around(460, 80))),
        ]

    G["#"] = glyph_hash
    G["$"] = lambda: G["S"]() + [pc(box(centre(348, 76), (-70, 770)))]

    def glyph_percent() -> list[Piece]:
        width = cap_width(104, 504, 700)
        away = 0.4 * max(0.0, tk(90) - 90) / W
        return [
            ring_p(150 - away, 150, 150, 60),
            ring_p(490 + away, 550, 150, 60),
            pc(band(cap_c(572, width), 0, cap_c(68, width), 700)),
        ]

    G["%"] = glyph_percent

    def axis_exit(
        a: Sequence[float],
        b: Sequence[float],
        cx: float,
        cy: float,
        ro: float,
        ri: float,
    ) -> tuple[float, float]:
        """Point where the axis ``a``→``b`` leaves a ring's stroke centreline."""

        outer_rx, inner_rx, outer_ry, inner_ry = radii(ro, ri)
        rx, ry = (outer_rx + inner_rx) / 2, (outer_ry + inner_ry) / 2
        px, py = (a[0] - X(cx)) / rx, (a[1] - cy) / ry
        dx, dy = (b[0] - a[0]) / rx, (b[1] - a[1]) / ry
        qa, qb, qc = dx * dx + dy * dy, 2 * (px * dx + py * dy), px * px + py * py - 1
        root = sqrt(max(0.0, qb * qb - 4 * qa * qc))
        t = (-qb + root) / (2 * qa)
        return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t

    def glyph_ampersand() -> list[Piece]:
        # Both strokes keep their canonical axis and start where that axis
        # leaves the centreline of the ring they grow from.
        leg_start = axis_exit((X(310), 230), (X(620), 690), 230, 170, 170, 66)
        arm_start = axis_exit((X(400.5), 564.5), (X(690), 320), 250, 470, 230, 126)
        leg_run, leg_drop = X(620) - leg_start[0], 690 - leg_start[1]
        leg_len = _js_hypot(leg_run, leg_drop) or 1.0
        foot_y = 719.1 - S / 2 * abs(leg_run) / leg_len
        # The arm keeps its canonical, slightly flared terminals.
        arm_end = (X(690), 320.0)
        near = (36.5 * ratio, 22.5 * ratio)
        far = (34.0 * ratio, 40.0 * ratio)
        return [
            ring_p(250, 470, 230, 126),
            ring_p(230, 170, 170, 66),
            pc(slab(leg_start, (X(620), foot_y), S)),
            pc(
                quad(
                    [
                        (arm_start[0] - near[0], arm_start[1] - near[1]),
                        (arm_start[0] + near[0], arm_start[1] + near[1]),
                        (arm_end[0] + far[0], arm_end[1] + far[1]),
                        (arm_end[0] - far[0], arm_end[1] - far[1]),
                    ]
                )
            ),
        ]

    G["&"] = glyph_ampersand
    G["'"] = lambda: [pc(rect(0, 0, tick_width(), 210))]
    G["("] = lambda: [pc(RS(560, 350, 560, 456, 128, 232, 232, 128, caps=(1, 1)))]
    G[")"] = lambda: mirror_x(G["("](), 230)

    def glyph_asterisk() -> list[Piece]:
        # A heavy asterisk keeps six readable arms instead of filling in.
        width = 84 * min(1.0, ratio) * heavy**0.4
        grow = heavy**0.35
        cx, cy = X(200), 180.0
        spokes = []
        for dx, dy in ((0.0, 140.0), (121.0, 70.0), (121.0, -70.0)):
            dx, dy = dx * W * grow, dy * grow
            spokes.append(pc(slab((cx - dx, cy - dy), (cx + dx, cy + dy), width)))
        return spokes

    G["*"] = glyph_asterisk
    G["+"] = lambda: [
        pc(box((X(0), X(440)), around(360))),
        pc(box(centre(220, 100), (140, 580))),
    ]

    def comma_parts(cx: float) -> list[Piece]:
        size = dot_radius(63, 0.8)
        factor = size / 63.0
        cy = 700 - size
        length = 165 * (0.5 + 0.5 * factor)
        return [
            dot_at(cx, cy, size),
            pc(
                band(
                    (cx - 43 * factor, cx + 43 * factor),
                    cy + 13 * factor,
                    (cx - 79 * factor, cx - 11 * factor),
                    cy + 13 * factor + length,
                )
            ),
        ]

    G[","] = lambda: comma_parts(X(63))
    G["-"] = lambda: [pc(box((X(0), X(400)), around(360)))]
    G["­"] = lambda: [pc(box((X(0), X(400)), around(360)))]
    G["."] = lambda: [base_point(X(63))]

    def glyph_slash() -> list[Piece]:
        width = cap_width(104, 356, 700)
        return [pc(band(cap_r(408, width), 0, cap_l(52, width), 700))]

    G["/"] = glyph_slash
    G[":"] = lambda: [point(63, 315, 63), base_point(X(63))]
    G[";"] = lambda: [point(63, 315, 63)] + comma_parts(X(63))
    G["<"] = lambda: [chev(50, 360, (430, 155), (430, 565), 96)]

    def glyph_equal() -> list[Piece]:
        thickness = bar_t(90)
        offset = 95 + 0.25 * max(0.0, thickness - 90)
        return [
            pc(rect(0, 380 - offset - thickness / 2, X(440), 380 - offset + thickness / 2)),
            pc(rect(0, 380 + offset - thickness / 2, X(440), 380 + offset + thickness / 2)),
        ]

    G["="] = glyph_equal
    G[">"] = lambda: mirror_x(G["<"](), 480)

    def glyph_question() -> list[Piece]:
        outer_rx, inner_rx, outer_ry, inner_ry = radii(210, 106)
        stem = (X(300), X(300) + S)
        size = dot_radius(63, 0.8)
        gap = 84.0 - 30.0 * heavy_progress
        return [
            pc(RS(300, 210, 210, 106, 215, 450, 450, 215, caps=(0, 1))),
            pc(box(stem, (210 + inner_ry, 700 - 2 * size - gap))),
            dot_at(mid(stem), 700 - size, size),
        ]

    G["?"] = glyph_question

    def glyph_at() -> list[Piece]:
        outer_rx, inner_rx, outer_ry, inner_ry = radii(350, 290)
        # The enclosed a carries an eased stroke so its counter survives.
        k = 1.0 if ratio <= 1.0 else (1.0 + 0.45 * (ratio - 1.0)) / ratio
        bowl_rx, _bowl_irx, _bowl_ry, _bowl_iry = radii(150, 70, k=k)
        bowl_right = X(350) + bowl_rx
        stem = (bowl_right - tk(76) * k, bowl_right)
        foot = (526 - bar_t(76) * k, 526.0)
        # The tail of the inner a runs into the spiral, whose lower terminal
        # is cut level with the top of that tail.
        rise = foot[0] - 390
        outer_start = asin(min(0.9, rise / outer_ry)) * 180 / pi
        inner_start = asin(min(0.9, rise / inner_ry)) * 180 / pi
        mid_rx, mid_ry = (outer_rx + inner_rx) / 2, (outer_ry + inner_ry) / 2
        lift = min(0.95, (mid(foot) - 390) / mid_ry)
        reach_x = X(360) + mid_rx * sqrt(1 - lift * lift)
        return [
            pc(
                sector(
                    X(360), 390, outer_rx, inner_rx, outer_ry, inner_ry,
                    outer_start, 330, 330, inner_start, caps=(1, 1), steps=78,
                )
            ),
            ring_p(350, 390, 150, 70, k=k),
            pc(box(stem, (254, 526))),
            pc(box((mid(stem), reach_x), foot)),
        ]

    G["@"] = glyph_at

    def bracket() -> list[Piece]:
        stem = left(52)
        return [
            pc(box(stem, (-40, 780))),
            pc(box((mid(stem), X(300)), top(-40, 80))),
            pc(box((mid(stem), X(300)), bottom(780, 80))),
        ]

    G["["] = bracket

    def glyph_backslash() -> list[Piece]:
        width = cap_width(104, 356, 700)
        return [pc(band(cap_l(52, width), 0, cap_r(408, width), 700))]

    G["\\"] = glyph_backslash
    G["]"] = lambda: mirror_x(G["["](), 300)
    G["^"] = lambda: [chev(230, 10, (60, 250), (400, 250), 92)]
    G["_"] = lambda: [pc(box((X(0), X(560)), top(730, 90)))]
    G["`"] = lambda: [bar(50, 25, 190, 170, 88)]

    def brace() -> list[Piece]:
        stem = centre(214, 88)
        hook_t = bar_t(85)
        spike = 88 * ratio
        return [
            pc(box((mid(stem), X(300) + (tk(88) - 88) / 2), (-40, -40 + hook_t))),
            pc(box(stem, (-40, 370 + JOIN))),
            chev_abs((stem[0] - 100 * W, 370), (mid(stem), 330), (mid(stem), 410), spike),
            pc(box(stem, (370 - JOIN, 780))),
            pc(box((mid(stem), X(300) + (tk(88) - 88) / 2), (780 - hook_t, 780))),
        ]

    G["{"] = brace
    G["|"] = lambda: [pc(box(left(52), (-40, 780)))]
    G["}"] = lambda: mirror_x(G["{"](), 300)
    G["~"] = lambda: [wave(220, 360, 220, 32, 45)]

    # ======================================================= Latin-1 symbols
    G["¡"] = lambda: rotate_180(G["!"](), 52, 350)
    G["¢"] = lambda: G["c"]() + [pc(box(centre(262, 76), (110, 790)))]

    def glyph_sterling() -> list[Piece]:
        stem = left(212)
        return [
            pc(RS(350, 190, 190, 86, 180, 330, 330, 180, caps=(1, 0), tails=(0.0, JOIN))),
            pc(box(stem, (190, 700 - bar_t() / 2))),
            pc(box((mid(stem) - 182 * W, mid(stem) + 208 * W), around(380))),
            pc(box((mid(stem) - 212 * W, mid(stem) + 358 * W), bottom(700))),
        ]

    G["£"] = glyph_sterling

    def glyph_currency() -> list[Piece]:
        outer_rx, inner_rx, outer_ry, inner_ry = radii(150, 70)
        cx, cy = X(230), 360.0
        width = 80 * ratio
        pieces = [ring_p(230, 360, 150, 70)]
        for sx, sy in ((1, -1), (-1, -1), (1, 1), (-1, 1)):
            root = (
                cx + sx * (outer_rx + inner_rx) / 2 * 0.7071,
                cy + sy * (outer_ry + inner_ry) / 2 * 0.7071,
            )
            tip = (
                cx + sx * (outer_rx + 111.6 * W) * 0.7071,
                cy + sy * (outer_ry + 111.6) * 0.7071,
            )
            pieces.append(pc(slab(root, tip, width)))
        return pieces

    G["¤"] = glyph_currency
    def glyph_yen() -> list[Piece]:
        offset = 70 + 0.3 * max(0.0, bar_t(70) - 70)
        return G["Y"]() + [
            pc(box((X(70), X(570)), around(455 - offset, 70))),
            pc(box((X(70), X(570)), around(455 + offset, 70))),
        ]

    G["¥"] = glyph_yen
    G["¦"] = lambda: [pc(box(left(52), (-40, 300))), pc(box(left(52), (420, 780)))]
    def glyph_section() -> list[Piece]:
        if S > 104.0 and not _nested:
            # Three bars and a ring cannot carry a heavy stroke; ease it.
            lighter = replace(
                p,
                s=104.0 + 0.12 * (S - 104.0),
                sh=100.0 + 0.12 * (SH - 100.0),
            )
            return glyph_defs(lighter, _nested=True)["§"]()
        return translate(
            scale(G["S"](), 0.85) + [ring_p(297, 297, 140, 72)], 20, 55
        )

    G["§"] = glyph_section
    G["¨"] = lambda: [accent_disc(10, 90, 55, 120), accent_disc(250, 90, 55, 120)]
    G["©"] = lambda: [
        ring_p(350, 350, 350, 290),
        pc(RS(350, 350, 190, 118, -38, -322, -330, -30, caps=(1, 1))),
    ]
    G["ª"] = lambda: translate(scale(G["a"](), 0.55), 0, -100)
    def glyph_guillemet() -> list[Piece]:
        # The second chevron steps away as the strokes thicken.
        step = 210 + 0.9 * max(0.0, tk(86) - 86) / W
        return [
            chev(50, 400, (190, 255), (190, 545), 86),
            chev(50 + step, 400, (190 + step, 255), (190 + step, 545), 86),
        ]

    G["«"] = glyph_guillemet

    def glyph_not() -> list[Piece]:
        bar_y = around(364, 88)
        return [
            pc(box((X(0), X(460)), bar_y)),
            pc(rect(X(460) - tk(88), bar_y[0], X(460), 570)),
        ]

    G["¬"] = glyph_not

    def glyph_registered() -> list[Piece]:
        # The enclosed R carries a damped stroke so its counters survive.
        local = ratio if ratio <= 1.0 else 1.0 + 0.2 * (ratio - 1.0)
        stem_w, bar_h, leg_w = 65 * local, 62 * local, 70 * local
        edge = X(287.5) - max(65.0, stem_w) / 2
        stem = (edge, edge + stem_w)
        bowl_x = X(390)
        outer_rx = 60 * W + max(62.0, bar_h) / 2
        leg_y = 402 - bar_h / 2
        return [
            ring_p(350, 350, 350, 290),
            pc(rect(stem[0], 220, stem[1], 480)),
            pc(rect(mid(stem), 220, bowl_x, 220 + bar_h)),
            pc(rect(mid(stem), 402 - bar_h, bowl_x, 402)),
            pc(
                sector(
                    bowl_x, 311, outer_rx, max(8.0, outer_rx - bar_h),
                    91, max(6.0, 91 - bar_h),
                    -90, 90, 90, -90, tails=(JOIN / 2, JOIN / 2),
                )
            ),
            pc(
                band(
                    cap_c(385 + 0.5 * (leg_y - 380), leg_w),
                    leg_y,
                    cap_c(435, leg_w),
                    480,
                )
            ),
        ]

    G["®"] = glyph_registered
    G["¯"] = lambda: [pc(box((X(0), X(360)), around(84, 88)))]
    G["°"] = lambda: [ring_p(115, 115, 115, 50)]
    G["±"] = lambda: [
        pc(box(centre(220, 88), (110, 510))),
        pc(box((X(0), X(440)), around(310, 88))),
        pc(box((X(0), X(440)), bottom(698, 88))),
    ]
    G["²"] = lambda: scale(G["2"](), 0.5)
    G["³"] = lambda: scale(G["3"](), 0.5)
    G["´"] = lambda: [bar(190, 25, 50, 170, 88)]
    G["µ"] = lambda: [
        pc(box(left(52), (200, 900))),
        pc(RS(262, 438, 262, 158, 180, 0, 0, 180, tails=(JOIN, JOIN))),
        pc(box(right(472), (200, 700))),
    ]

    def glyph_pilcrow() -> list[Piece]:
        # Two stems share a 210-unit skeleton; an eased stroke keeps the gap.
        width = tk() * (1 - 0.35 * heavy_progress)
        first = (X(382) - width / 2, X(382) + width / 2)
        edge = X(592) + max(104.0, width) / 2
        second = (edge - width, edge)
        bar_y = top(0, 90)
        return [
            pc(
                Contour(
                    arc_pts(first[0], 180, 180 * W, 180, 90, 270)
                    + [(first[0] + JOIN, 0.0, 0), (first[0] + JOIN, 360.0, 0)]
                )
            ),
            pc(box(first, (0, 700))),
            pc(box(second, (0, 700))),
            pc(box((first[0], second[1]), bar_y)),
        ]

    G["¶"] = glyph_pilcrow
    G["·"] = lambda: [point(63, 360, 63)]

    def cedilla(cx: float) -> list[Piece]:
        stem = centre(cx, 68)
        foot = bottom(836, 64)
        return [
            pc(box(stem, (690, 836))),
            pc(box((stem[1] - 138 * max(1.0, ratio**0.6), stem[1]), foot)),
        ]

    G["¸"] = lambda: cedilla(100)
    G["¹"] = lambda: scale(G["1"](), 0.5)
    G["º"] = lambda: translate(scale(G["o"](), 0.55), 0, -100)
    G["»"] = lambda: mirror_x(
        G["«"](), 450 + 0.9 * max(0.0, tk(86) - 86) / W
    )

    def fraction(top_name: str, bottom_name: str, dx: float) -> list[Piece]:
        """Numerator, slash and denominator with a guaranteed clearance.

        The canonical positions stand wherever they leave room. A heavy or
        condensed figure that would reach the slash pushes it, and the
        denominator behind it, to the right.
        """

        upper = scale(G[top_name](), 0.44)
        lower = translate(scale(G[bottom_name](), 0.44), dx, 392)
        width = cap_width(70, 350, 700)
        head, foot = cap_c(435, width), cap_c(85, width)
        clearance = 10.0 + 0.25 * width

        def slash_edge(y: float, side: float) -> float:
            return at_y(head, 0, foot, 700, y) + side * width / 2

        upper_bottom = max(q[1] for piece in upper for q in piece.outer.pts)
        push = max(
            0.0,
            extent(upper)[1] + clearance - slash_edge(upper_bottom, -1),
        )
        lower_top = min(q[1] for piece in lower for q in piece.outer.pts)
        pull = max(
            0.0,
            slash_edge(lower_top, 1) + push + clearance - extent(lower)[0],
        )
        slash = pc(
            band((head[0] + push, head[1] + push), 0, (foot[0] + push, foot[1] + push), 700)
        )
        return upper + [slash] + map_pieces(
            lower, lambda q: (q[0] + pull, q[1], q[2])
        )

    G["¼"] = lambda: fraction("1", "4", 330)
    G["½"] = lambda: fraction("1", "2", 330)
    G["¾"] = lambda: fraction("3", "4", 350)
    G["¿"] = lambda: rotate_180(G["?"](), 319, 350)
    G["×"] = lambda: [bar(139, 219, 421, 501, 96), bar(421, 219, 139, 501, 96)]

    def glyph_divide() -> list[Piece]:
        bar_y = around(360, 88)
        size = dot_radius(63, 0.8)
        offset = max(210.0, bar_t(88) / 2 + 0.45 * size + size)
        return [
            pc(box((X(0), X(440)), bar_y)),
            dot_at(X(220), 360 - offset, size),
            dot_at(X(220), 360 + offset, size),
        ]

    G["÷"] = glyph_divide

    # ======================================================= special letters
    def glyph_ae_cap() -> list[Piece]:
        stem = centre(392)
        width = cap_width(104, 340, 700)
        # The foot steps out with weight so the A counter stays open.
        foot = cap_l(52 - 0.9 * max(0.0, S - 104.0) / W, width)
        return [
            pc(band(stem, 0, foot, 700)),
            pc(box(stem, (0, 700))),
            pc(box((mid(stem), X(900)), top(0))),
            pc(box((mid(stem), X(760)), around(360))),
            pc(box((mid(stem), X(910)), bottom(700))),
            pc(box((at_y(stem, 0, foot, 700, 480), mid(stem)), around(480))),
        ]

    G["Æ"] = glyph_ae_cap
    G["æ"] = lambda: [ring_p(250, 450, 250, 146)] + e_parts(690, 250, 146)
    G["Ø"] = lambda: G["O"]() + [bar(40, 770, 690, -70, 76)]
    G["ø"] = lambda: G["o"]() + [bar(30, 760, 494, 140, 66)]

    def glyph_eth_cap() -> list[Piece]:
        stem = left(52)
        return G["D"]() + [
            pc(box((mid(stem) - 122 * W, mid(stem) + 198 * W), around(352, 96)))
        ]

    G["Ð"] = glyph_eth_cap
    G["ð"] = lambda: [
        ring_p(240, 490, 222, 118),
        bar(300, 300, 480, 40, 96),
        bar(310, 110, 480, 230, 66),
    ]

    def glyph_thorn_cap() -> list[Piece]:
        stem = left(52)
        return [
            pc(box(stem, (0, 700))),
            pc(box((mid(stem), X(400)), (202 - S / 2, 202 + S / 2))),
            pc(box((mid(stem), X(400)), (508 - S / 2, 508 + S / 2))),
            pc(half_bowl(400, 202, 508, 205, 101, "right")),
        ]

    G["Þ"] = glyph_thorn_cap
    G["þ"] = lambda: [pc(box(left(52), (0, 900))), bowl()]

    def glyph_germandbls() -> list[Piece]:
        stem, link = left(52), right(298)
        outer_rx, inner_rx, outer_ry, inner_ry = radii(202, 98)
        return [
            pc(box(stem, (0, 700))),
            pc(arch(stem[0], link[1], 175, 175, 71)),
            pc(box(link, (175, 498 - inner_ry))),
            pc(
                sector(
                    mid(link), 498, outer_rx, inner_rx, outer_ry, inner_ry,
                    -90, 90, 90, -90, caps=(1, 0), tails=(0.0, JOIN),
                )
            ),
        ]

    G["ß"] = glyph_germandbls

    direct_count = len(G)

    # ================================================================ accents
    def cap_accent(kind: str, cx: float) -> list[Piece]:
        if kind == "grave":
            return accent_bar(cx - 110, -255, cx + 45, -90, 94, -57.8)
        if kind == "acute":
            return accent_bar(cx + 110, -255, cx - 45, -90, 94, -57.8)
        if kind == "circ":
            return accent_chev(
                cx, -260, (cx - 155, -85), (cx + 155, -85), 90, -55.2
            )
        if kind == "dier":
            return [
                accent_disc(cx - 136, -115, 63, 136),
                accent_disc(cx + 136, -115, 63, 136),
            ]
        if kind == "ring":
            return [ring_p(cx, -150, 96, 42)]
        if kind == "tilde":
            return settle([wave(cx, -160, 190, 26, 44)], -90.0)
        if kind == "ced":
            return cedilla(cx)
        return []

    def lc_accent(kind: str, cx: float) -> list[Piece]:
        # Lowercase accents rest 26 units above the round overshoot line;
        # the canonical grave, acute and circumflex ran into their letters.
        if kind == "grave":
            return accent_bar(cx - 100, 25, cx + 40, 170, 88, 162.0)
        if kind == "acute":
            return accent_bar(cx + 100, 25, cx - 40, 170, 88, 162.0)
        if kind == "circ":
            # Preserve the canonical ±140 default while keeping the terminal
            # caps clear of the extrusion direction away from wdth=100.
            half_span = 140 / max(1.0, W)
            return accent_chev(
                cx, 20, (cx - half_span, 170), (cx + half_span, 170), 84, 162.0
            )
        if kind == "dier":
            return [
                accent_disc(cx - 120, 85, 55, 120),
                accent_disc(cx + 120, 85, 55, 120),
            ]
        if kind == "ring":
            return [ring_p(cx, 70, 88, 36)]
        if kind == "tilde":
            return settle([wave(cx, 95, 170, 24, 40)], 159.0)
        if kind == "ced":
            return cedilla(cx)
        return []

    def x_center(pieces: Sequence[Piece]) -> float:
        low, high = extent(pieces)
        return (low + high) / (2 * W)

    def composed(base: str, accent: str, lowercase: bool) -> Builder:
        def builder() -> list[Piece]:
            pieces = G[base]()
            accents = lc_accent if lowercase else cap_accent
            return pieces + accents(accent, x_center(pieces))

        return builder

    for char, (base, accent) in CAP_COMPOSITES.items():
        G[char] = composed(base, accent, False)
    for char, (base, accent) in LC_COMPOSITES.items():
        G[char] = composed(base, accent, True)

    if direct_count != 138:
        raise AssertionError(f"canonical direct-builder count changed: {direct_count}")
    return G


# Source-name aliases make line-by-line comparisons with the JS straightforward.
arcPts = arc_pts
ringSector = ring_sector


# ------------------------------------------------------------- design space
DESIGN_WEIGHTS = (100.0, 400.0, 700.0, 900.0)
DESIGN_WIDTHS = (75.0, 100.0, 125.0)
DEFAULT_LOCATION = (400.0, 100.0)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3 - 2 * value)


def heavy_width_factor(width: float) -> float:
    """Limit added Black ink where the condensed skeleton has less room."""

    if width <= 100:
        return _lerp(0.9, 1.0, (width - 75) / 25)
    return _lerp(1.0, 1.04, (width - 100) / 25)


def weight_strokes(weight: float, width: float = 100) -> tuple[float, float]:
    """Return coordinated vertical/horizontal strokes for the family.

    Thin through Regular retains the canonical donor values. Above Regular,
    growth eases toward a deliberate Black ceiling instead of scaling every
    piece to 200 units. The added ink is width-aware, so condensed counters and
    joins retain the same visual margin as the normal and expanded cuts.
    """

    if weight <= 400:
        t = (weight - 100) / 300
        return _lerp(40, 104, t), _lerp(36, 100, t)
    progress = _smoothstep((weight - 400) / 500)
    width_factor = heavy_width_factor(width)
    return (
        104 + (176 - 104) * progress * width_factor,
        100 + (170 - 100) * progress * width_factor,
    )


def design_params(
    wght: float = 400.0,
    wdth: float = 100.0,
    *,
    hand: bool = False,
) -> GeneratorParams:
    """Map a Weight/Width location onto generator parameters."""

    s, sh = weight_strokes(wght, wdth)
    heavy_progress = _smoothstep((wght - 400) / 500)
    # Heavy cuts need more skeleton room as well as more stroke. Expanding
    # the skeleton most at Condensed prevents counters and joins from being
    # consumed while preserving the requested width ordering.
    skeleton_growth = _lerp(0.08, 0.04, (wdth - 75) / 50)
    return GeneratorParams(
        s=s,
        sh=sh,
        w=(wdth / 100) * (1 + skeleton_growth * heavy_progress),
        v=(60, 70),
        hatch_n=HATCH_N,
        hatch_t=9,
        hatch_sp=17,
        jit=3.4 if hand else 0,
    )


def design_masters() -> tuple[GeneratorParams, ...]:
    """Return the twelve source cuts, default first."""

    locations = [DEFAULT_LOCATION] + [
        (weight, width)
        for weight in DESIGN_WEIGHTS
        for width in DESIGN_WIDTHS
        if (weight, width) != DEFAULT_LOCATION
    ]
    return tuple(design_params(weight, width) for weight, width in locations)


# ------------------------------------------------------------------ sampling
@dataclass(frozen=True, slots=True)
class SamplePoint:
    """A sampled outline point.

    ``arc``, ``force`` and ``hidden`` describe the edge that starts here:
    whether it belongs to a curve, is a forced terminal cap, or lies inside
    another piece of the same glyph.
    """

    x: float
    y: float
    arc: bool = False
    force: bool = False
    hidden: bool = False

    @property
    def flag(self) -> int:
        return 2 if self.force else (1 if self.arc else 0)

    def translated(self, dx: float, dy: float) -> "SamplePoint":
        return SamplePoint(self.x + dx, self.y + dy, self.arc, self.force, self.hidden)


@dataclass(frozen=True, slots=True)
class SpanTopology:
    """Frozen sampling recipe for one smooth run of raw edges.

    A span is a single straight raw edge or a maximal run of curve chords.
    ``cuts`` are the positions, in raw-edge units from the span start, where
    the span enters or leaves another piece at the structure master. Each
    interval between cuts owns a fixed sample count, so the same sample
    index marks the same junction at every axis location.
    """

    start: int
    edges: int
    arc: bool
    force: bool
    closed: bool
    hidden_first: bool
    cuts: tuple[float, ...]
    counts: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ContourTopology:
    """Frozen spans plus the default-master winding normalization."""

    spans: tuple[SpanTopology, ...]
    reverse: bool

    @property
    def point_count(self) -> int:
        return sum(sum(span.counts) for span in self.spans)


@dataclass(frozen=True, slots=True)
class GlyphTopology:
    """Per-piece topology frozen once across the design masters."""

    pieces: tuple[tuple[ContourTopology, ...], ...]


@dataclass(frozen=True, slots=True)
class BuiltContour:
    """One normalized contour at a master, with ideal and jittered points."""

    points: tuple[SamplePoint, ...]
    ideal: tuple[SamplePoint, ...]
    is_hole: bool


@dataclass(frozen=True, slots=True)
class BuiltPiece:
    """One normalized filled piece at a master."""

    contours: tuple[BuiltContour, ...]

    @property
    def outer(self) -> BuiltContour:
        return self.contours[0]

    @property
    def holes(self) -> tuple[BuiltContour, ...]:
        return self.contours[1:]


@dataclass(frozen=True, slots=True)
class GlyphOutline:
    """A glyph's frozen-topology source outline in y-down coordinates."""

    name: str
    pieces: tuple[BuiltPiece, ...]
    params: GeneratorParams
    seed: float
    topology: GlyphTopology
    #: Spans whose junction structure differs from the structure master.
    unmatched: int = 0

    @property
    def contours(self) -> tuple[BuiltContour, ...]:
        return tuple(contour for piece in self.pieces for contour in piece.contours)


def _xy(point: SamplePoint | Sequence[float]) -> tuple[float, float]:
    if isinstance(point, SamplePoint):
        return point.x, point.y
    return float(point[0]), float(point[1])


def subdivide(
    contour: Contour,
    max_len: float = SUBDIVISION_MAX_LENGTH,
) -> list[SamplePoint]:
    """Port ``subdivide``: uniform samples on every raw edge."""

    points = contour.pts
    out: list[SamplePoint] = []
    for index, a in enumerate(points):
        b = points[(index + 1) % len(points)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = _js_hypot(dx, dy)
        count = max(1, ceil(length / max_len))
        arc = a[2] == 1 and b[2] == 1 and length < 40
        for k in range(count):
            out.append(
                SamplePoint(
                    a[0] + dx * k / count,
                    a[1] + dy * k / count,
                    arc,
                    a[2] == 2,
                )
            )
    return out


def signed_area(points: Sequence[SamplePoint | Sequence[float]]) -> float:
    """Return the source-coordinate signed area (positive is clockwise visually)."""

    total = 0.0
    for index, point in enumerate(points):
        other = points[(index + 1) % len(points)]
        ax, ay = _xy(point)
        bx, by = _xy(other)
        total += ax * by - bx * ay
    return total / 2


def point_in(x: float, y: float, points: Sequence[SamplePoint | Sequence[float]]) -> bool:
    """Port the grid engine's even/odd ``ptIn`` test."""

    inside = False
    previous = len(points) - 1
    for index, point in enumerate(points):
        ax, ay = _xy(point)
        bx, by = _xy(points[previous])
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
        previous = index
    return inside


def jitter_points(points: Sequence[SamplePoint], amp: float, seed: float) -> list[SamplePoint]:
    """Port ``jitterPts`` while retaining the load-bearing edge flags."""

    if not amp:
        return [SamplePoint(p.x, p.y, p.arc, p.force, p.hidden) for p in points]
    s1, s2 = seed * 1.7 + 0.4, seed * 2.3 + 1.9
    s3, s4 = seed * 3.1 + 0.7, seed * 1.3 + 2.6
    return [
        SamplePoint(
            p.x + amp * 0.5 * (sin(p.x * 0.011 + s1) + sin(p.y * 0.017 + s2)),
            p.y + amp * 0.5 * (sin(p.x * 0.015 + s3) + sin(p.y * 0.009 + s4)),
            p.arc,
            p.force,
            p.hidden,
        )
        for p in points
    ]


def glyph_seed(name: str) -> float:
    """Return the JS ``charCodeAt`` seed, including UTF-16 surrogate semantics."""

    encoded = name.encode("utf-16-le", "surrogatepass")
    return sum(int.from_bytes(encoded[i : i + 2], "little") * 7.13 for i in range(0, len(encoded), 2))


def _raw_piece_contours(piece: Piece) -> tuple[Contour, ...]:
    return (piece.outer, *piece.holes)


# A boundary point counts as buried when the point this far outside it lies in
# another piece. The offset also treats abutting pieces as joined.
HIDE_OFFSET = 1.5
# Buried stretches shorter than this, and gaps this short between them, are
# not worth a sample point.
MIN_CUT_LENGTH = 1.0
# A junction this close to a span end is the span end: the outward offset
# rounds a corner slightly early or late.
END_SNAP = 4.0
# Diagnostic switch: also report junctions that exist at a location but not at
# the structure master. Costs one extra containment pass per span.
AUDIT_NEW_JUNCTIONS = False

XY: TypeAlias = tuple[float, float]
Cut: TypeAlias = tuple[float, int]


@dataclass(frozen=True, slots=True)
class _Shape:
    """One raw piece prepared for containment queries."""

    outer: tuple[XY, ...]
    holes: tuple[tuple[XY, ...], ...]
    box: tuple[float, float, float, float]

    def contains(self, x: float, y: float) -> bool:
        if not (self.box[0] <= x <= self.box[2] and self.box[1] <= y <= self.box[3]):
            return False
        return point_in(x, y, self.outer) and not any(
            point_in(x, y, hole) for hole in self.holes
        )


def _shape(piece: Piece) -> _Shape:
    outer = tuple((q[0], q[1]) for q in piece.outer.pts)
    holes = tuple(tuple((q[0], q[1]) for q in hole.pts) for hole in piece.holes)
    xs = [q[0] for q in outer]
    ys = [q[1] for q in outer]
    return _Shape(outer, holes, (min(xs), min(ys), max(xs), max(ys)))


def _crossings(p: XY, q: XY, polygon: Sequence[XY]) -> list[float]:
    """Parameters in (0, 1) where segment ``p``→``q`` meets a closed polygon."""

    px, py = p
    dx, dy = q[0] - px, q[1] - py
    lo_x, hi_x = min(px, q[0]), max(px, q[0])
    lo_y, hi_y = min(py, q[1]), max(py, q[1])
    out: list[float] = []
    ax, ay = polygon[-1]
    for bx, by in polygon:
        if not (
            (ax < lo_x and bx < lo_x)
            or (ax > hi_x and bx > hi_x)
            or (ay < lo_y and by < lo_y)
            or (ay > hi_y and by > hi_y)
        ):
            ex, ey = bx - ax, by - ay
            den = dx * ey - dy * ex
            if abs(den) > 1e-12:
                t = ((ax - px) * ey - (ay - py) * ex) / den
                s = ((ax - px) * dy - (ay - py) * dx) / den
                if -1e-9 <= s <= 1 + 1e-9 and 0.0 < t < 1.0:
                    out.append(t)
        ax, ay = bx, by
    return out


def _buried_intervals(a: XY, b: XY, others: Sequence[_Shape]) -> list[tuple[float, float]]:
    """Parameter intervals of segment ``a``→``b`` that lie inside ``others``."""

    lo_x, hi_x = min(a[0], b[0]), max(a[0], b[0])
    lo_y, hi_y = min(a[1], b[1]), max(a[1], b[1])
    found: list[tuple[float, float]] = []
    for shape in others:
        box = shape.box
        if hi_x < box[0] or lo_x > box[2] or hi_y < box[1] or lo_y > box[3]:
            continue
        breaks = [0.0, 1.0]
        breaks.extend(_crossings(a, b, shape.outer))
        for hole in shape.holes:
            breaks.extend(_crossings(a, b, hole))
        breaks.sort()
        for first, second in zip(breaks, breaks[1:]):
            if second - first < 1e-9:
                continue
            middle = (first + second) / 2
            if shape.contains(
                a[0] + (b[0] - a[0]) * middle,
                a[1] + (b[1] - a[1]) * middle,
            ):
                found.append((first, second))
    if not found:
        return found
    found.sort()
    merged = [found[0]]
    for first, second in found[1:]:
        if first <= merged[-1][1] + 1e-9:
            merged[-1] = (merged[-1][0], max(merged[-1][1], second))
        else:
            merged.append((first, second))
    return merged


def _normalized(contour: Contour, reverse: bool) -> tuple[list[XY], list[tuple[bool, bool, float]]]:
    """Return points and per-edge ``(arc, force, length)`` in normalized order."""

    raw = contour.pts
    count = len(raw)
    edges: list[tuple[bool, bool, float]] = []
    for index, a in enumerate(raw):
        b = raw[(index + 1) % count]
        length = _js_hypot(b[0] - a[0], b[1] - a[1])
        edges.append((a[2] == 1 and b[2] == 1 and length < 40, a[2] == 2, length))
    points = [(q[0], q[1]) for q in raw]
    if reverse:
        points.reverse()
        # Normalized edge k runs raw edge (count - 2 - k) backwards.
        edges = [edges[(count - 2 - k) % count] for k in range(count)]
    return points, edges


def _span_layout(edges: Sequence[tuple[bool, bool, float]]) -> list[tuple[int, int, bool, bool, bool]]:
    """Group raw edges into ``(start, edges, arc, force, closed)`` spans."""

    count = len(edges)
    if all(edge[0] for edge in edges):
        return [(0, count, True, False, True)]
    # Begin at an edge that does not continue a curve run, so no run wraps.
    first = next(
        index
        for index in range(count)
        if not (edges[index][0] and edges[index - 1][0])
    )
    spans: list[tuple[int, int, bool, bool, bool]] = []
    offset = 0
    while offset < count:
        index = (first + offset) % count
        arc, force, _length = edges[index]
        run = 1
        if arc:
            while offset + run < count and edges[(first + offset + run) % count][0]:
                run += 1
        spans.append((index, run, arc, force, False))
        offset += run
    return spans


def _span_cuts(
    points: Sequence[XY],
    start: int,
    edge_count: int,
    closed: bool,
    others: Sequence[_Shape],
) -> tuple[bool, list[Cut]]:
    """Return the start state and the junction cuts of one span.

    A cut is ``(position, polarity)`` with the position in raw-edge units from
    the span start and polarity ``+1`` where the span becomes buried.
    """

    count = len(points)
    intervals: list[tuple[float, float]] = []
    lengths: list[float] = []
    for local in range(edge_count):
        a = points[(start + local) % count]
        b = points[(start + local + 1) % count]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = _js_hypot(dx, dy)
        lengths.append(length)
        if length < 1e-9 or not others:
            continue
        nx, ny = dy / length * HIDE_OFFSET, -dx / length * HIDE_OFFSET
        for first, second in _buried_intervals(
            (a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), others
        ):
            intervals.append((local + first, local + second))

    def distance(first: float, second: float) -> float:
        """Polyline length between two span positions."""

        total = 0.0
        index = int(first)
        position = first
        while position < second - 1e-12:
            step_end = min(float(index + 1), second)
            total += (step_end - position) * lengths[min(index, edge_count - 1)]
            position = step_end
            index += 1
        return total

    merged: list[tuple[float, float]] = []
    for first, second in sorted(intervals):
        if merged and distance(merged[-1][1], first) < MIN_CUT_LENGTH:
            merged[-1] = (merged[-1][0], max(merged[-1][1], second))
        else:
            merged.append((first, second))
    merged = [
        (first, second)
        for first, second in merged
        if distance(first, second) >= MIN_CUT_LENGTH
    ]
    total = float(edge_count)
    if closed and merged:
        if merged[0][0] <= 1e-9 and merged[-1][1] >= total - 1e-9:
            if len(merged) == 1:
                return True, []
            # One buried run wraps the closing point.
            wrap = (merged[-1][0], merged[0][1] + total)
            merged = merged[1:-1] + [wrap]
    hidden_first = False
    cuts: list[Cut] = []
    for first, second in merged:
        if closed:
            cuts.append((first % total, 1))
            cuts.append((second % total, -1))
            continue
        starts_here = distance(0.0, first) < END_SNAP
        ends_here = distance(second, total) < END_SNAP
        if starts_here:
            hidden_first = True
        else:
            cuts.append((first, 1))
        if not ends_here:
            cuts.append((second, -1))
    cuts.sort()
    if closed and cuts:
        # The state at the closing point follows from the first cut.
        hidden_first = cuts[0][1] == -1
    return hidden_first, cuts


CUT_SEPARATION = 1e-4


def _align_cuts(
    reference: Sequence[Cut],
    found: Sequence[Cut],
    penalty: float,
) -> tuple[float, list[int | None]]:
    """Order-preserving alignment of reference cuts with found cuts.

    Returns the cost and, per reference cut, the index of its found
    counterpart or ``None``. A reference cut may stay unmatched at
    ``penalty``; surplus found cuts are free to skip.
    """

    rows, cols = len(reference), len(found)
    cost = [[0.0] * (cols + 1) for _ in range(rows + 1)]
    move = [[2] * (cols + 1) for _ in range(rows + 1)]
    for i in range(1, rows + 1):
        cost[i][0] = cost[i - 1][0] + penalty
        move[i][0] = 1
    for i in range(1, rows + 1):
        ref_position, ref_polarity = reference[i - 1]
        for j in range(1, cols + 1):
            position, polarity = found[j - 1]
            best, how = cost[i][j - 1], 2
            skip = cost[i - 1][j] + penalty
            if skip < best:
                best, how = skip, 1
            if polarity == ref_polarity:
                pair = cost[i - 1][j - 1] + abs(position - ref_position)
                if pair <= best:
                    best, how = pair, 0
            cost[i][j], move[i][j] = best, how
    pairs: list[int | None] = [None] * rows
    i, j = rows, cols
    while i > 0:
        how = move[i][j]
        if how == 0:
            pairs[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif how == 1:
            i -= 1
        else:
            j -= 1
    return cost[rows][cols], pairs


def _end_cuts(
    found: Sequence[Cut],
    found_first: bool,
    reference_first: bool,
    reference_count: int,
    total: float,
) -> list[Cut]:
    """Express a span's state against the reference's start and end states.

    Where the span starts or ends in the other state, a junction has slid
    off that end; a cut pinned to the end stands in for it.
    """

    cuts = list(found)
    if found_first != reference_first:
        cuts.insert(0, (0.0, 1 if found_first else -1))
    found_last = found_first ^ (len(found) % 2 == 1)
    reference_last = reference_first ^ (reference_count % 2 == 1)
    if found_last != reference_last:
        cuts.append((total, 1 if reference_last else -1))
    return cuts


def _rotations(found: Sequence[Cut], total: float) -> list[list[Cut]]:
    """Every unrolled rotation of a closed span's cuts, either side of 0."""

    out: list[list[Cut]] = []
    size = len(found)
    for shift in range(size):
        unrolled: list[Cut] = []
        offset = 0.0
        previous = found[shift][0]
        for index in range(size):
            position, polarity = found[(index + shift) % size]
            if position + offset < previous:
                offset += total
            previous = position + offset
            unrolled.append((previous, polarity))
        out.append(unrolled)
        out.append([(position - total, polarity) for position, polarity in unrolled])
    return out


def _best_alignment(
    reference: Sequence[Cut],
    found: Sequence[Cut],
    closed: bool,
    total: float,
    penalty: float,
) -> tuple[list[Cut], list[int | None]]:
    candidates = _rotations(found, total) if closed and found else [list(found)]
    best: tuple[float, list[Cut], list[int | None]] | None = None
    for candidate in candidates:
        cost, pairs = _align_cuts(reference, candidate, penalty)
        if best is None or cost < best[0]:
            best = (cost, candidate, pairs)
    assert best is not None
    return best[1], best[2]


def _merge_cuts(
    reference: Sequence[Cut],
    found: Sequence[Cut],
    closed: bool,
    total: float,
) -> list[Cut]:
    """Add to ``reference`` the junctions that only exist at another source.

    Surplus cuts are taken in alternating pairs between matched neighbours,
    so the merged list still alternates. At a source without that junction
    the pair collapses onto one point.
    """

    if not found:
        return list(reference)
    if not reference:
        return list(found) if len(found) % 2 == 0 else []
    candidate, pairs = _best_alignment(reference, found, closed, total, 0.25 * total)
    matched = [(i, j) for i, j in enumerate(pairs) if j is not None]
    if not matched:
        return list(reference)
    merged: list[Cut] = []

    def surplus(j0: int, j1: int, low: float, high: float) -> list[Cut]:
        """Found cuts j0..j1-1 mapped into the reference interval."""

        if (j1 - j0) % 2 or j1 <= j0:
            return []
        first, last = candidate[j0][0], candidate[j1 - 1][0]
        span_low = candidate[j0 - 1][0] if j0 > 0 else min(first, low)
        span_high = candidate[j1][0] if j1 < len(candidate) else max(last, high)
        scale = (high - low) / (span_high - span_low) if span_high > span_low else 0.0
        return [
            (low + (position - span_low) * scale, polarity)
            for position, polarity in candidate[j0:j1]
        ]

    first_i, first_j = matched[0]
    last_i, last_j = matched[-1]
    if not closed and first_i == 0:
        merged.extend(surplus(0, first_j, 0.0, reference[0][0]))
    merged.extend(reference[: first_i + 1])
    for (i0, j0), (i1, j1) in zip(matched, matched[1:]):
        if i1 == i0 + 1:
            merged.extend(surplus(j0 + 1, j1, reference[i0][0], reference[i1][0]))
        merged.extend(reference[i0 + 1 : i1 + 1])
    merged.extend(reference[last_i + 1 :])
    if not closed:
        if last_i == len(reference) - 1:
            merged.extend(
                surplus(last_j + 1, len(candidate), reference[-1][0], total)
            )
        return merged
    if first_i == 0 and last_i == len(reference) - 1:
        # On a loop the cuts after the last match and before the first one
        # share the stretch that wraps the origin.
        wrapped = list(candidate[last_j + 1 :]) + [
            (position + total, polarity) for position, polarity in candidate[:first_j]
        ]
        if wrapped and len(wrapped) % 2 == 0:
            low, high = reference[-1][0], reference[0][0] + total
            span_low, span_high = candidate[last_j][0], candidate[first_j][0] + total
            scale = (high - low) / (span_high - span_low) if span_high > span_low else 0.0
            merged.extend(
                (low + (position - span_low) * scale, polarity)
                for position, polarity in wrapped
            )
    return merged


def _match_cuts(
    reference: Sequence[Cut],
    found: Sequence[Cut],
    hidden_first: bool,
    found_hidden_first: bool,
    closed: bool,
    total: float,
    arc: bool = False,
) -> tuple[list[float], bool]:
    """Place the reference cuts at this source's junctions.

    Returns one position per reference cut and whether every junction was
    found. On a straight edge, a junction that does not exist here collapses
    with its partner onto one point: points may slide along a line without
    changing it. On a curve they may not, because a point interpolated
    between two positions on an arc falls inside the arc. There a missing
    junction keeps its reference position, and the wall it bounds is
    flattened instead.
    """

    if not reference:
        return [], not found and hidden_first == found_hidden_first
    if not closed:
        found = _end_cuts(found, found_hidden_first, hidden_first, len(reference), total)
    candidate, pairs = _best_alignment(
        reference, found, closed, total, 8.0 if arc else 0.25 * total
    )
    exact = all(pair is not None for pair in pairs) and len(candidate) == len(reference)

    positions: list[float | None] = [
        None if pair is None else candidate[pair][0] for pair in pairs
    ]
    # A cut never sits exactly on a span end: that would repeat the point it
    # shares with the neighbouring span.
    low = (reference[0][0] - total) if closed else CUT_SEPARATION
    high = (reference[0][0] + 2 * total) if closed else total - CUT_SEPARATION
    index = 0
    while index < len(positions):
        if positions[index] is not None:
            index += 1
            continue
        end = index
        while end < len(positions) and positions[end] is None:
            end += 1
        before = positions[index - 1] if index > 0 else None
        after = positions[end] if end < len(positions) else None
        floor = before if before is not None else low
        ceiling = after if after is not None else high
        # A skipped found cut inside the gap marks where the state really
        # changes; otherwise stay near the reference position.
        if arc:
            for slot in range(index, end):
                positions[slot] = min(ceiling, max(floor, reference[slot][0]))
            index = end
            continue
        j0 = pairs[index - 1] if index > 0 else None
        j1 = pairs[end] if end < len(positions) else None
        between = candidate[(j0 + 1 if j0 is not None else 0) : (j1 if j1 is not None else len(candidate))]
        if between:
            anchor = between[len(between) // 2][0]
        else:
            anchor = reference[index][0]
        anchor = min(ceiling, max(floor, anchor))
        for slot in range(index, end):
            positions[slot] = anchor
        index = end

    placed: list[float] = []
    for position in positions:
        assert position is not None
        position = max(position, low)
        if placed:
            position = max(position, placed[-1] + CUT_SEPARATION)
        placed.append(position)
    limit = (placed[0] + total) if closed else total
    for index in range(len(placed) - 1, -1, -1):
        ceiling = limit - (len(placed) - index) * CUT_SEPARATION
        if placed[index] > ceiling:
            placed[index] = ceiling
    return placed, exact


def _span_point(points: Sequence[XY], start: int, position: float) -> XY:
    count = len(points)
    index = int(position)
    fraction = position - index
    a = points[(start + index) % count]
    if fraction < 1e-12:
        return a
    b = points[(start + index + 1) % count]
    return a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction


def _span_intervals(span: SpanTopology, cuts: Sequence[float]) -> list[tuple[float, float]]:
    """Return the sampled intervals of a span that has junction cuts."""

    if span.closed:
        bounds = list(cuts) + [cuts[0] + span.edges]
    else:
        bounds = [0.0, *cuts, float(span.edges)]
    return list(zip(bounds, bounds[1:]))


def _curve_point(points: Sequence[XY], span: SpanTopology, position: float) -> XY:
    """Point on a curve span, interpolated through its neighbouring chords.

    A sample between two raw points of an ellipse belongs on the ellipse, not
    on the chord. A Catmull-Rom segment through the four surrounding raw
    points stays within a hundredth of a unit of it.
    """

    count = len(points)
    index = int(position)
    fraction = position - index
    if fraction < 1e-12:
        return points[(span.start + index) % count]

    def raw(local: int) -> XY:
        if span.closed:
            return points[(span.start + local) % count]
        if local < 0:
            a, b = points[span.start % count], points[(span.start + 1) % count]
            return 2 * a[0] - b[0], 2 * a[1] - b[1]
        if local > span.edges:
            a = points[(span.start + span.edges) % count]
            b = points[(span.start + span.edges - 1) % count]
            return 2 * a[0] - b[0], 2 * a[1] - b[1]
        return points[(span.start + local) % count]

    p0, p1, p2, p3 = raw(index - 1), raw(index), raw(index + 1), raw(index + 2)
    t, t2, t3 = fraction, fraction * fraction, fraction**3
    return tuple(
        0.5
        * (
            2 * p1[axis]
            + (p2[axis] - p0[axis]) * t
            + (2 * p0[axis] - 5 * p1[axis] + 4 * p2[axis] - p3[axis]) * t2
            + (3 * p1[axis] - p0[axis] - 3 * p2[axis] + p3[axis]) * t3
        )
        for axis in (0, 1)
    )  # type: ignore[return-value]


def _buried_ranges(
    state: bool,
    found: Sequence[Cut],
    closed: bool,
    total: float,
) -> list[tuple[float, float]]:
    """Stretches of a span, in raw-edge units, that are buried at a source."""

    bounds = [0.0] + sorted(position % total if closed else position for position, _p in found) + [total]
    ranges: list[tuple[float, float]] = []
    hidden = state
    for first, second in zip(bounds, bounds[1:]):
        if hidden and second > first:
            ranges.append((first, second))
        hidden = not hidden
    return ranges


def _sample_span(
    points: Sequence[XY],
    span: SpanTopology,
    cuts: Sequence[float],
    buried: Sequence[tuple[float, float]] | None = None,
) -> list[SamplePoint]:
    """Sample one span.

    ``hidden`` on each sample says whether the edge that starts there is
    buried in another piece at this source. Without ``buried`` the frozen
    structure answers; with it, the source's own junctions do.
    """

    def at(position: float) -> XY:
        if span.arc and span.edges > 1:
            return _curve_point(points, span, position)
        return _span_point(points, span.start, position)

    out: list[SamplePoint] = []
    if not span.cuts:
        for local, count in enumerate(span.counts):
            for k in range(count):
                first = local + k / count
                x, y = at(first)
                state = span.hidden_first
                if buried is not None:
                    # A chord counts as buried only when all of it is: a wall
                    # that overruns a junction hides behind the face, a wall
                    # that stops short of it leaves a gap.
                    second = local + (k + 1) / count
                    state = any(
                        low - 1e-6 <= first and second <= high + 1e-6
                        for low, high in buried
                    )
                out.append(SamplePoint(x, y, span.arc, span.force, state))
        return out
    total = float(span.edges)
    hidden = span.hidden_first
    for (first, second), count in zip(_span_intervals(span, cuts), span.counts):
        for k in range(count):
            x, y = at(first + (second - first) * k / count)
            state = hidden
            if buried is not None:
                middle = first + (second - first) * (k + 0.5) / count
                if span.closed:
                    middle %= total
                state = any(low <= middle < high for low, high in buried)
            out.append(SamplePoint(x, y, span.arc, span.force, state))
        hidden = not hidden
    return out


def _glyph_shapes(pieces: Sequence[Piece]) -> list[_Shape]:
    return [_shape(piece) for piece in pieces]


def _params_key(params: GeneratorParams) -> tuple[float, float, float]:
    return params.s, params.sh, params.w


# Ideal (unjittered) samples per ``(glyph, cut, topology)``; jitter is applied
# on top, so Regular and Handdrawn share one sampling pass.
_IDEAL_CACHE: dict[tuple, tuple] = {}


def freeze_topology(
    params: ParamsLike | None = None,
    names: Iterable[str] | None = None,
    max_len: float = SUBDIVISION_MAX_LENGTH,
    masters: Sequence[ParamsLike] | None = None,
) -> dict[str, GlyphTopology]:
    """Freeze winding, spans, junction cuts and sample counts.

    ``params`` is the structure master: it decides how many junctions each
    span has. ``masters`` (the twelve design sources by default) only raise
    sample counts, so an interval that is short at the structure master but
    long elsewhere is still sampled finely enough.
    """

    structure = coerce_params(params)
    others = [coerce_params(master) for master in (masters if masters is not None else design_masters())]
    cuts_only = [structure] + [
        master for master in others if _params_key(master) != _params_key(structure)
    ]
    builder_sets = [glyph_defs(master) for master in cuts_only]
    selected = tuple(builder_sets[0]) if names is None else tuple(names)
    result: dict[str, GlyphTopology] = {}
    for name in selected:
        if name not in builder_sets[0]:
            raise KeyError(name)
        raw_sets = [builders[name]() for builders in builder_sets]
        shape_sets = [_glyph_shapes(raw) for raw in raw_sets]
        piece_topologies: list[tuple[ContourTopology, ...]] = []
        for piece_index, piece in enumerate(raw_sets[0]):
            contours: list[ContourTopology] = []
            for contour_index, contour in enumerate(_raw_piece_contours(piece)):
                sampled = subdivide(contour, max_len)
                reverse = (signed_area(sampled) > 0) != (contour_index == 0)
                points, edges = _normalized(contour, reverse)
                spans: list[SpanTopology] = []
                for start, edge_count, arc, force, closed in _span_layout(edges):
                    total = float(edge_count)
                    states: list[tuple[list[XY], bool, list[Cut]]] = []
                    for master_index, raw in enumerate(raw_sets):
                        master_contour = _raw_piece_contours(raw[piece_index])[contour_index]
                        master_points, _master_edges = _normalized(master_contour, reverse)
                        other_shapes = [
                            shape
                            for index, shape in enumerate(shape_sets[master_index])
                            if index != piece_index
                        ]
                        state, found = _span_cuts(
                            master_points, start, edge_count, closed, other_shapes
                        )
                        states.append((master_points, state, found))

                    # The structure master fixes the start state; every other
                    # source may add junctions that only exist there.
                    hidden_first = states[0][1]
                    reference: list[Cut] = [] if arc else list(states[0][2])
                    for _points, state, found in states[1:]:
                        if arc:
                            # A point that slides along a curve bends it at
                            # every location between two sources. Curves keep
                            # their chord samples; their walls follow a
                            # junction chord by chord instead.
                            break
                        if not closed:
                            found = _end_cuts(found, state, hidden_first, len(reference), total)
                        reference = _merge_cuts(reference, found, closed, total)
                    if closed and reference:
                        if not states[0][2]:
                            # Collapsed at the structure master, the loop must
                            # read as its single state there.
                            wanted = -1 if states[0][1] else 1
                            if reference[0][1] != wanted:
                                reference = reference[1:] + [
                                    (reference[0][0] + total, reference[0][1])
                                ]
                        hidden_first = reference[0][1] == 1

                    def samples(length: float, master_index: int) -> int:
                        # Curves are already resolved by their chords.
                        limit = (
                            max_len
                            if master_index == 0 and not arc
                            else RELAXED_MAX_LENGTH
                        )
                        return max(1, ceil(length / limit - 1e-9))

                    if not reference:
                        counts = []
                        for local in range(edge_count):
                            needed = 1
                            for master_index, (master_points, _state, _found) in enumerate(states):
                                a = _span_point(master_points, start, float(local))
                                b = _span_point(master_points, start, float(local + 1))
                                needed = max(
                                    needed,
                                    samples(_js_hypot(b[0] - a[0], b[1] - a[1]), master_index),
                                )
                            counts.append(needed)
                        spans.append(
                            SpanTopology(
                                start, edge_count, arc, force, closed,
                                hidden_first, (), tuple(counts),
                            )
                        )
                        continue

                    probe = SpanTopology(
                        start, edge_count, arc, force, closed, hidden_first,
                        tuple(position for position, _p in reference), (),
                    )
                    counts = [1] * len(_span_intervals(probe, probe.cuts))
                    for master_index, (master_points, state, found) in enumerate(states):
                        positions, _exact = _match_cuts(
                            reference, found, hidden_first, state, closed, total, arc
                        )
                        for index, (first, second) in enumerate(
                            _span_intervals(probe, positions)
                        ):
                            if second - first <= 2 * CUT_SEPARATION:
                                continue
                            if arc:
                                # Never sample a curve more coarsely than its chords.
                                longest = 0.0
                                local = int(first)
                                while local < second:
                                    a = _span_point(master_points, start, float(local))
                                    b = _span_point(master_points, start, float(local + 1))
                                    longest = max(longest, _js_hypot(b[0] - a[0], b[1] - a[1]))
                                    local += 1
                                needed = max(1, ceil(second - first - 1e-9)) * samples(
                                    longest, master_index
                                )
                            else:
                                a = _span_point(master_points, start, first)
                                b = _span_point(master_points, start, second)
                                needed = samples(
                                    _js_hypot(b[0] - a[0], b[1] - a[1]), master_index
                                )
                            counts[index] = max(counts[index], needed)
                    spans.append(
                        SpanTopology(
                            start, edge_count, arc, force, closed, hidden_first,
                            probe.cuts, tuple(counts),
                        )
                    )
                contours.append(ContourTopology(tuple(spans), reverse))
            piece_topologies.append(tuple(contours))
        result[name] = GlyphTopology(tuple(piece_topologies))
    return result


def _resolve_topology(
    name: str,
    topology: GlyphTopology | Mapping[str, GlyphTopology] | None,
) -> GlyphTopology:
    if isinstance(topology, GlyphTopology):
        return topology
    if topology is not None:
        return topology[name]
    # Structure is always frozen at D, even when the requested outline is
    # another master.  This is the core interpolation invariant.
    return freeze_topology(GeneratorParams(), (name,))[name]


def build_contours(
    name: str,
    params: ParamsLike | None = None,
    *,
    seed: float | None = None,
    topology: GlyphTopology | Mapping[str, GlyphTopology] | None = None,
) -> GlyphOutline:
    """Build one glyph by replaying its frozen sampling topology.

    Sample points that mark a junction at the structure master are placed on
    the same junction here, so every wall run starts and stops where two
    pieces actually meet at this location.
    """

    p = coerce_params(params)
    frozen = _resolve_topology(name, topology)
    actual_seed = glyph_seed(name) if seed is None else seed
    key = (name, *_params_key(p), id(frozen), AUDIT_NEW_JUNCTIONS)
    cached = _IDEAL_CACHE.get(key)
    if cached is not None and cached[0] is frozen:
        return GlyphOutline(
            name,
            tuple(
                BuiltPiece(
                    tuple(
                        BuiltContour(
                            tuple(jitter_points(ideal, p.jit, actual_seed)),
                            ideal,
                            contour_index > 0,
                        )
                        for contour_index, ideal in enumerate(piece)
                    )
                )
                for piece in cached[1]
            ),
            p,
            actual_seed,
            frozen,
            cached[2],
        )
    builders = glyph_defs(p)
    if name not in builders:
        raise KeyError(name)
    pieces = builders[name]()
    if len(pieces) != len(frozen.pieces):
        raise ValueError(f"{name!r}: piece count differs from default topology")
    shapes = _glyph_shapes(pieces)
    built_pieces: list[BuiltPiece] = []
    unmatched = 0
    for piece_index, piece in enumerate(pieces):
        raw_contours = _raw_piece_contours(piece)
        contour_topologies = frozen.pieces[piece_index]
        if len(raw_contours) != len(contour_topologies):
            raise ValueError(f"{name!r}: contour count differs from default topology")
        other_shapes = [shape for index, shape in enumerate(shapes) if index != piece_index]
        built_contours: list[BuiltContour] = []
        for contour_index, raw in enumerate(raw_contours):
            contour_topology = contour_topologies[contour_index]
            points, _edges = _normalized(raw, contour_topology.reverse)
            if sum(span.edges for span in contour_topology.spans) != len(points):
                raise ValueError("raw contour edge count differs from frozen topology")
            ideal: list[SamplePoint] = []
            for span in contour_topology.spans:
                positions: Sequence[float] = ()
                buried: list[tuple[float, float]] | None = None
                if span.cuts:
                    state, found = _span_cuts(
                        points, span.start, span.edges, span.closed, other_shapes
                    )
                    reference = _reference_cuts(span)
                    positions, exact = _match_cuts(
                        reference, found, span.hidden_first, state,
                        span.closed, float(span.edges), span.arc,
                    )
                    buried = _buried_ranges(
                        state, found, span.closed, float(span.edges)
                    )
                    if not exact:
                        unmatched += 1
                elif span.arc and other_shapes:
                    state, found = _span_cuts(
                        points, span.start, span.edges, span.closed, other_shapes
                    )
                    buried = _buried_ranges(
                        state, found, span.closed, float(span.edges)
                    )
                elif AUDIT_NEW_JUNCTIONS and other_shapes:
                    state, found = _span_cuts(
                        points, span.start, span.edges, span.closed, other_shapes
                    )
                    if found or state != span.hidden_first:
                        unmatched += 1
                ideal.extend(_sample_span(points, span, positions, buried))
            jittered = jitter_points(ideal, p.jit, actual_seed)
            built_contours.append(
                BuiltContour(tuple(jittered), tuple(ideal), contour_index > 0)
            )
        built_pieces.append(BuiltPiece(tuple(built_contours)))
    if len(_IDEAL_CACHE) > 8192:
        _IDEAL_CACHE.clear()
    _IDEAL_CACHE[key] = (
        frozen,
        tuple(
            tuple(contour.ideal for contour in piece.contours)
            for piece in built_pieces
        ),
        unmatched,
    )
    return GlyphOutline(name, tuple(built_pieces), p, actual_seed, frozen, unmatched)


def _reference_cuts(span: SpanTopology) -> list[Cut]:
    """Rebuild ``(position, polarity)`` pairs from a frozen span."""

    if span.closed:
        # A closed span starts sampling at its first cut, which enters the
        # state of the first interval.
        polarity = 1 if span.hidden_first else -1
    else:
        polarity = -1 if span.hidden_first else 1
    cuts: list[Cut] = []
    for position in span.cuts:
        cuts.append((position, polarity))
        polarity = -polarity
    return cuts


def topology_signature(outline: GlyphOutline) -> tuple[int, tuple[int, ...]]:
    """Return the CI invariant ``(contour count, point counts)``."""

    contours = outline.contours
    return len(contours), tuple(len(contour.points) for contour in contours)


def assert_compatible(outlines: Sequence[GlyphOutline]) -> None:
    """Fail if any supplied master violates contour/point compatibility."""

    if not outlines:
        return
    expected = topology_signature(outlines[0])
    for outline in outlines[1:]:
        actual = topology_signature(outline)
        if actual != expected:
            raise AssertionError(
                f"{outline.name!r}: topology {actual!r} differs from {expected!r}"
            )


WallColor = Literal["bronze", "dark"]


@dataclass(frozen=True, slots=True)
class WallRun:
    """One frozen visible edge run; ``end`` may wrap beyond contour length.

    ``segments`` splits the run wherever the set of sources at which an edge
    faces the extrusion changes. Each segment becomes its own wall contour,
    so a wall is either fully raised or fully flat at any one source.
    """

    piece_index: int
    contour_index: int
    start: int
    end: int
    color: WallColor
    arc: bool
    default_length: float
    segments: tuple[tuple[int, int], ...] = ()

    @property
    def walls(self) -> tuple[tuple[int, int], ...]:
        return self.segments or ((self.start, self.end),)


@dataclass(frozen=True, slots=True)
class HatchGroup:
    """A frozen light/shade transition that always emits seven marks."""

    piece_index: int
    contour_index: int
    anchor_edge: int
    before_run: int
    after_run: int
    count: int = HATCH_N


@dataclass(frozen=True, slots=True)
class FrozenRecipe:
    """Default-master wall labels and hatch anchors for one visual family."""

    name: str
    hand: bool
    jitter_amp: float
    topology: GlyphTopology
    runs: tuple[WallRun, ...]
    hatch_groups: tuple[HatchGroup, ...]


@dataclass(slots=True)
class _MutableRun:
    color: WallColor
    start: int
    end: int
    arc: bool
    length: float = 0.0


def _run_points(points: Sequence[SamplePoint], start: int, end: int) -> list[SamplePoint]:
    count = len(points)
    return [points[index % count] for index in range(start, end + 1)]


def _polyline_length(points: Sequence[SamplePoint]) -> float:
    return sum(
        _js_hypot(points[index].x - points[index - 1].x, points[index].y - points[index - 1].y)
        for index in range(1, len(points))
    )


def freeze_recipe(
    name: str,
    params: ParamsLike | None = None,
    *,
    hand: bool = False,
    seed: float | None = None,
    topology: GlyphTopology | Mapping[str, GlyphTopology] | None = None,
    masters: Sequence[ParamsLike] | None = None,
) -> FrozenRecipe:
    """Freeze edge visibility/labels at D, separately for regular and hand.

    Junction burial and wall colour come from D. Whether an edge faces the
    extrusion is taken across ``masters`` (the design sources by default): a
    stroke that lies almost along the depth vector shows one side at one
    width and the other side at another, so both sides own a wall and each
    is raised only where it faces. A terminal cap that faces away gets no
    wall: under a nonzero fill its reversed winding would erase the wall
    beside it.
    """

    p = coerce_params(params)
    p = replace(p, jit=3.4 if hand else 0.0, hatch_n=HATCH_N)
    frozen = _resolve_topology(name, topology)
    outline = build_contours(name, p, seed=seed, topology=frozen)
    vx, vy = p.v
    frozen_runs: list[WallRun] = []
    hatch_groups: list[HatchGroup] = []
    sources = [outline] + [
        build_contours(name, replace(coerce_params(master), jit=0.0), topology=frozen)
        for master in (design_masters() if masters is None else masters)
    ]

    depth = _js_hypot(vx, vy) or 1.0

    def facing_pattern(
        piece_index: int, contour_index: int, index: int
    ) -> tuple[bool, tuple[int, ...]]:
        """Return whether the edge ever shows a wall, and its state per source.

        States are +1 raised (exposed and facing the extrusion), -1 flat
        (buried in another piece, or facing away), 0 edge-on. Only an
        exposed curve chord may be edge-on. Its wall is a sliver there, so
        it can share a contour with either neighbour; a straight edge is
        long enough that a wrongly raised wall would show.
        """

        ever = False
        pattern: list[int] = []
        for source in sources:
            points = source.pieces[piece_index].contours[contour_index].ideal
            a = points[index]
            b = points[(index + 1) % len(points)]
            dx, dy = b.x - a.x, b.y - a.y
            length = _js_hypot(dx, dy)
            if length <= 1e-9:
                pattern.append(0)
                continue
            if a.hidden:
                pattern.append(-1)
                continue
            dot = (dy * vx - dx * vy) / length
            ever = ever or dot > 0.02
            if a.arc and abs(dot) <= EDGE_ON_TOLERANCE * depth:
                pattern.append(0)
            else:
                pattern.append(1 if dot > 0.02 else -1)
        return ever, tuple(pattern)

    for piece_index, piece in enumerate(outline.pieces):
        for contour_index, contour in enumerate(piece.contours):
            ideal, drawn = contour.ideal, contour.points
            count = len(ideal)
            edge_data: list[tuple[bool, WallColor | None, bool]] = []
            patterns: list[tuple[int, ...]] = []
            for index, point in enumerate(ideal):
                other = ideal[(index + 1) % count]
                dx, dy = other.x - point.x, other.y - point.y
                length = _js_hypot(dx, dy) or 1.0
                nx, ny = dy / length, -dx / length
                # An edge owns a wall if it is exposed and faces the
                # extrusion at any source; sampling put a point on every
                # junction, so no edge straddles one.
                ever, pattern = facing_pattern(piece_index, contour_index, index)
                patterns.append(pattern)
                visible = ever
                color: WallColor | None
                if not visible:
                    color = None
                elif point.force:
                    color = "dark"
                elif ny >= abs(nx):
                    color = "dark"
                elif nx > 0:
                    color = "bronze"
                elif ny > 0:
                    color = "dark"
                else:
                    color = "bronze"
                edge_data.append((visible, color, point.arc))

            runs: list[_MutableRun] = []
            current: _MutableRun | None = None
            for index, (visible, color, is_arc) in enumerate(edge_data):
                if not visible:
                    current = None
                    continue
                assert color is not None
                if current is not None and current.color == color and current.end == index:
                    current.end = index + 1
                    current.arc = current.arc or is_arc
                else:
                    current = _MutableRun(color, index, index + 1, is_arc)
                    runs.append(current)
            if len(runs) > 1:
                first, last = runs[0], runs[-1]
                if first.start == 0 and last.end == count and first.color == last.color:
                    last.end = count + first.end
                    last.arc = last.arc or first.arc
                    runs.pop(0)

            for run in runs:
                run.length = _polyline_length(_run_points(drawn, run.start, run.end))
                if run.color == "bronze" and run.length < 80:
                    run.color = "dark"

            local_global_indices: list[int] = []
            for run in runs:
                local_global_indices.append(len(frozen_runs))
                # Split the run wherever an edge faces the other way from
                # the wall collected so far at any source.
                segments: list[tuple[int, int]] = []
                segment_start = run.start
                held = list(patterns[run.start % count])
                for edge in range(run.start + 1, run.end):
                    signs = patterns[edge % count]
                    if any(a * b < 0 for a, b in zip(held, signs)):
                        segments.append((segment_start, edge))
                        segment_start = edge
                        held = list(signs)
                    else:
                        held = [a or b for a, b in zip(held, signs)]
                segments.append((segment_start, run.end))
                frozen_runs.append(
                    WallRun(
                        piece_index,
                        contour_index,
                        run.start,
                        run.end,
                        run.color,
                        run.arc,
                        run.length,
                        tuple(segments),
                    )
                )

            if len(runs) < 2:
                continue
            for run_index, first in enumerate(runs):
                second_index = (run_index + 1) % len(runs)
                second = runs[second_index]
                if first.color == second.color:
                    continue
                if second.start % count != first.end % count:
                    continue
                if not (first.arc or second.arc):
                    continue
                if first.length < 60 or second.length < 60:
                    continue
                hatch_groups.append(
                    HatchGroup(
                        piece_index,
                        contour_index,
                        first.end % count,
                        local_global_indices[run_index],
                        local_global_indices[second_index],
                        HATCH_N,
                    )
                )

    return FrozenRecipe(
        name,
        hand,
        p.jit,
        frozen,
        tuple(frozen_runs),
        tuple(hatch_groups),
    )


def freeze_recipes(
    name: str,
    params: ParamsLike | None = None,
    *,
    seed: float | None = None,
    topology: GlyphTopology | Mapping[str, GlyphTopology] | None = None,
) -> tuple[FrozenRecipe, FrozenRecipe]:
    """Freeze the regular and hand recipes independently at the same D."""

    frozen = _resolve_topology(name, topology)
    return (
        freeze_recipe(name, params, hand=False, seed=seed, topology=frozen),
        freeze_recipe(name, params, hand=True, seed=seed, topology=frozen),
    )


@dataclass(frozen=True, slots=True)
class LayerPiece:
    """One closed layer shape and optional holes, ready for UFO conversion.

    ``flat`` marks a wall that faces away from the extrusion at this source
    and therefore carries no depth.
    """

    outer: tuple[SamplePoint, ...]
    holes: tuple[tuple[SamplePoint, ...], ...] = ()
    flat: bool = False

    @property
    def contours(self) -> tuple[tuple[SamplePoint, ...], ...]:
        return (self.outer, *self.holes)


@dataclass(frozen=True, slots=True)
class ReplayedLayers:
    """Interpolation-compatible geometry for the COLRv1 paint layers."""

    outline: GlyphOutline
    wall_dark: tuple[LayerPiece, ...]
    wall_bronze: tuple[LayerPiece, ...]
    hatch: tuple[LayerPiece, ...]
    keyline: tuple[LayerPiece, ...]
    face: tuple[LayerPiece, ...]


# A curve chord within this sine of the depth direction counts as edge-on.
EDGE_ON_TOLERANCE = 0.06
# Share of the depth vector kept by a wall that faces away from the extrusion.
FLAT_WALL_DEPTH = 1e-3


def _wall_piece(
    points: Sequence[SamplePoint],
    start: int,
    end: int,
    vector: tuple[float, float],
) -> LayerPiece:
    """Return one wall contour: a front run and its translated rear run.

    A run that faces away from the extrusion here, or that another piece
    buries here, is kept flat. It keeps its point structure for
    interpolation and cannot cancel a neighbouring wall. The residual depth only keeps its points distinct, so no tool
    merges them and changes the point count.
    """

    run_points = _run_points(points, start, end)
    swept = 0.0
    buried = 0
    for a, b in zip(run_points, run_points[1:]):
        swept += (b.y - a.y) * vector[0] - (b.x - a.x) * vector[1]
        buried += a.hidden
    flat = swept <= 0 or 2 * buried > len(run_points) - 1
    depth = FLAT_WALL_DEPTH if flat else 1.0
    back = [
        point.translated(vector[0] * depth, vector[1] * depth)
        for point in reversed(run_points)
    ]
    return LayerPiece(tuple(run_points + back), flat=flat)


def _walk_contour(
    points: Sequence[SamplePoint], start: int, distance: float, direction: int
) -> SamplePoint:
    count = len(points)
    index = start
    remaining = distance
    for _ in range(count + 1):
        a = points[index % count]
        b = points[(index + direction) % count]
        length = _js_hypot(b.x - a.x, b.y - a.y)
        if remaining <= length or length == 0:
            ratio = 0.0 if length == 0 else remaining / length
            return SamplePoint(
                a.x + (b.x - a.x) * ratio,
                a.y + (b.y - a.y) * ratio,
                a.arc and b.arc,
                a.force or b.force,
            )
        remaining -= length
        index += direction
    return points[index % count]


def _hatch_quad(
    center: SamplePoint,
    vector: tuple[float, float],
    thickness: float,
) -> LayerPiece:
    """Build one nominal full-thickness four-point hatch mark."""

    vx, vy = vector
    depth = _js_hypot(vx, vy) or 1.0
    ux, uy = vx / depth, vy / depth
    half_length = depth * 0.4
    px, py = -uy * thickness / 2, ux * thickness / 2
    start = SamplePoint(center.x - ux * half_length, center.y - uy * half_length)
    end = SamplePoint(center.x + ux * half_length, center.y + uy * half_length)
    return LayerPiece(
        (
            SamplePoint(start.x + px, start.y + py),
            SamplePoint(end.x + px, end.y + py),
            SamplePoint(end.x - px, end.y - py),
            SamplePoint(start.x - px, start.y - py),
        )
    )


def _offset_contour(points: Sequence[SamplePoint], distance: float) -> tuple[SamplePoint, ...]:
    result: list[SamplePoint] = []
    count = len(points)
    for index, point in enumerate(points):
        previous = points[index - 1]
        following = points[(index + 1) % count]
        d1 = (point.x - previous.x, point.y - previous.y)
        d2 = (following.x - point.x, following.y - point.y)
        l1, l2 = _js_hypot(*d1) or 1.0, _js_hypot(*d2) or 1.0
        n1, n2 = (d1[1] / l1, -d1[0] / l1), (d2[1] / l2, -d2[0] / l2)
        p1 = (point.x + n1[0] * distance, point.y + n1[1] * distance)
        p2 = (point.x + n2[0] * distance, point.y + n2[1] * distance)
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-9:
            x, y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        else:
            t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
            x, y = p1[0] + d1[0] * t, p1[1] + d1[1] * t
            if _js_hypot(x - point.x, y - point.y) > distance * 8:
                x, y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        result.append(SamplePoint(x, y, point.arc, point.force))
    return tuple(result)


def replay_recipe(
    recipe: FrozenRecipe,
    params: ParamsLike | None = None,
    *,
    seed: float | None = None,
    keyline_offset: float = 7.5,
) -> ReplayedLayers:
    """Replay one frozen recipe with seven topology-stable hatches per group."""

    p = coerce_params(params)
    p = replace(p, jit=recipe.jitter_amp, hatch_n=HATCH_N)
    outline = build_contours(recipe.name, p, seed=seed, topology=recipe.topology)
    vector = p.v
    dark: list[LayerPiece] = []
    bronze: list[LayerPiece] = []
    for run in recipe.runs:
        points = outline.pieces[run.piece_index].contours[run.contour_index].points
        target = bronze if run.color == "bronze" else dark
        for start, end in run.walls:
            target.append(_wall_piece(points, start, end, vector))

    hatches: list[LayerPiece] = []
    for group in recipe.hatch_groups:
        contour = outline.pieces[group.piece_index].contours[group.contour_index].points
        before_run = recipe.runs[group.before_run]
        after_run = recipe.runs[group.after_run]
        before_length = _polyline_length(
            _run_points(contour, before_run.start, before_run.end)
        )
        after_length = _polyline_length(
            _run_points(contour, after_run.start, after_run.end)
        )
        half = HATCH_N // 2
        guard = p.hatch_t / 2
        before_spacing = min(
            p.hatch_sp,
            max(0.0, (before_length - guard) / half),
        )
        after_spacing = min(
            p.hatch_sp,
            max(0.0, (after_length - guard) / half),
        )
        for mark in range(-half, half + 1):
            spacing = after_spacing if mark >= 0 else before_spacing
            boundary = _walk_contour(
                contour,
                group.anchor_edge,
                abs(mark) * spacing,
                1 if mark >= 0 else -1,
            )
            center = boundary.translated(vector[0] * 0.5, vector[1] * 0.5)
            hatch = _hatch_quad(center, vector, p.hatch_t)
            hatches.append(hatch)

    face: list[LayerPiece] = []
    keyline: list[LayerPiece] = []
    for piece in outline.pieces:
        face.append(
            LayerPiece(
                piece.outer.points,
                tuple(hole.points for hole in piece.holes),
            )
        )
        for contour in piece.contours:
            keyline.append(
                LayerPiece(
                    _offset_contour(contour.points, keyline_offset),
                    (tuple(reversed(contour.points)),),
                )
            )

    return ReplayedLayers(
        outline,
        tuple(dark),
        tuple(bronze),
        tuple(hatches),
        tuple(keyline),
        tuple(face),
    )


# Engine aliases retain the canonical JS names for audits and spot comparisons.
signedArea = signed_area
ptIn = point_in
jitterPts = jitter_points
buildGlyph = build_contours


# Deterministic canonical inventory: 138 direct builders followed by CAP then LC.
GLYPH_CHARS = tuple(glyph_defs())
DIRECT_GLYPH_CHARS = GLYPH_CHARS[:138]
