"""Canonical Lötschberg parametric glyph generator.

This is a direct Python port of ``Loetschberg Character Grid.dc.html``.  All
coordinates remain in the source's y-down coordinate system; font-coordinate
conversion belongs to the build layer.  The specimen generator is deliberately
not consulted here.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from math import ceil, cos, inf, pi, sin, sqrt
from typing import Literal, TypeAlias


# SHA-256 of the decoded text inside the canonical ``data-dc-script`` element.
GRID_SOURCE_SHA256 = "b42ad1dfdf204d650da26e35624b3283466350efb0bf780ad0fb3777ee02f47a"
# SHA-256 of the complete containing HTML file, useful for source-governance CI.
GRID_HTML_SHA256 = "c0c10bb4c72138d3ebc13e2ba509899f57036c49afc1baecc6a0cf84fdf9c985"
HATCH_N = 7
SUBDIVISION_MAX_LENGTH = 24.0

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


def _raw_contours_touch(
    first: Sequence[RawPoint],
    second: Sequence[RawPoint],
    *,
    epsilon: float = 1e-7,
) -> bool:
    """Return whether two closed raw contours intersect or contain a vertex."""

    first_xy = tuple((point[0], point[1]) for point in first)
    second_xy = tuple((point[0], point[1]) for point in second)

    def cross(
        a: tuple[float, float],
        b: tuple[float, float],
        c: tuple[float, float],
    ) -> float:
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
            and min(a[0], b[0]) - epsilon
            <= point[0]
            <= max(a[0], b[0]) + epsilon
            and min(a[1], b[1]) - epsilon
            <= point[1]
            <= max(a[1], b[1]) + epsilon
        )

    def segments_intersect(
        a: tuple[float, float],
        b: tuple[float, float],
        c: tuple[float, float],
        d: tuple[float, float],
    ) -> bool:
        ab_c, ab_d = cross(a, b, c), cross(a, b, d)
        cd_a, cd_b = cross(c, d, a), cross(c, d, b)
        if (
            ((ab_c > epsilon and ab_d < -epsilon) or
             (ab_c < -epsilon and ab_d > epsilon))
            and ((cd_a > epsilon and cd_b < -epsilon) or
                 (cd_a < -epsilon and cd_b > epsilon))
        ):
            return True
        return (
            on_segment(a, b, c)
            or on_segment(a, b, d)
            or on_segment(c, d, a)
            or on_segment(c, d, b)
        )

    for a, b in zip(
        first_xy,
        first_xy[1:] + first_xy[:1],
        strict=True,
    ):
        for c, d in zip(
            second_xy,
            second_xy[1:] + second_xy[:1],
            strict=True,
        ):
            if segments_intersect(a, b, c, d):
                return True

    def contains(
        point: tuple[float, float],
        polygon: tuple[tuple[float, float], ...],
    ) -> bool:
        inside = False
        previous = polygon[-1]
        for current in polygon:
            if on_segment(previous, current, point):
                return True
            if (current[1] > point[1]) != (previous[1] > point[1]):
                crossing_x = (
                    (previous[0] - current[0])
                    * (point[1] - current[1])
                    / (previous[1] - current[1])
                    + current[0]
                )
                if point[0] < crossing_x:
                    inside = not inside
            previous = current
        return inside

    return contains(first_xy[0], second_xy) or contains(
        second_xy[0],
        first_xy,
    )


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
) -> list[RawPoint]:
    """Port of ``arcPts``; sample count depends only on angular span."""

    n = max(2, ceil(abs(a1 - a0) / 4))
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


def glyph_defs(params: ParamsLike | None = None) -> dict[str, Builder]:
    """Return all 138 direct grid builders plus the CAP/LC compositions."""

    p = coerce_params(params)
    S, SH, W = p.s, p.sh, p.w
    weight_ratio = S / 104.0

    def protected_curve_strokes(
        ro: float,
        ri: float,
    ) -> tuple[float, float, float, float]:
        """Return skeleton-scaled x radii and counter-safe y radii.

        Width acts on the round stroke's centreline rather than its outer
        boundary.  This keeps the physical stroke independent from ``wdth``.
        Weight grows into the counter, but compact bowls retain a deliberate
        aperture instead of collapsing or inverting at Black Condensed.
        """

        base_stroke = ro - ri
        desired_stroke = base_stroke * weight_ratio
        heavy_progress = min(
            1.0,
            max(0.0, (desired_stroke - base_stroke) / max(base_stroke * 0.7, 1)),
        )

        skeleton_rx = (ro + ri) * W / 2
        counter_floor_x = max(16.0, ri * W * 0.35)
        stroke_x = min(
            desired_stroke,
            max(1.0, 2 * (skeleton_rx - counter_floor_x)),
        )
        outward_share = 0.5 + 0.12 * heavy_progress
        outer_rx = skeleton_rx + stroke_x * outward_share
        inner_rx = skeleton_rx - stroke_x * (1 - outward_share)

        # Keep the canonical silhouette at Regular. Above it, distribute new
        # curve weight both outside and inside instead of consuming the full
        # counter. This is the round-glyph counterpart to the weight-aware
        # skeleton expansion used by straight and diagonal construction.
        counter_floor_y = max(18.0, ri * 0.35)
        added_stroke_y = max(0.0, desired_stroke - base_stroke)
        outer_ry = ro + added_stroke_y * 0.35
        inner_ry = max(
            counter_floor_y,
            ri - added_stroke_y * 0.65,
        )
        return outer_rx, inner_rx, outer_ry, inner_ry

    # ``w`` is applied to the canonical grid geometry, never to stale specimen
    # outlines. Coordinates that place skeleton features scale in x while
    # physical stroke thickness is controlled by weight. The tests below use
    # the canonical rectangle dimensions, not the current weight, so a heavy
    # short stem cannot accidentally change from a stem into a layout box.
    def R(x0: float, y0: float, x1: float, y1: float) -> Contour:
        width, height = abs(x1 - x0), abs(y1 - y0)
        is_horizontal = (
            (abs(height - S) < 1e-9 or abs(height - SH) < 1e-9)
            and width > 1.01 * min(height, 104.0)
        ) or (height <= 150.0 and width > 1.5 * height)
        is_vertical = (
            (abs(width - S) < 1e-9 or abs(width - 104.0) < 1e-9)
            and height > 1.01 * min(width, 104.0)
        ) or (width <= 150.0 and height > 1.5 * width)
        if is_vertical and not is_horizontal:
            target_width = (
                width
                if abs(width - S) < 1e-9
                else width * weight_ratio
            )
            if x0 == 0:
                xx0, xx1 = 0.0, target_width
            else:
                center = (x0 + x1) * W / 2
                xx0, xx1 = center - target_width / 2, center + target_width / 2
            return rect(xx0, y0, xx1, y1)
        if is_horizontal:
            if abs(height - S) < 1e-9 or abs(height - SH) < 1e-9:
                target_height = height
            elif abs(height - 104.0) < 1e-9:
                target_height = S
            elif abs(height - 100.0) < 1e-9:
                target_height = SH
            else:
                target_height = height * (SH / 100.0)
            if y0 == 0:
                yy0, yy1 = 0.0, target_height
            elif y1 == 700:
                yy0, yy1 = 700.0 - target_height, 700.0
            else:
                center = (y0 + y1) / 2
                yy0, yy1 = center - target_height / 2, center + target_height / 2
            return rect(x0 * W, yy0, x1 * W, yy1)
        return rect(x0 * W, y0, x1 * W, y1)

    def vstem(
        center: float,
        y0: float,
        y1: float,
        canonical_width: float = 104.0,
    ) -> Contour:
        """Build a vertical stroke about an explicitly scaled skeleton."""

        width = canonical_width * weight_ratio
        cx = center * W
        return rect(cx - width / 2, y0, cx + width / 2, y1)

    def hstem(
        x0: float,
        x1: float,
        center: float,
        canonical_height: float = 100.0,
    ) -> Contour:
        """Build a horizontal stroke with explicit attachment coordinates."""

        height = canonical_height * (SH / 100.0)
        return rect(x0, center - height / 2, x1, center + height / 2)

    def Q(points: Sequence[Sequence[float]]) -> Contour:
        if (
            len(points) == 4
            and abs(points[0][1] - points[1][1]) < 1e-9
            and abs(points[2][1] - points[3][1]) < 1e-9
        ):
            transformed: list[tuple[float, float]] = []
            for first, second in ((points[0], points[1]), (points[3], points[2])):
                mx, my = (first[0] + second[0]) / 2, (first[1] + second[1]) / 2
                dx, dy = (first[0] - second[0]) / 2, (first[1] - second[1]) / 2
                transformed.extend(
                    [
                        (mx * W + dx * weight_ratio, my + dy * weight_ratio),
                        (mx * W - dx * weight_ratio, my - dy * weight_ratio),
                    ]
                )
            # The second pair was traversed 3 -> 2; restore source point order.
            return quad([transformed[0], transformed[1], transformed[3], transformed[2]])

        if len(points) == 4:
            # General four-point strokes (R leg, 1 flag, comma tail, etc.)
            # need the same skeleton/weight treatment as horizontal-paired
            # diagonals.  Preserve the canonical default bit-for-bit.
            if abs(W - 1.0) < 1e-12 and abs(weight_ratio - 1.0) < 1e-12:
                return quad(points)

            source = [(float(q[0]), float(q[1])) for q in points]

            def edge_length(index: int) -> float:
                first, second = source[index], source[(index + 1) % 4]
                return _js_hypot(second[0] - first[0], second[1] - first[1])

            # Opposite short edges are the stroke caps.
            cap_start = min(
                (0, 1),
                key=lambda index: edge_length(index) + edge_length(index + 2),
            )
            cap_indices = (cap_start, (cap_start + 2) % 4)
            base_width = sum(edge_length(index) for index in cap_indices) / 2
            target_width = max(1.0, base_width * weight_ratio)
            transformed: list[tuple[float, float] | None] = [None] * 4

            cap_midpoints = []
            for index in cap_indices:
                first, second = source[index], source[(index + 1) % 4]
                cap_midpoints.append(
                    (
                        (first[0] + second[0]) * W / 2,
                        (first[1] + second[1]) / 2,
                    )
                )
            dx = cap_midpoints[1][0] - cap_midpoints[0][0]
            dy = cap_midpoints[1][1] - cap_midpoints[0][1]
            length = _js_hypot(dx, dy) or 1.0
            normal = (-dy / length, dx / length)

            for index, midpoint in zip(cap_indices, cap_midpoints):
                next_index = (index + 1) % 4
                original_vector = (
                    source[next_index][0] * W - source[index][0] * W,
                    source[next_index][1] - source[index][1],
                )
                orientation = (
                    1.0
                    if original_vector[0] * normal[0]
                    + original_vector[1] * normal[1]
                    >= 0
                    else -1.0
                )
                half_x = normal[0] * target_width / 2 * orientation
                half_y = normal[1] * target_width / 2 * orientation
                transformed[index] = (midpoint[0] - half_x, midpoint[1] - half_y)
                transformed[next_index] = (
                    midpoint[0] + half_x,
                    midpoint[1] + half_y,
                )
            if all(point is not None for point in transformed):
                return quad([point for point in transformed if point is not None])

        return quad([(q[0] * W, q[1]) for q in points])

    def diagonal_strip_hex(
        center_a: tuple[float, float],
        center_b: tuple[float, float],
        base_thickness: float,
        bounds: tuple[float, float, float, float],
        canonical: Sequence[Sequence[float]],
    ) -> Contour:
        """Clip a constant-width diagonal skeleton to a rectangular box.

        The selected Z/z geometry always has the same six intersections:
        top edge, top-right corner, right edge, bottom edge,
        bottom-left corner, and left edge. Keeping those semantic vertices
        fixed gives interpolation a stable point order at every axis corner.
        """

        if abs(W - 1.0) < 1e-12 and abs(weight_ratio - 1.0) < 1e-12:
            return quad(canonical)

        ax, ay = center_a[0] * W, center_a[1]
        bx, by = center_b[0] * W, center_b[1]
        dx, dy = bx - ax, by - ay
        length = _js_hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length
        half = base_thickness * weight_ratio / 2
        left, right, top, bottom = (
            bounds[0] * W,
            bounds[1] * W,
            bounds[2],
            bounds[3],
        )

        def x_at(y: float, offset: float) -> float:
            return ax + (offset - ny * (y - ay)) / nx

        def y_at(x: float, offset: float) -> float:
            return ay + (offset - nx * (x - ax)) / ny

        return quad(
            [
                (x_at(top, half), top),
                (right, top),
                (right, y_at(right, -half)),
                (x_at(bottom, -half), bottom),
                (left, bottom),
                (left, y_at(left, half)),
            ]
        )

    def vertically_clipped_band(
        top_center: tuple[float, float],
        bottom_center: tuple[float, float],
        top: float,
        bottom: float,
        canonical_cap_width: float = 104.0,
    ) -> Contour:
        """A diagonal band clipped to horizontal joins at both ends."""

        ax, ay = top_center[0] * W, top_center[1]
        bx, by = bottom_center[0] * W, bottom_center[1]
        if abs(by - ay) < 1e-9:
            raise ValueError("clipped band requires a non-horizontal skeleton")

        def center_x(y: float) -> float:
            return ax + (bx - ax) * (y - ay) / (by - ay)

        half = canonical_cap_width * weight_ratio / 2
        top_x, bottom_x = center_x(top), center_x(bottom)
        return quad(
            [
                (top_x - half, top),
                (top_x + half, top),
                (bottom_x + half, bottom),
                (bottom_x - half, bottom),
            ]
        )

    def RS(
        cx: float,
        cy: float,
        ro: float,
        ri: float,
        oa0: float,
        oa1: float,
        ia0: float,
        ia1: float,
        _sx: float | None = None,
        caps: object = None,
    ) -> Contour:
        outer_rx, inner_rx, outer_ry, inner_ry = protected_curve_strokes(ro, ri)
        outer = arc_pts(cx * W, cy, outer_rx, outer_ry, oa0, oa1)
        inner = arc_pts(cx * W, cy, inner_rx, inner_ry, ia0, ia1)
        if caps:
            outer[-1] = (outer[-1][0], outer[-1][1], 2)
            inner[-1] = (inner[-1][0], inner[-1][1], 2)
        return Contour(outer + inner)

    def RSXY(
        cx: float,
        cy: float,
        rox: float,
        rix: float,
        roy: float,
        riy: float,
        oa0: float,
        oa1: float,
        ia0: float,
        ia1: float,
        caps: object = None,
    ) -> Contour:
        """Anisotropic ring sector with skeleton-scaled x and explicit y."""

        outer_rx, inner_rx, _outer_ry, _inner_ry = protected_curve_strokes(
            rox, rix
        )
        outer = arc_pts(cx * W, cy, outer_rx, roy, oa0, oa1)
        inner = arc_pts(cx * W, cy, inner_rx, riy, ia0, ia1)
        if caps:
            outer[-1] = (outer[-1][0], outer[-1][1], 2)
            inner[-1] = (inner[-1][0], inner[-1][1], 2)
        return Contour(outer + inner)

    def connected_half_bowl(
        cx: float,
        first_center: float,
        second_center: float,
        rox: float,
        rix: float,
        oa0: float,
        oa1: float,
        ia0: float,
        ia1: float,
    ) -> Contour:
        """Build a half-bowl whose caps share the adjoining stroke centres."""

        cy = (first_center + second_center) / 2
        skeleton_ry = abs(second_center - first_center) / 2
        counter_floor = max(18.0, skeleton_ry * 0.18)
        stroke_y = min(S, max(1.0, 2 * (skeleton_ry - counter_floor)))
        outer_ry = skeleton_ry + stroke_y / 2
        inner_ry = skeleton_ry - stroke_y / 2
        return RSXY(
            cx,
            cy,
            rox,
            rix,
            outer_ry,
            inner_ry,
            oa0,
            oa1,
            ia0,
            ia1,
        )

    def pc(outer: Contour, holes: Sequence[Contour] | None = None) -> Piece:
        return _piece(outer, holes)

    def attach_quad_cap(
        body: Sequence[Piece],
        contour: Contour,
        moving_indices: Sequence[int],
        direction: tuple[float, float],
    ) -> Contour:
        """Extend one quad cap only enough to overlap its parent stroke."""

        length = _js_hypot(*direction) or 1.0
        ux, uy = direction[0] / length, direction[1] / length
        moving = frozenset(moving_indices)

        def extended(distance: float) -> Contour:
            return Contour(
                [
                    (
                        point[0] + (ux * distance if index in moving else 0),
                        point[1] + (uy * distance if index in moving else 0),
                        point[2],
                    )
                    for index, point in enumerate(contour.pts)
                ]
            )

        def touches(candidate: Contour) -> bool:
            return any(
                _raw_contours_touch(piece.outer.pts, candidate.pts)
                for piece in body
            )

        if touches(contour):
            return contour

        lower, upper = 0.0, 1.0
        while upper < 256 and not touches(extended(upper)):
            lower, upper = upper, upper * 2
        if not touches(extended(upper)):
            raise AssertionError("attachment cap cannot reach its parent stroke")
        for _ in range(40):
            middle = (lower + upper) / 2
            if touches(extended(middle)):
                upper = middle
            else:
                lower = middle

        # A positive overlap survives integer rounding and ordinary gvar
        # interpolation between the explicit width/weight source planes.
        return extended(upper + max(2.0, 0.08 * S))

    def disc(cx: float, cy: float, radius: float) -> Piece:
        weighted_radius = max(8.0, radius + (S - 104.0) * 0.25)
        return pc(ellipse(cx * W, cy, weighted_radius, weighted_radius))

    def ring_p(cx: float, cy: float, ro: float, ri: float) -> Piece:
        outer_rx, inner_rx, outer_ry, inner_ry = protected_curve_strokes(ro, ri)
        return pc(
            ellipse(cx * W, cy, outer_rx, outer_ry),
            [ellipse(cx * W, cy, inner_rx, inner_ry)],
        )

    def ellipse_ring_p(
        cx: float,
        cy: float,
        rox: float,
        rix: float,
        roy: float,
        riy: float,
    ) -> Piece:
        outer_rx, inner_rx, _unused_outer_y, _unused_inner_y = (
            protected_curve_strokes(rox, rix)
        )
        _unused_outer_x, _unused_inner_x, outer_ry, inner_ry = (
            protected_curve_strokes(roy, riy)
        )
        return pc(
            ellipse(cx * W, cy, outer_rx, outer_ry),
            [ellipse(cx * W, cy, inner_rx, inner_ry)],
        )

    def bar(x1: float, y1: float, x2: float, y2: float, width: float) -> Piece:
        width = width if abs(width - S) < 1e-9 else width * weight_ratio
        x1, x2 = x1 * W, x2 * W
        dx, dy = x2 - x1, y2 - y1
        length = _js_hypot(dx, dy) or 1.0
        px, py = -dy / length * width / 2, dx / length * width / 2
        return pc(
            Contour(
                [
                    (x1 + px, y1 + py, 0),
                    (x2 + px, y2 + py, 0),
                    (x2 - px, y2 - py, 0),
                    (x1 - px, y1 - py, 0),
                ]
            )
        )

    def leg(ax: float, ay: float, bx: float, by: float, width: float) -> Piece:
        width = width if abs(width - S) < 1e-9 else width * weight_ratio
        ax, bx = ax * W, bx * W
        dx, dy = bx - ax, by - ay
        length = _js_hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        px, py = -dy / length * width / 2, dx / length * width / 2
        a1, a2 = (ax + px, ay + py), (ax - px, ay - py)
        t1, t2 = (700 - a1[1]) / uy, (700 - a2[1]) / uy
        return pc(
            Contour(
                [
                    (a1[0], a1[1], 0),
                    (a1[0] + ux * t1, 700, 0),
                    (a2[0] + ux * t2, 700, 0),
                    (a2[0], a2[1], 0),
                ]
            )
        )

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

    def wave(cx: float, cy: float, half_len: float, amp: float, half_w: float) -> Piece:
        top: list[RawPoint] = []
        bottom: list[RawPoint] = []
        # Bound the offset by the sinusoid's minimum radius of curvature.
        # Without this cap, Black Condensed tildes fold back through themselves.
        curvature_radius = (half_len * W) ** 2 / (amp * pi**2)
        effective_half_w = min(
            half_w * weight_ratio,
            0.72 * curvature_radius,
        )
        for i in range(41):
            t = i / 40
            x = (cx - half_len + 2 * half_len * t) * W
            y = cy - amp * sin(2 * pi * t)
            d = -amp * cos(2 * pi * t) * pi / (half_len * W)
            length = _js_hypot(1, d)
            nx, ny = d / length, -1 / length
            top.append((x + nx * effective_half_w, y + ny * effective_half_w, 1))
            bottom.append((x - nx * effective_half_w, y - ny * effective_half_w, 1))
        return pc(Contour(top + list(reversed(bottom))))

    def chev(
        ax: float,
        ay: float,
        b1: Sequence[float],
        b2: Sequence[float],
        width: float,
    ) -> Piece:
        width *= weight_ratio
        ax *= W
        b1 = (b1[0] * W, b1[1])
        b2 = (b2[0] * W, b2[1])
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
        return pc(
            Contour(
                [(x, y, 0) for x, y in points]
            )
        )

    G: dict[str, Builder] = {}

    # Uppercase -- assignment order mirrors the canonical source.
    G["O"] = lambda: [ring_p(362, 350, 362, 258)]
    G["Ö"] = lambda: G["O"]() + [disc(225.5, -115, 63), disc(498.5, -115, 63)]
    G["C"] = lambda: [pc(RS(362, 350, 362, 258, -38, -322, -330, -30, 1, 1))]

    def glyph_g_cap() -> list[Piece]:
        outer_rx, _inner_rx, _outer_ry, _inner_ry = protected_curve_strokes(
            362, 258
        )
        outer_right = 362 * W + outer_rx
        aperture_x = 362 * W + outer_rx * cos(38 * pi / 180)
        terminal_left = outer_right - 116 * weight_ratio
        aperture_y = 350 + 362 * sin(38 * pi / 180)
        connector_padding = max(6.0, 0.1 * S)
        connector_left = min(aperture_x, terminal_left) - connector_padding
        connector_right = max(aperture_x, terminal_left) + connector_padding
        return [
            pc(RS(362, 350, 362, 258, -38, -322, -345, -30, 1, 1)),
            pc(rect(terminal_left, 325, outer_right, 700)),
            pc(
                hstem(
                    connector_left,
                    connector_right,
                    aperture_y,
                )
            ),
        ]

    G["G"] = glyph_g_cap

    def glyph_h_cap() -> list[Piece]:
        left_center, right_center = 52 * W, 578 * W
        return [
            pc(vstem(52, 0, 700)),
            pc(vstem(578, 0, 700)),
            pc(hstem(left_center + S / 2, right_center - S / 2, 371)),
        ]

    G["H"] = glyph_h_cap
    G["E"] = lambda: [
        pc(R(0, 0, 104, 700)),
        pc(R(0, 0, 590, SH)),
        pc(R(0, 310, 425, 410)),
        pc(R(0, 600, 596, 700)),
    ]
    G["L"] = lambda: [pc(R(0, 0, 104, 700)), pc(R(0, 600, 615, 700))]
    G["T"] = lambda: [pc(R(0, 0, 700, S)), pc(R(298, 0, 402, 700))]
    G["I"] = lambda: [pc(R(0, 0, 104, 700))]
    def glyph_s_cap() -> list[Piece]:
        top_center = S / 2
        middle_center = 345
        bottom_center = 700 - S / 2
        return [
            pc(R(198.5, 0, 690, S)),
            pc(
                connected_half_bowl(
                    198.5,
                    top_center,
                    middle_center,
                    198.5,
                    94.5,
                    90,
                    270,
                    270,
                    90,
                )
            ),
            pc(R(198.5, 345 - S / 2, 501.5, 345 + S / 2)),
            pc(
                connected_half_bowl(
                    501.5,
                    middle_center,
                    bottom_center,
                    203.5,
                    99.5,
                    -90,
                    90,
                    90,
                    -90,
                )
            ),
            pc(R(10, 700 - S, 501.5, 700)),
        ]

    G["S"] = glyph_s_cap

    def glyph_b_cap() -> list[Piece]:
        top_center = S / 2
        middle_center = 350
        bottom_center = 700 - S / 2
        return [
            pc(R(0, 0, 104, 700)),
            pc(R(0, 0, 404, S)),
            pc(R(0, 350 - S / 2, 419, 350 + S / 2)),
            pc(R(0, 700 - S, 419, 700)),
            pc(
                connected_half_bowl(
                    404,
                    top_center,
                    middle_center,
                    201,
                    97,
                    -90,
                    90,
                    90,
                    -90,
                )
            ),
            pc(
                connected_half_bowl(
                    419,
                    middle_center,
                    bottom_center,
                    201,
                    97,
                    -90,
                    90,
                    90,
                    -90,
                )
            ),
        ]

    G["B"] = glyph_b_cap

    def glyph_p_cap() -> list[Piece]:
        top_center = S / 2
        lower_center = 371
        return [
            pc(R(0, 0, 104, 700)),
            pc(R(0, 0, 393.5, S)),
            pc(R(0, lower_center - S / 2, 393.5, lower_center + S / 2)),
            pc(
                connected_half_bowl(
                    393.5,
                    top_center,
                    lower_center,
                    211.5,
                    107.5,
                    -90,
                    90,
                    90,
                    -90,
                )
            ),
        ]

    G["P"] = glyph_p_cap

    def glyph_r() -> list[Piece]:
        leg_top, u, px = (480, 380), (0.417, 0.909), (0.909, -0.417)
        tl = (leg_top[0] - px[0] * 52, leg_top[1] - px[1] * 52)
        tr = (leg_top[0] + px[0] * 52, leg_top[1] + px[1] * 52)
        br = (tr[0] + u[0] * ((700 - tr[1]) / u[1]), 700)
        bl = (tl[0] + u[0] * ((700 - tl[1]) / u[1]), 700)
        body = G["P"]()
        leg_contour = Q([tl, tr, br, bl])
        top_midpoint = (
            (leg_contour.pts[0][0] + leg_contour.pts[1][0]) / 2,
            (leg_contour.pts[0][1] + leg_contour.pts[1][1]) / 2,
        )
        bottom_midpoint = (
            (leg_contour.pts[2][0] + leg_contour.pts[3][0]) / 2,
            (leg_contour.pts[2][1] + leg_contour.pts[3][1]) / 2,
        )
        leg_contour = attach_quad_cap(
            body,
            leg_contour,
            (0, 1),
            (
                top_midpoint[0] - bottom_midpoint[0],
                top_midpoint[1] - bottom_midpoint[1],
            ),
        )
        return body + [pc(leg_contour)]

    G["R"] = glyph_r

    def glyph_m_cap() -> list[Piece]:
        center = 385 * W
        left_inner = 52 * W + S / 2
        right_inner = 718 * W - S / 2
        top_inset = 49.48120950323974 * weight_ratio
        inner_apex_y = 381.470462633452
        outer_apex_y = inner_apex_y + (
            487.9110320284698 - inner_apex_y
        ) * weight_ratio
        outer_cap_half = 48 * weight_ratio
        return [
            pc(vstem(52, 0, 700)),
            pc(vstem(718, 0, 700)),
            pc(
                quad(
                    [
                        (left_inner, 0),
                        (left_inner + top_inset, 0),
                        (center, inner_apex_y),
                        (right_inner - top_inset, 0),
                        (right_inner, 0),
                        (right_inner, S),
                        (center + outer_cap_half, outer_apex_y),
                        (center - outer_cap_half, outer_apex_y),
                        (left_inner, S),
                    ]
                )
            ),
        ]

    G["M"] = glyph_m_cap
    def glyph_n_cap() -> list[Piece]:
        left = pc(R(0, 0, 104, 700))
        right = pc(R(521, 0, 625, 700))
        diagonal = Q([(0, 0), (129.7, 0), (625, 700), (495.3, 700)])
        diagonal = attach_quad_cap([left], diagonal, (0, 1), (-1, 0))
        diagonal = attach_quad_cap([right], diagonal, (2, 3), (1, 0))
        return [left, right, pc(diagonal)]

    G["N"] = glyph_n_cap
    G["A"] = lambda: [
        pc(Q([(302, 0), (406, 0), (104, 700), (0, 700)])),
        pc(Q([(302, 0), (406, 0), (708, 700), (604, 700)])),
        pc(R(120, 440, 590, 540)),
    ]
    G["D"] = lambda: [
        pc(R(0, 0, 104, 700)),
        pc(R(0, 0, 340, 104)),
        pc(R(0, 596, 340, 700)),
        pc(RS(340, 350, 350, 246, -90, 90, 90, -90)),
    ]
    G["F"] = lambda: [pc(R(0, 0, 104, 700)), pc(R(0, 0, 590, SH)), pc(R(0, 310, 425, 410))]
    G["J"] = lambda: [
        pc(R(396, 0, 500, 550)),
        pc(RS(347, 547, 153, 49, 0, 180, 180, 0, 1, 1)),
    ]
    G["K"] = lambda: [pc(R(0, 0, 104, 700)), bar(50, 478, 590, 48, S), leg(240, 335, 620, 700, S)]
    G["Q"] = lambda: G["O"]() + [bar(440, 460, 760, 790, S)]
    G["U"] = lambda: [
        pc(vstem(52, 0, 400)),
        pc(vstem(578, 0, 400)),
        pc(RS(315, 397, 315, 211, 180, 0, 0, 180)),
    ]
    G["V"] = lambda: [
        pc(Q([(0, 0), (104, 0), (389, 700), (285, 700)])),
        pc(Q([(570, 0), (674, 0), (389, 700), (285, 700)])),
    ]
    G["W"] = lambda: [
        pc(Q([(0, 0), (104, 0), (292, 700), (188, 700)])),
        pc(Q([(292, 700), (188, 700), (428, 60), (532, 60)])),
        pc(Q([(428, 60), (532, 60), (772, 700), (668, 700)])),
        pc(Q([(668, 700), (772, 700), (960, 0), (856, 0)])),
    ]
    G["X"] = lambda: [
        pc(Q([(0, 0), (104, 0), (644, 700), (540, 700)])),
        pc(Q([(540, 0), (644, 0), (104, 700), (0, 700)])),
    ]
    G["Y"] = lambda: [
        pc(Q([(0, 0), (104, 0), (374, 380), (270, 380)])),
        pc(Q([(536, 0), (640, 0), (374, 380), (270, 380)])),
        pc(R(268, 360, 372, 700)),
    ]
    G["Z"] = lambda: [
        pc(R(0, 0, 620, SH)),
        pc(R(0, 600, 620, 700)),
        pc(
            diagonal_strip_hex(
                (581.7, 60),
                (38.3, 640),
                110.59591548657296,
                (0, 620, 20, 680),
                [
                    (543.4, 20),
                    (620, 20),
                    (620, 100),
                    (76.6, 680),
                    (0, 680),
                    (0, 600),
                ],
            )
        ),
    ]

    # Digits.
    G["0"] = lambda: [ellipse_ring_p(310, 350, 310, 206, 362, 258)]

    def glyph_one() -> list[Piece]:
        x0, u, pp = 150, (-0.743, 0.669), (0.669, 0.743)
        a = (x0, 0)
        b = (x0 + u[0] * 150, u[1] * 150)
        # Q applies the active weight to this canonical 104-unit band.
        # Feeding S here would scale the Thin flag twice.
        c = (b[0] + pp[0] * 104, b[1] + pp[1] * 104)
        d = (a[0] + pp[0] * 104, a[1] + pp[1] * 104)
        stem = pc(R(x0, 0, x0 + 104, 700))
        flag = Q([a, b, c, d])
        far_midpoint = (
            (flag.pts[1][0] + flag.pts[2][0]) / 2,
            (flag.pts[1][1] + flag.pts[2][1]) / 2,
        )
        attachment_midpoint = (
            (flag.pts[3][0] + flag.pts[0][0]) / 2,
            (flag.pts[3][1] + flag.pts[0][1]) / 2,
        )
        flag = attach_quad_cap(
            [stem],
            flag,
            (0, 3),
            (
                attachment_midpoint[0] - far_midpoint[0],
                attachment_midpoint[1] - far_midpoint[1],
            ),
        )
        return [stem, pc(flag)]

    G["1"] = glyph_one
    def glyph_two() -> list[Piece]:
        outer_rx, inner_rx, outer_ry, inner_ry = protected_curve_strokes(
            322, 218
        )
        angle = 30 * pi / 180
        inner_cap = (
            322 * W + inner_rx * cos(angle),
            322 + inner_ry * sin(angle),
        )
        outer_cap = (
            322 * W + outer_rx * cos(angle),
            322 + outer_ry * sin(angle),
        )
        return [
            pc(RS(322, 322, 322, 218, 180, 390, 390, 180, 1, 1)),
            pc(
                quad(
                    [
                        inner_cap,
                        outer_cap,
                        (140 * W, 600),
                        (140 * W, 640),
                        (0, 640),
                        (0, 600),
                    ]
                )
            ),
            pc(R(0, 600, 640, 700)),
        ]

    G["2"] = glyph_two
    def glyph_three() -> list[Piece]:
        top_center = S / 2
        middle_center = 308
        bottom_center = 700 - S / 2
        return [
            pc(R(80, 0, 320, SH)),
            pc(
                connected_half_bowl(
                    320,
                    top_center,
                    middle_center,
                    180,
                    76,
                    -90,
                    90,
                    90,
                    -90,
                )
            ),
            pc(R(190, middle_center - S / 2, 320, middle_center + S / 2)),
            pc(
                connected_half_bowl(
                    320,
                    middle_center,
                    bottom_center,
                    222,
                    118,
                    -90,
                    90,
                    90,
                    -90,
                )
            ),
            pc(R(70, 700 - S, 320, 700)),
        ]

    G["3"] = glyph_three
    G["4"] = lambda: [
        pc(R(430, 0, 534, 700)),
        pc(R(0, 480, 620, 580)),
        pc(vertically_clipped_band((482, 0), (67, 486), 0, 520)),
    ]
    def glyph_five() -> list[Piece]:
        middle_center = 336
        bottom_center = 700 - S / 2
        return [
            pc(R(90, 0, 650, SH)),
            pc(R(90, 0, 194, middle_center + S / 2)),
            pc(R(90, middle_center - S / 2, 470, middle_center + S / 2)),
            pc(
                connected_half_bowl(
                    470,
                    middle_center,
                    bottom_center,
                    208,
                    104,
                    -90,
                    90,
                    90,
                    -90,
                )
            ),
            pc(R(96, 700 - S, 470, 700)),
        ]

    G["5"] = glyph_five
    G["6"] = lambda: [
        ring_p(322, 462, 250, 146),
        pc(R(72, 290, 176, 462)),
        pc(RS(362, 290, 290, 186, 180, 310, 310, 180, 1, 1)),
    ]
    G["7"] = lambda: [pc(R(0, 0, 620, SH)), pc(Q([(478, 90), (620, 90), (292, 700), (150, 700)]))]
    G["8"] = lambda: [ring_p(310, 168, 180, 76), ring_p(310, 512, 200, 96)]
    G["9"] = lambda: rotate_180(G["6"](), 322, 356)

    # Lowercase.
    G["a"] = lambda: [ring_p(262, 450, 262, 158), pc(R(420, 195, 524, 700))]
    G["b"] = lambda: [pc(vstem(52, 0, 700)), ring_p(262, 450, 262, 158)]
    G["c"] = lambda: [pc(RS(262, 450, 262, 158, -35, -325, -333, -27, 1, 1))]
    G["d"] = lambda: [ring_p(262, 450, 262, 158), pc(R(420, 0, 524, 700))]
    G["e"] = lambda: [pc(RS(262, 450, 262, 158, 38, 365, 365, 38, 1, 1)), pc(R(8, 400, 516, 500))]
    G["f"] = lambda: [
        pc(RS(354, 150, 150, 46, 180, 270, 270, 180, 1, 1)),
        pc(R(200, 144, 304, 700)),
        pc(R(30, 200, 470, 300)),
    ]
    G["g"] = lambda: [
        ring_p(262, 450, 262, 158),
        pc(R(420, 195, 524, 660)),
        pc(RS(284, 660, 240, 136, 0, 150, 150, 0, 1, 1)),
    ]
    G["h"] = lambda: [
        pc(vstem(52, 0, 700)),
        pc(RS(262, 462, 262, 158, 180, 360, 360, 180)),
        pc(R(420, 462, 524, 700)),
    ]
    G["i"] = lambda: [pc(R(0, 200, 104, 700)), disc(52, 75, 55)]
    G["ı"] = lambda: [pc(R(0, 200, 104, 700))]
    G["j"] = lambda: [
        pc(R(150, 200, 254, 760)),
        pc(RS(101, 747, 153, 49, 0, 150, 150, 0, 1, 1)),
        disc(202, 75, 55),
    ]
    G["k"] = lambda: [pc(R(0, 0, 104, 700)), bar(60, 485, 440, 205, S), leg(235, 345, 470, 700, S)]
    G["l"] = lambda: [pc(R(0, 0, 104, 700))]
    G["m"] = lambda: [
        pc(vstem(52, 200, 700)),
        pc(RS(233, 433, 233, 129, 180, 360, 360, 180)),
        pc(R(362, 433, 466, 700)),
        pc(RS(595, 433, 233, 129, 180, 360, 360, 180)),
        pc(R(724, 433, 828, 700)),
    ]
    G["n"] = lambda: [
        pc(vstem(52, 200, 700)),
        pc(RS(262, 462, 262, 158, 180, 360, 360, 180)),
        pc(R(420, 462, 524, 700)),
    ]
    G["o"] = lambda: [ring_p(262, 450, 262, 158)]
    G["p"] = lambda: [pc(vstem(52, 200, 900)), ring_p(262, 450, 262, 158)]
    G["q"] = lambda: [ring_p(262, 450, 262, 158), pc(R(420, 200, 524, 900))]
    G["r"] = lambda: [pc(R(0, 200, 104, 700)), pc(RS(240, 440, 240, 136, 180, 310, 310, 180, 1, 1))]
    def glyph_s_lower() -> list[Piece]:
        top_center = 256
        middle_center = 448
        bottom_center = 660
        return [
            pc(R(148, top_center - S / 2, 500, top_center + S / 2)),
            pc(
                connected_half_bowl(
                    148,
                    top_center,
                    middle_center,
                    148,
                    44,
                    90,
                    270,
                    270,
                    90,
                )
            ),
            pc(R(148, middle_center - S / 2, 352, middle_center + S / 2)),
            pc(
                connected_half_bowl(
                    352,
                    middle_center,
                    bottom_center,
                    158,
                    54,
                    -90,
                    90,
                    90,
                    -90,
                )
            ),
            pc(R(10, bottom_center - S / 2, 352, bottom_center + S / 2)),
        ]

    G["s"] = glyph_s_lower
    G["t"] = lambda: [
        pc(R(130, 80, 234, 560)),
        pc(R(0, 200, 420, 300)),
        pc(RS(270, 560, 140, 36, 180, 0, 0, 180, 1, 1)),
    ]
    G["u"] = lambda: [
        pc(vstem(52, 200, 440)),
        pc(RS(262, 438, 262, 158, 180, 0, 0, 180)),
        pc(R(420, 200, 524, 700)),
    ]
    G["v"] = lambda: [
        pc(Q([(0, 200), (104, 200), (312, 700), (208, 700)])),
        pc(Q([(416, 200), (520, 200), (312, 700), (208, 700)])),
    ]
    G["w"] = lambda: [
        pc(Q([(0, 200), (104, 200), (244, 700), (140, 700)])),
        pc(Q([(244, 700), (140, 700), (348, 240), (452, 240)])),
        pc(Q([(348, 240), (452, 240), (660, 700), (556, 700)])),
        pc(Q([(556, 700), (660, 700), (800, 200), (696, 200)])),
    ]
    G["x"] = lambda: [
        pc(Q([(0, 200), (104, 200), (500, 700), (396, 700)])),
        pc(Q([(396, 200), (500, 200), (104, 700), (0, 700)])),
    ]
    G["y"] = lambda: [
        pc(Q([(416, 200), (520, 200), (164, 900), (60, 900)])),
        pc(Q([(0, 200), (104, 200), (290, 655), (186, 655)])),
    ]
    G["z"] = lambda: [
        pc(R(20, 200, 520, 296)),
        pc(R(20, 604, 520, 700)),
        pc(
            diagonal_strip_hex(
                (486.2, 263),
                (53.8, 637),
                94.1409813428312,
                (20, 520, 230, 670),
                [
                    (452.4, 230),
                    (520, 230),
                    (520, 296),
                    (87.6, 670),
                    (20, 670),
                    (20, 604),
                ],
            )
        ),
    ]

    # ASCII punctuation.
    G["!"] = lambda: [pc(R(0, 0, 104, 470)), disc(52, 637, 63)]
    G['"'] = lambda: [pc(R(0, 0, 90, 210)), pc(R(170, 0, 260, 210))]
    G["#"] = lambda: [pc(R(150, 60, 240, 640)), pc(R(380, 60, 470, 640)), pc(R(0, 200, 620, 280)), pc(R(0, 420, 620, 500))]
    G["$"] = lambda: G["S"]() + [pc(R(310, -70, 386, 770))]
    G["%"] = lambda: [ring_p(150, 150, 150, 60), ring_p(490, 550, 150, 60), pc(Q([(520, 0), (624, 0), (120, 700), (16, 700)]))]
    G["&"] = lambda: [
        ring_p(250, 470, 230, 126),
        ring_p(230, 170, 170, 66),
        bar(310, 230, 620, 690, S),
        pc(Q([(364, 542), (437, 587), (724, 360), (656, 280)])),
    ]
    G["'"] = lambda: [pc(R(0, 0, 90, 210))]
    G["("] = lambda: [pc(RS(560, 350, 560, 456, 128, 232, 232, 128, 1, 1))]
    G[")"] = lambda: mirror_x(G["("](), 230)
    G["*"] = lambda: [bar(200, 40, 200, 320, 84), bar(79, 110, 321, 250, 84), bar(79, 250, 321, 110, 84)]
    G["+"] = lambda: [pc(R(0, 310, 440, 410)), pc(R(170, 140, 270, 580))]
    G[","] = lambda: [disc(63, 637, 63), pc(Q([(20, 650), (106, 650), (52, 815), (-16, 815)]))]
    G["-"] = lambda: [pc(R(0, 310, 400, 410))]
    G["\u00ad"] = lambda: [pc(R(0, 310, 400, 410))]
    G["."] = lambda: [disc(63, 637, 63)]
    G["/"] = lambda: [pc(Q([(356, 0), (460, 0), (104, 700), (0, 700)]))]
    G[":"] = lambda: [disc(63, 315, 63), disc(63, 637, 63)]
    G[";"] = lambda: [disc(63, 315, 63), disc(63, 637, 63), pc(Q([(20, 650), (106, 650), (52, 815), (-16, 815)]))]
    G["<"] = lambda: [chev(50, 360, (430, 155), (430, 565), 96)]
    G["="] = lambda: [pc(R(0, 240, 440, 330)), pc(R(0, 430, 440, 520))]
    G[">"] = lambda: mirror_x(G["<"](), 480)
    G["?"] = lambda: [pc(RS(300, 210, 210, 106, 215, 450, 450, 215, 1, 1)), pc(R(300, 316, 404, 490)), disc(352, 637, 63)]
    G["@"] = lambda: [
        pc(RS(360, 390, 350, 290, 20, 330, 330, 20, 1, 1)),
        ring_p(350, 390, 150, 70),
        pc(R(424, 254, 500, 526)),
        pc(R(424, 450, 604, 526)),
    ]
    G["["] = lambda: [pc(R(0, -40, 104, 780)), pc(R(0, -40, 300, 40)), pc(R(0, 700, 300, 780))]
    G["\\"] = lambda: [pc(Q([(0, 0), (104, 0), (460, 700), (356, 700)]))]
    G["]"] = lambda: mirror_x(G["["](), 300)
    G["^"] = lambda: [chev(230, 10, (60, 250), (400, 250), 92)]
    G["_"] = lambda: [pc(R(0, 730, 560, 820))]
    G["`"] = lambda: [bar(50, 25, 190, 170, 88)]
    G["{"] = lambda: [
        pc(R(170, -40, 300, 45)),
        pc(R(170, -40, 258, 370)),
        chev(70, 370, (214, 330), (214, 410), 88),
        pc(R(170, 370, 258, 780)),
        pc(R(170, 695, 300, 780)),
    ]
    G["|"] = lambda: [pc(R(0, -40, 104, 780))]
    G["}"] = lambda: mirror_x(G["{"](), 300)
    G["~"] = lambda: [wave(220, 360, 220, 32, 45)]

    # Latin-1 symbols.
    G["¡"] = lambda: rotate_180(G["!"](), 52, 350)
    G["¢"] = lambda: G["c"]() + [pc(R(224, 110, 300, 790))]
    G["£"] = lambda: [
        pc(RS(350, 190, 190, 86, 180, 330, 330, 180, 1, 1)),
        pc(R(160, 180, 264, 610)),
        pc(R(30, 330, 420, 430)),
        pc(R(0, 600, 570, 700)),
    ]
    G["¤"] = lambda: [
        ring_p(230, 360, 150, 70),
        bar(335, 255, 415, 175, 80),
        bar(125, 255, 45, 175, 80),
        bar(335, 465, 415, 545, 80),
        bar(125, 465, 45, 545, 80),
    ]
    G["¥"] = lambda: G["Y"]() + [pc(R(70, 350, 570, 420)), pc(R(70, 490, 570, 560))]
    G["¦"] = lambda: [pc(R(0, -40, 104, 300)), pc(R(0, 420, 104, 780))]
    G["§"] = lambda: translate(scale(G["S"](), 0.85) + [ring_p(297, 297, 140, 72)], 20, 55)
    G["¨"] = lambda: [disc(10, 90, 55), disc(250, 90, 55)]
    G["©"] = lambda: [ring_p(350, 350, 350, 290), pc(RS(350, 350, 190, 118, -38, -322, -330, -30, 1, 1))]
    G["ª"] = lambda: translate(scale(G["a"](), 0.55), 0, -100)
    G["«"] = lambda: [chev(50, 400, (190, 255), (190, 545), 86), chev(260, 400, (400, 255), (400, 545), 86)]
    G["¬"] = lambda: [pc(R(0, 320, 460, 408)), pc(R(372, 408, 460, 570))]
    G["®"] = lambda: [
        ring_p(350, 350, 350, 290),
        pc(R(255, 220, 320, 480)),
        pc(R(255, 220, 390, 282)),
        pc(R(255, 340, 390, 402)),
        pc(RS(390, 311, 91, 29, -90, 90, 90, -90)),
        pc(Q([(350, 380), (420, 380), (470, 480), (400, 480)])),
    ]
    G["¯"] = lambda: [pc(R(0, 40, 360, 128))]
    G["°"] = lambda: [ring_p(115, 115, 115, 50)]
    G["±"] = lambda: [pc(R(176, 110, 264, 510)), pc(R(0, 266, 440, 354)), pc(R(0, 610, 440, 698))]
    G["²"] = lambda: scale(G["2"](), 0.5)
    G["³"] = lambda: scale(G["3"](), 0.5)
    G["´"] = lambda: [bar(190, 25, 50, 170, 88)]
    G["µ"] = lambda: [
        pc(vstem(52, 200, 900)),
        pc(RS(262, 438, 262, 158, 180, 0, 0, 180)),
        pc(R(420, 200, 524, 700)),
    ]
    G["¶"] = lambda: [
        pc(Contour(arc_pts(330 * W, 180, 180 * W, 180, 90, 270))),
        pc(R(330, 0, 434, 700)),
        pc(R(540, 0, 644, 700)),
        pc(R(330, 0, 644, 90)),
    ]
    G["·"] = lambda: [disc(63, 360, 63)]
    G["¸"] = lambda: [pc(R(66, 690, 134, 772)), pc(R(-4, 772, 134, 836))]
    G["¹"] = lambda: scale(G["1"](), 0.5)
    G["º"] = lambda: translate(scale(G["o"](), 0.55), 0, -100)
    G["»"] = lambda: mirror_x(G["«"](), 450)

    def fraction_slash() -> Piece:
        return pc(Q([(400, 0), (470, 0), (120, 700), (50, 700)]))

    G["¼"] = lambda: scale(G["1"](), 0.44) + [fraction_slash()] + translate(scale(G["4"](), 0.44), 330, 392)
    G["½"] = lambda: scale(G["1"](), 0.44) + [fraction_slash()] + translate(scale(G["2"](), 0.44), 330, 392)
    G["¾"] = lambda: scale(G["3"](), 0.44) + [fraction_slash()] + translate(scale(G["4"](), 0.44), 350, 392)
    G["¿"] = lambda: rotate_180(G["?"](), 319, 350)
    G["×"] = lambda: [bar(139, 219, 421, 501, 96), bar(421, 219, 139, 501, 96)]
    G["÷"] = lambda: [pc(R(0, 316, 440, 404)), disc(220, 150, 63), disc(220, 570, 63)]

    # Special letters.
    G["Æ"] = lambda: [
        pc(Q([(340, 0), (444, 0), (104, 700), (0, 700)])),
        pc(R(340, 0, 444, 700)),
        pc(R(340, 0, 900, SH)),
        pc(R(340, 310, 760, 410)),
        pc(R(340, 600, 910, 700)),
        pc(R(180, 430, 400, 530)),
    ]
    G["æ"] = lambda: [ring_p(250, 450, 250, 146), pc(RS(690, 450, 250, 146, 38, 365, 365, 38, 1, 1)), pc(R(452, 400, 928, 500))]
    G["Ø"] = lambda: G["O"]() + [bar(40, 770, 690, -70, 76)]
    G["ø"] = lambda: G["o"]() + [bar(30, 760, 494, 140, 66)]
    G["Ð"] = lambda: G["D"]() + [pc(R(-70, 304, 250, 400))]
    G["ð"] = lambda: [ring_p(240, 490, 222, 118), bar(300, 300, 480, 40, 96), bar(310, 110, 480, 230, 66)]
    G["Þ"] = lambda: [
        pc(R(0, 0, 104, 700)),
        pc(R(0, 150, 400, 254)),
        pc(R(0, 456, 400, 560)),
        pc(RS(400, 355, 205, 101, -90, 90, 90, -90)),
    ]
    G["þ"] = lambda: [pc(vstem(52, 0, 900)), ring_p(262, 450, 262, 158)]
    G["ß"] = lambda: [
        pc(R(0, 0, 104, 700)),
        pc(RS(175, 175, 175, 71, 180, 360, 360, 180)),
        pc(R(246, 160, 350, 400)),
        pc(RS(298, 498, 202, 98, -90, 90, 90, -90, 1, 1)),
    ]

    direct_count = len(G)

    def cap_accent(kind: str, cx: float) -> list[Piece]:
        if kind == "grave":
            return [bar(cx - 110, -255, cx + 45, -90, 94)]
        if kind == "acute":
            return [bar(cx + 110, -255, cx - 45, -90, 94)]
        if kind == "circ":
            return [chev(cx, -260, (cx - 155, -85), (cx + 155, -85), 90)]
        if kind == "dier":
            return [disc(cx - 136, -115, 63), disc(cx + 136, -115, 63)]
        if kind == "ring":
            return [ring_p(cx, -150, 96, 42)]
        if kind == "tilde":
            return [wave(cx, -160, 190, 26, 44)]
        if kind == "ced":
            return [pc(R(cx - 34, 690, cx + 34, 772)), pc(R(cx - 104, 772, cx + 34, 836))]
        return []

    def lc_accent(kind: str, cx: float) -> list[Piece]:
        if kind == "grave":
            return [bar(cx - 100, 25, cx + 40, 170, 88)]
        if kind == "acute":
            return [bar(cx + 100, 25, cx - 40, 170, 88)]
        if kind == "circ":
            # Preserve the canonical ±140 default while keeping the terminal
            # caps clear of the extrusion direction away from wdth=100.
            half_span = 140 / max(1.0, W)
            return [
                chev(
                    cx,
                    20,
                    (cx - half_span, 170),
                    (cx + half_span, 170),
                    84,
                )
            ]
        if kind == "dier":
            return [disc(cx - 120, 85, 55), disc(cx + 120, 85, 55)]
        if kind == "ring":
            return [ring_p(cx, 70, 88, 36)]
        if kind == "tilde":
            return [wave(cx, 95, 170, 24, 40)]
        if kind == "ced":
            return cap_accent("ced", cx)
        return []

    def x_center(pieces: Sequence[Piece]) -> float:
        left, right = 1e9, -1e9
        for piece in pieces:
            for x, _y, _flag in piece.outer.pts:
                left = min(left, x)
                right = max(right, x)
        return (left + right) / (2 * W)

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


@dataclass(frozen=True, slots=True)
class SamplePoint:
    """A subdivided point with interpolation-stable arc and cap metadata."""

    x: float
    y: float
    arc: bool = False
    force: bool = False

    @property
    def flag(self) -> int:
        return 2 if self.force else (1 if self.arc else 0)

    def translated(self, dx: float, dy: float) -> "SamplePoint":
        return SamplePoint(self.x + dx, self.y + dy, self.arc, self.force)


@dataclass(frozen=True, slots=True)
class EdgeTopology:
    """Frozen sample count and flags for one raw source edge."""

    count: int
    arc: bool
    force: bool


@dataclass(frozen=True, slots=True)
class ContourTopology:
    """Frozen raw-edge recipe and default-master winding normalization."""

    edges: tuple[EdgeTopology, ...]
    reverse: bool


@dataclass(frozen=True, slots=True)
class GlyphTopology:
    """Per-piece topology frozen once at the default master."""

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
    """A glyph's default-topology source outline in y-down coordinates."""

    name: str
    pieces: tuple[BuiltPiece, ...]
    params: GeneratorParams
    seed: float
    topology: GlyphTopology

    @property
    def contours(self) -> tuple[BuiltContour, ...]:
        return tuple(contour for piece in self.pieces for contour in piece.contours)


