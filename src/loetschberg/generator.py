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

    # ``w`` is applied to the canonical grid geometry, never to stale specimen
    # outlines.  Coordinates that place skeleton features scale in x.  Narrow
    # vertical rectangles retain their physical x-width, and rings scale their
    # outer x-radius while subtracting the unscaled source stroke for the inner
    # x-radius.  Thus H's stems and O's horizontal stroke stay invariant.
    def R(x0: float, y0: float, x1: float, y1: float) -> Contour:
        width, height = abs(x1 - x0), abs(y1 - y0)
        if width <= max(150.0, 1.5 * S) and height > 1.5 * width:
            target_width = width if abs(width - S) < 1e-9 else width * weight_ratio
            if x0 == 0:
                xx0, xx1 = 0.0, target_width
            else:
                center = (x0 + x1) * W / 2
                xx0, xx1 = center - target_width / 2, center + target_width / 2
            return rect(xx0, y0, xx1, y1)
        if height <= max(150.0, 1.5 * SH) and width > 1.5 * height:
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
        return quad([(q[0] * W, q[1]) for q in points])

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
        stroke = (ro - ri) * weight_ratio
        outer_rx = ro * W
        inner_rx = max(1.0, outer_rx - stroke)
        inner_ry = max(1.0, ro - stroke)
        outer = arc_pts(cx * W, cy, outer_rx, ro, oa0, oa1)
        inner = arc_pts(cx * W, cy, inner_rx, inner_ry, ia0, ia1)
        if caps:
            outer[-1] = (outer[-1][0], outer[-1][1], 2)
            inner[-1] = (inner[-1][0], inner[-1][1], 2)
        return Contour(outer + inner)

    def pc(outer: Contour, holes: Sequence[Contour] | None = None) -> Piece:
        return _piece(outer, holes)

    def disc(cx: float, cy: float, radius: float) -> Piece:
        return pc(ellipse(cx * W, cy, radius, radius))

    def ring_p(cx: float, cy: float, ro: float, ri: float) -> Piece:
        stroke = (ro - ri) * weight_ratio
        outer_rx = ro * W
        inner_rx = max(1.0, outer_rx - stroke)
        inner_ry = max(1.0, ro - stroke)
        return pc(
            ellipse(cx * W, cy, outer_rx, ro),
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
        for i in range(41):
            t = i / 40
            x = (cx - half_len + 2 * half_len * t) * W
            y = cy - amp * sin(2 * pi * t)
            d = -amp * cos(2 * pi * t) * pi / (half_len * W)
            length = _js_hypot(1, d)
            nx, ny = d / length, -1 / length
            weighted_half_w = half_w * weight_ratio
            top.append((x + nx * weighted_half_w, y + ny * weighted_half_w, 1))
            bottom.append((x - nx * weighted_half_w, y - ny * weighted_half_w, 1))
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
        n1, n2 = (-u1[1], u1[0]), (-u2[1], u2[0])
        if n1[0] * u2[0] + n1[1] * u2[1] > 0:
            n1 = (-n1[0], -n1[1])
        if n2[0] * u1[0] + n2[1] * u1[1] > 0:
            n2 = (-n2[0], -n2[1])
        nn1 = (n1[0] * width / 2, n1[1] * width / 2)
        nn2 = (n2[0] * width / 2, n2[1] * width / 2)

        def intersect(
            point: Sequence[float],
            direction: Sequence[float],
            other: Sequence[float],
            other_direction: Sequence[float],
        ) -> tuple[float, float]:
            den = direction[0] * other_direction[1] - direction[1] * other_direction[0]
            if abs(den) < 1e-9:
                return (point[0] + other[0]) / 2, (point[1] + other[1]) / 2
            t = (
                (other[0] - point[0]) * other_direction[1]
                - (other[1] - point[1]) * other_direction[0]
            ) / den
            return point[0] + direction[0] * t, point[1] + direction[1] * t

        outer_apex = intersect(
            (ax + nn1[0], ay + nn1[1]),
            u1,
            (ax + nn2[0], ay + nn2[1]),
            u2,
        )
        inner_apex = intersect(
            (ax - nn1[0], ay - nn1[1]),
            u1,
            (ax - nn2[0], ay - nn2[1]),
            u2,
        )
        return pc(
            Contour(
                [
                    (b1[0] + nn1[0], b1[1] + nn1[1], 0),
                    (outer_apex[0], outer_apex[1], 0),
                    (b2[0] + nn2[0], b2[1] + nn2[1], 0),
                    (b2[0] - nn2[0], b2[1] - nn2[1], 0),
                    (inner_apex[0], inner_apex[1], 0),
                    (b1[0] - nn1[0], b1[1] - nn1[1], 0),
                ]
            )
        )

    G: dict[str, Builder] = {}

    # Uppercase -- assignment order mirrors the canonical source.
    G["O"] = lambda: [ring_p(362, 350, 362, 258)]
    G["Ö"] = lambda: G["O"]() + [disc(225.5, -115, 63), disc(498.5, -115, 63)]
    G["C"] = lambda: [pc(RS(362, 350, 362, 258, -38, -322, -330, -30, 1, 1))]
    G["G"] = lambda: [
        pc(RS(362, 350, 362, 258, -38, -322, -345, -30, 1, 1)),
        pc(R(608, 325, 724, 700)),
    ]
    G["H"] = lambda: [pc(R(0, 0, S, 700)), pc(R(526, 0, 630, 700)), pc(R(S, 321, 526, 421))]
    G["E"] = lambda: [
        pc(R(0, 0, S, 700)),
        pc(R(0, 0, 590, SH)),
        pc(R(0, 310, 425, 410)),
        pc(R(0, 600, 596, 700)),
    ]
    G["L"] = lambda: [pc(R(0, 0, S, 700)), pc(R(0, 600, 615, 700))]
    G["T"] = lambda: [pc(R(0, 0, 700, S)), pc(R(298, 0, 402, 700))]
    G["I"] = lambda: [pc(R(0, 0, S, 700))]
    G["S"] = lambda: [
        pc(R(198.5, 0, 690, S)),
        pc(RS(198.5, 198.5, 198.5, 94.5, 90, 270, 270, 90)),
        pc(R(198.5, 293, 501.5, 397)),
        pc(RS(501.5, 496.5, 203.5, 99.5, -90, 90, 90, -90)),
        pc(R(10, 596, 501.5, 700)),
    ]
    G["B"] = lambda: [
        pc(R(0, 0, S, 700)),
        pc(R(0, 0, 404, S)),
        pc(R(0, 298, 419, 402)),
        pc(R(0, 596, 419, 700)),
        pc(RS(404, 201, 201, 97, -90, 90, 90, -90)),
        pc(RS(419, 499, 201, 97, -90, 90, 90, -90)),
    ]
    G["P"] = lambda: [
        pc(R(0, 0, S, 700)),
        pc(R(0, 0, 393.5, S)),
        pc(R(0, 319, 393.5, 423)),
        pc(RS(393.5, 211.5, 211.5, 107.5, -90, 90, 90, -90)),
    ]

    def glyph_r() -> list[Piece]:
        leg_top, u, px = (480, 380), (0.417, 0.909), (0.909, -0.417)
        tl = (leg_top[0] - px[0] * 52, leg_top[1] - px[1] * 52)
        tr = (leg_top[0] + px[0] * 52, leg_top[1] + px[1] * 52)
        br = (tr[0] + u[0] * ((700 - tr[1]) / u[1]), 700)
        bl = (tl[0] + u[0] * ((700 - tl[1]) / u[1]), 700)
        return G["P"]() + [pc(Q([tl, tr, br, bl]))]

    G["R"] = glyph_r

    def glyph_m_cap() -> list[Piece]:
        width, wh, mid, ya, jj, fw = 770, 112.6, 385, 567, S, 96
        dxo, dyo = mid - S, ya - jj
        xt = S + wh - dxo * jj / dyo
        y_cr = jj + dyo * (mid - S - wh) / dxo
        yf = ya - fw / 2 * dyo / dxo
        return [
            pc(R(0, 0, S, 700)),
            pc(R(width - S, 0, width, 700)),
            pc(
                Q(
                    [
                        (S, 0),
                        (xt, 0),
                        (mid, y_cr),
                        (width - xt, 0),
                        (width - S, 0),
                        (width - S, jj),
                        (mid + fw / 2, yf),
                        (mid - fw / 2, yf),
                        (S, jj),
                    ]
                )
            ),
        ]

    G["M"] = glyph_m_cap
    G["N"] = lambda: [
        pc(R(0, 0, S, 700)),
        pc(R(521, 0, 625, 700)),
        pc(Q([(0, 0), (129.7, 0), (625, 700), (495.3, 700)])),
    ]
    G["A"] = lambda: [
        pc(Q([(302, 0), (406, 0), (104, 700), (0, 700)])),
        pc(Q([(302, 0), (406, 0), (708, 700), (604, 700)])),
        pc(R(120, 440, 590, 540)),
    ]
    G["D"] = lambda: [
        pc(R(0, 0, S, 700)),
        pc(R(0, 0, 340, 104)),
        pc(R(0, 596, 340, 700)),
        pc(RS(340, 350, 350, 246, -90, 90, 90, -90)),
    ]
    G["F"] = lambda: [pc(R(0, 0, S, 700)), pc(R(0, 0, 590, SH)), pc(R(0, 310, 425, 410))]
    G["J"] = lambda: [
        pc(R(396, 0, 500, 550)),
        pc(RS(347, 547, 153, 49, 0, 180, 180, 0, 1, 1)),
    ]
    G["K"] = lambda: [pc(R(0, 0, S, 700)), bar(50, 478, 590, 48, S), leg(240, 335, 620, 700, S)]
    G["Q"] = lambda: G["O"]() + [bar(440, 460, 760, 790, S)]
    G["U"] = lambda: [
        pc(R(0, 0, S, 400)),
        pc(R(526, 0, 630, 400)),
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
        pc(Q([(543.4, 20), (620, 20), (620, 100), (76.6, 680), (0, 680), (0, 600)])),
    ]

    # Digits.
    G["0"] = lambda: [
        pc(
            ellipse(310 * W, 350, 310 * W, 362),
            [
                ellipse(
                    310 * W,
                    350,
                    max(1.0, 310 * W - S),
                    max(1.0, 362 - S),
                )
            ],
        )
    ]

    def glyph_one() -> list[Piece]:
        x0, u, pp = 150, (-0.743, 0.669), (0.669, 0.743)
        a = (x0, 0)
        b = (x0 + u[0] * 150, u[1] * 150)
        c = (b[0] + pp[0] * S, b[1] + pp[1] * S)
        d = (a[0] + pp[0] * S, a[1] + pp[1] * S)
        return [pc(R(x0, 0, x0 + S, 700)), pc(Q([a, b, c, d]))]

    G["1"] = glyph_one
    G["2"] = lambda: [
        pc(RS(322, 322, 322, 218, 180, 390, 390, 180, 1, 1)),
        pc(Q([(511, 431), (519.6, 414.1), (613.8, 458.1), (601, 483), (140, 600), (140, 640), (0, 640), (0, 600)])),
        pc(R(0, 600, 640, 700)),
    ]
    G["3"] = lambda: [
        pc(R(80, 0, 320, SH)),
        pc(RS(320, 180, 180, 76, -90, 90, 90, -90)),
        pc(R(190, 256, 320, 360)),
        pc(RS(320, 478, 222, 118, -90, 90, 90, -90)),
        pc(R(70, 596, 320, 700)),
    ]
    G["4"] = lambda: [
        pc(R(430, 0, 534, 700)),
        pc(R(0, 480, 620, 580)),
        pc(Q([(430, 0), (534, 0), (534, 60), (134, 480), (134, 520), (0, 520), (0, 452)])),
    ]
    G["5"] = lambda: [
        pc(R(90, 0, 650, SH)),
        pc(R(90, 0, 194, 388)),
        pc(R(90, 284, 470, 388)),
        pc(RS(470, 492, 208, 104, -90, 90, 90, -90)),
        pc(R(96, 596, 470, 700)),
    ]
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
    G["b"] = lambda: [pc(R(0, 0, S, 700)), ring_p(262, 450, 262, 158)]
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
        pc(R(0, 0, S, 700)),
        pc(RS(262, 462, 262, 158, 180, 360, 360, 180)),
        pc(R(420, 462, 524, 700)),
    ]
    G["i"] = lambda: [pc(R(0, 200, S, 700)), disc(52, 75, 55)]
    G["ı"] = lambda: [pc(R(0, 200, S, 700))]
    G["j"] = lambda: [
        pc(R(150, 200, 254, 760)),
        pc(RS(101, 747, 153, 49, 0, 150, 150, 0, 1, 1)),
        disc(202, 75, 55),
    ]
    G["k"] = lambda: [pc(R(0, 0, S, 700)), bar(60, 485, 440, 205, S), leg(235, 345, 470, 700, S)]
    G["l"] = lambda: [pc(R(0, 0, S, 700))]
    G["m"] = lambda: [
        pc(R(0, 200, S, 700)),
        pc(RS(233, 433, 233, 129, 180, 360, 360, 180)),
        pc(R(362, 433, 466, 700)),
        pc(RS(595, 433, 233, 129, 180, 360, 360, 180)),
        pc(R(724, 433, 828, 700)),
    ]
    G["n"] = lambda: [
        pc(R(0, 200, S, 700)),
        pc(RS(262, 462, 262, 158, 180, 360, 360, 180)),
        pc(R(420, 462, 524, 700)),
    ]
    G["o"] = lambda: [ring_p(262, 450, 262, 158)]
    G["p"] = lambda: [pc(R(0, 200, S, 900)), ring_p(262, 450, 262, 158)]
    G["q"] = lambda: [ring_p(262, 450, 262, 158), pc(R(420, 200, 524, 900))]
    G["r"] = lambda: [pc(R(0, 200, S, 700)), pc(RS(240, 440, 240, 136, 180, 310, 310, 180, 1, 1))]
    G["s"] = lambda: [
        pc(R(148, 204, 500, 308)),
        pc(RS(148, 352, 148, 44, 90, 270, 270, 90)),
        pc(R(148, 396, 352, 500)),
        pc(RS(352, 554, 158, 54, -90, 90, 90, -90)),
        pc(R(10, 608, 352, 712)),
    ]
    G["t"] = lambda: [
        pc(R(130, 80, 234, 560)),
        pc(R(0, 200, 420, 300)),
        pc(RS(270, 560, 140, 36, 180, 0, 0, 180, 1, 1)),
    ]
    G["u"] = lambda: [
        pc(R(0, 200, S, 440)),
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
        pc(Q([(452.4, 230), (520, 230), (520, 296), (87.6, 670), (20, 670), (20, 604)])),
    ]

    # ASCII punctuation.
    G["!"] = lambda: [pc(R(0, 0, S, 470)), disc(52, 637, 63)]
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
    G["["] = lambda: [pc(R(0, -40, S, 780)), pc(R(0, -40, 300, 40)), pc(R(0, 700, 300, 780))]
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
    G["|"] = lambda: [pc(R(0, -40, S, 780))]
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
    G["¦"] = lambda: [pc(R(0, -40, S, 300)), pc(R(0, 420, S, 780))]
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
        pc(R(0, 200, S, 900)),
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
        pc(R(0, 0, S, 700)),
        pc(R(0, 150, 400, 254)),
        pc(R(0, 456, 400, 560)),
        pc(RS(400, 355, 205, 101, -90, 90, 90, -90)),
    ]
    G["þ"] = lambda: [pc(R(0, 0, S, 900)), ring_p(262, 450, 262, 158)]
    G["ß"] = lambda: [
        pc(R(0, 0, S, 700)),
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
            return [chev(cx, 20, (cx - 140, 170), (cx + 140, 170), 84)]
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
    """Interpolation-compatible geometry for the five COLRv1 paint layers."""

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


def _point_on_segment(
    x: float, y: float, a: SamplePoint, b: SamplePoint, tolerance: float = 1e-7
) -> bool:
    cross = (x - a.x) * (b.y - a.y) - (y - a.y) * (b.x - a.x)
    if abs(cross) > tolerance * max(1.0, _js_hypot(b.x - a.x, b.y - a.y)):
        return False
    return (
        min(a.x, b.x) - tolerance <= x <= max(a.x, b.x) + tolerance
        and min(a.y, b.y) - tolerance <= y <= max(a.y, b.y) + tolerance
    )


def _inside_or_boundary(x: float, y: float, polygon: Sequence[SamplePoint]) -> bool:
    return point_in(x, y, polygon) or any(
        _point_on_segment(x, y, polygon[index - 1], polygon[index])
        for index in range(len(polygon))
    )


def _intersection_parameter(
    start: SamplePoint,
    end: SamplePoint,
    a: SamplePoint,
    b: SamplePoint,
) -> float | None:
    dx, dy = end.x - start.x, end.y - start.y
    ex, ey = b.x - a.x, b.y - a.y
    den = dx * ey - dy * ex
    if abs(den) < 1e-12:
        return None
    qx, qy = a.x - start.x, a.y - start.y
    t = (qx * ey - qy * ex) / den
    u = (qx * dy - qy * dx) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return min(1.0, max(0.0, t))
    return None


def _clip_segment(
    start: SamplePoint,
    end: SamplePoint,
    polygons: Sequence[Sequence[SamplePoint]],
) -> tuple[SamplePoint, SamplePoint]:
    """Clip to a polygon union and retain the interval crossing the midpoint."""

    parameters = [0.0, 1.0]
    for polygon in polygons:
        for index, point in enumerate(polygon):
            t = _intersection_parameter(start, end, polygon[index - 1], point)
            if t is not None:
                parameters.append(t)
    parameters = sorted(set(round(t, 12) for t in parameters))
    inside_intervals: list[tuple[float, float]] = []
    for lo, hi in zip(parameters, parameters[1:]):
        mid = (lo + hi) / 2
        x = start.x + (end.x - start.x) * mid
        y = start.y + (end.y - start.y) * mid
        if any(_inside_or_boundary(x, y, polygon) for polygon in polygons):
            inside_intervals.append((lo, hi))
    if not inside_intervals:
        # A hatch centreline often lies exactly on the shared boundary of two
        # wall polygons.  The requested 10%-90% segment is already face-safe.
        return start, end
    containing_mid = [interval for interval in inside_intervals if interval[0] <= 0.5 <= interval[1]]
    lo, hi = max(
        containing_mid or inside_intervals,
        key=lambda interval: interval[1] - interval[0],
    )
    return (
        SamplePoint(start.x + (end.x - start.x) * lo, start.y + (end.y - start.y) * lo),
        SamplePoint(start.x + (end.x - start.x) * hi, start.y + (end.y - start.y) * hi),
    )


def _hatch_quad(
    center: SamplePoint,
    vector: tuple[float, float],
    thickness: float,
    clip_polygons: Sequence[Sequence[SamplePoint]],
) -> LayerPiece:
    vx, vy = vector
    depth = _js_hypot(vx, vy) or 1.0
    ux, uy = vx / depth, vy / depth
    half_length = depth * 0.4
    start = SamplePoint(center.x - ux * half_length, center.y - uy * half_length)
    end = SamplePoint(center.x + ux * half_length, center.y + uy * half_length)
    start, end = _clip_segment(start, end, clip_polygons)
    px, py = -uy * thickness / 2, ux * thickness / 2
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
    """Replay a frozen recipe at a master with seven clipped hatch quads/group."""

    p = coerce_params(params)
    p = replace(p, jit=recipe.jitter_amp, hatch_n=HATCH_N)
    outline = build_contours(recipe.name, p, seed=seed, topology=recipe.topology)
    vector = p.v
    wall_pieces: list[LayerPiece] = []
    dark: list[LayerPiece] = []
    bronze: list[LayerPiece] = []
    for run in recipe.runs:
        points = outline.pieces[run.piece_index].contours[run.contour_index].points
        wall = _wall_piece(points, run, vector)
        wall_pieces.append(wall)
        (bronze if run.color == "bronze" else dark).append(wall)

    hatches: list[LayerPiece] = []
    for group in recipe.hatch_groups:
        contour = outline.pieces[group.piece_index].contours[group.contour_index].points
        before = wall_pieces[group.before_run].outer
        after = wall_pieces[group.after_run].outer
        half = HATCH_N // 2
        for mark in range(-half, half + 1):
            boundary = _walk_contour(
                contour,
                group.anchor_edge,
                abs(mark) * p.hatch_sp,
                1 if mark >= 0 else -1,
            )
            center = boundary.translated(vector[0] * 0.5, vector[1] * 0.5)
            hatches.append(_hatch_quad(center, vector, p.hatch_t, (before, after)))

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