def _xy(point: SamplePoint | Sequence[float]) -> tuple[float, float]:
    if isinstance(point, SamplePoint):
        return point.x, point.y
    return float(point[0]), float(point[1])


def _edge_topology(contour: Contour, max_len: float) -> tuple[EdgeTopology, ...]:
    points = contour.pts
    edges: list[EdgeTopology] = []
    for index, a in enumerate(points):
        b = points[(index + 1) % len(points)]
        length = _js_hypot(b[0] - a[0], b[1] - a[1])
        count = max(1, ceil(length / max_len))
        edges.append(
            EdgeTopology(
                count=count,
                arc=a[2] == 1 and b[2] == 1 and length < 40,
                force=a[2] == 2,
            )
        )
    return tuple(edges)


def subdivide(
    contour: Contour,
    max_len: float = SUBDIVISION_MAX_LENGTH,
    topology: ContourTopology | Sequence[EdgeTopology] | None = None,
) -> list[SamplePoint]:
    """Port ``subdivide``; optionally replay default-master edge counts/flags."""

    edges = topology.edges if isinstance(topology, ContourTopology) else topology
    if edges is None:
        edges = _edge_topology(contour, max_len)
    if len(edges) != len(contour.pts):
        raise ValueError("raw contour edge count differs from frozen topology")
    out: list[SamplePoint] = []
    for index, a in enumerate(contour.pts):
        b = contour.pts[(index + 1) % len(contour.pts)]
        edge = edges[index]
        dx, dy = b[0] - a[0], b[1] - a[1]
        for k in range(edge.count):
            out.append(
                SamplePoint(
                    a[0] + dx * k / edge.count,
                    a[1] + dy * k / edge.count,
                    edge.arc,
                    edge.force,
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
    """Port ``jitterPts`` while retaining both load-bearing point flags."""

    if not amp:
        return [SamplePoint(p.x, p.y, p.arc, p.force) for p in points]
    s1, s2 = seed * 1.7 + 0.4, seed * 2.3 + 1.9
    s3, s4 = seed * 3.1 + 0.7, seed * 1.3 + 2.6
    return [
        SamplePoint(
            p.x + amp * 0.5 * (sin(p.x * 0.011 + s1) + sin(p.y * 0.017 + s2)),
            p.y + amp * 0.5 * (sin(p.x * 0.015 + s3) + sin(p.y * 0.009 + s4)),
            p.arc,
            p.force,
        )
        for p in points
    ]


def glyph_seed(name: str) -> float:
    """Return the JS ``charCodeAt`` seed, including UTF-16 surrogate semantics."""

    encoded = name.encode("utf-16-le", "surrogatepass")
    return sum(int.from_bytes(encoded[i : i + 2], "little") * 7.13 for i in range(0, len(encoded), 2))


def _raw_piece_contours(piece: Piece) -> tuple[Contour, ...]:
    return (piece.outer, *piece.holes)


def freeze_topology(
    params: ParamsLike | None = None,
    names: Iterable[str] | None = None,
    max_len: float = SUBDIVISION_MAX_LENGTH,
) -> dict[str, GlyphTopology]:
    """Freeze default-master edge sample counts, flags, winding, and starts."""

    p = coerce_params(params)
    builders = glyph_defs(p)
    selected = tuple(builders) if names is None else tuple(names)
    result: dict[str, GlyphTopology] = {}
    for name in selected:
        if name not in builders:
            raise KeyError(name)
        piece_topologies: list[tuple[ContourTopology, ...]] = []
        for piece in builders[name]():
            contours: list[ContourTopology] = []
            for contour_index, contour in enumerate(_raw_piece_contours(piece)):
                edges = _edge_topology(contour, max_len)
                sampled = subdivide(contour, max_len, edges)
                reverse_winding = (signed_area(sampled) > 0) != (contour_index == 0)
                contours.append(ContourTopology(edges, reverse_winding))
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
    # Counts are always frozen at D, even when the requested outline is another
    # master.  This is the core interpolation invariant.
    return freeze_topology(GeneratorParams(), (name,))[name]


def build_contours(
    name: str,
    params: ParamsLike | None = None,
    *,
    seed: float | None = None,
    topology: GlyphTopology | Mapping[str, GlyphTopology] | None = None,
) -> GlyphOutline:
    """Build one glyph by replaying its default-master subdivision topology."""

    p = coerce_params(params)
    frozen = _resolve_topology(name, topology)
    builders = glyph_defs(p)
    if name not in builders:
        raise KeyError(name)
    pieces = builders[name]()
    if len(pieces) != len(frozen.pieces):
        raise ValueError(f"{name!r}: piece count differs from default topology")
    actual_seed = glyph_seed(name) if seed is None else seed
    built_pieces: list[BuiltPiece] = []
    for piece_index, piece in enumerate(pieces):
        raw_contours = _raw_piece_contours(piece)
        contour_topologies = frozen.pieces[piece_index]
        if len(raw_contours) != len(contour_topologies):
            raise ValueError(f"{name!r}: contour count differs from default topology")
        built_contours: list[BuiltContour] = []
        for contour_index, raw in enumerate(raw_contours):
            contour_topology = contour_topologies[contour_index]
            ideal = subdivide(raw, topology=contour_topology)
            if contour_topology.reverse:
                ideal.reverse()
            jittered = jitter_points(ideal, p.jit, actual_seed)
            built_contours.append(
                BuiltContour(tuple(jittered), tuple(ideal), contour_index > 0)
            )
        built_pieces.append(BuiltPiece(tuple(built_contours)))
    return GlyphOutline(name, tuple(built_pieces), p, actual_seed, frozen)


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
    """One frozen visible edge run; ``end`` may wrap beyond contour length."""

    piece_index: int
    contour_index: int
    start: int
    end: int
    color: WallColor
    arc: bool
    default_length: float


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


def _in_outline(x: float, y: float, outline: GlyphOutline) -> bool:
    return any(
        point_in(x, y, piece.outer.ideal)
        and not any(point_in(x, y, hole.ideal) for hole in piece.holes)
        for piece in outline.pieces
    )


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
) -> FrozenRecipe:
    """Freeze edge visibility/labels at D, separately for regular and hand."""

    p = coerce_params(params)
    p = replace(p, jit=3.4 if hand else 0.0, hatch_n=HATCH_N)
    frozen = _resolve_topology(name, topology)
    outline = build_contours(name, p, seed=seed, topology=frozen)
    vx, vy = p.v
    frozen_runs: list[WallRun] = []
    hatch_groups: list[HatchGroup] = []

    for piece_index, piece in enumerate(outline.pieces):
        for contour_index, contour in enumerate(piece.contours):
            ideal, drawn = contour.ideal, contour.points
            count = len(ideal)
            edge_data: list[tuple[bool, WallColor | None, bool]] = []
            for index, point in enumerate(ideal):
                other = ideal[(index + 1) % count]
                dx, dy = other.x - point.x, other.y - point.y
                length = _js_hypot(dx, dy) or 1.0
                nx, ny = dy / length, -dx / length
                visible = (
                    nx * vx + ny * vy > 0.02 or point.force
                ) and not _in_outline(
                    (point.x + other.x) / 2 + nx * 6,
                    (point.y + other.y) / 2 + ny * 6,
                    outline,
                )
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
                edge_data.append((visible, color, point.arc and other.arc))

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
                frozen_runs.append(
                    WallRun(
                        piece_index,
                        contour_index,
                        run.start,
                        run.end,
                        run.color,
                        run.arc,
                        run.length,
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
    """One closed layer shape and optional holes, ready for UFO conversion."""

    outer: tuple[SamplePoint, ...]
    holes: tuple[tuple[SamplePoint, ...], ...] = ()

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


def _wall_piece(
    points: Sequence[SamplePoint], run: WallRun, vector: tuple[float, float]
) -> LayerPiece:
    run_points = _run_points(points, run.start, run.end)
    back = [point.translated(*vector) for point in reversed(run_points)]
    return LayerPiece(tuple(run_points + back))


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
        wall = _wall_piece(points, run, vector)
        (bronze if run.color == "bronze" else dark).append(wall)

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
