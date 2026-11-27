# Lötschberg variants

The primary Lötschberg colour font has two orthogonal OpenType toggles over one two-axis designspace. The toggles are substitutions, not boolean variation axes. A palette-free, overlap-unioned Regular family is supplied for local applications that cannot render COLRv1 reliably.

## Feature states

| Feature | Name | Off | On |
|---|---|---|---|
| `ss01` | Handdrawn | Regular parametric outline (`jit=0`) | Point-compatible displaced outline (`jit=3.4`) |
| `ss02` | Extruded | Mono face outline | Variable COLRv1 extrusion with walls, seven-mark hatch groups, keyline, and face |

| `ss01` | `ss02` | Glyph family | Result |
|---:|---:|---|---|
| off | off | `base` | Regular, flat default |
| on | off | `.hand` | Handdrawn, flat |
| off | on | `.ext` | Regular, extruded COLRv1 |
| on | on | `.hand.ext` | Handdrawn, extruded COLRv1 |

The substitutions converge in either order:

```fea
feature ss01 {
  featureNames { name "Handdrawn"; };
  sub @base by @hand;
  sub @ext by @hand_ext;
} ss01;

feature ss02 {
  featureNames { name "Extruded"; };
  sub @base by @ext;
  sub @hand by @hand_ext;
} ss02;
```

## Registered axes

| Tag | Name | Min | Default | Max | Notes |
|---|---|---:|---:|---:|---|
| `wght` | Weight | 100 | 400 | 900 | Coordinated stroke, counter, skeleton, and advance progression |
| `wdth` | Width | 75 | 100 | 125 | Skeleton/layout width with weight-aware compensation at the black end |

Twelve exact sources cover four weights at three widths. Optical size and slant are intentionally absent from version 1.0.4. Handdrawn remains a stylistic set, so it does not consume an axis and works at every weight/width location.

## Colour construction

The production colour strategy is variable COLRv1. Ordinary `gvar`-driven layer glyphs carry shape variation while the paint graph remains fixed.

`HATCH_N = 7` everywhere. Wall runs, wall colours, hatch anchors, and layer order are frozen once, separately for Regular and Handdrawn, then replayed at every source. Each hatch remains a compatible four-point quad. The COLRv1 graph clips the nominal hatch paint to the live wall union with `PaintComposite(SRC_IN)`.

A wall must start and stop where two pieces meet, and that point moves with weight and width. Each outline is therefore sampled between its junctions: every place where an edge enters or leaves another piece owns a sample point, and that point sits on the junction at every source. The default master fixes the junction structure; a junction that exists only at another source is added as a pair that collapses to one point elsewhere.

A run is split wherever its edges stop facing the extrusion at any source. Each part is its own wall contour. At a source where it faces away it is flat: it keeps its points, carries no depth, and cannot cancel the wall beside it under the nonzero fill.

Back-to-front paint order:

1. dark wall (`#3A332A`)
2. bronze wall (`#B07A41`)
3. hatch (`#3A332A`), clipped to the wall union
4. keyline (`#2A2016`)
5. ochre face (`#E2A250`)

All colours are fixed CPAL entries.

## Font flavour contract

`Loetschberg-VF[wght,wdth].ttf` is the primary `glyf` COLRv1 font. Its WOFF2 and WOFF aliases carry the same variable outlines, GSUB features, paint graph, and palette.

`Loetschberg-Text-VF[wght,wdth].otf` is the CFF2 mono sidecar in the separately installable **Lötschberg Text** family. It contains base and `.hand` outlines plus `ss01`; COLR/CPAL, `.ext`, `.hand.ext`, and `ss02` are omitted.

## Figma compatibility exports

| File | Install family | Default construction | OpenType variant |
|---|---|---|---|
| `Loetschberg-Regular-VF[wght,wdth].ttf` | **Lötschberg** | Overlap-unioned Regular flat outline | `ss01` → Handdrawn flat |

The export retains only `wght` and `wdth`; it contains no COLR/CPAL or `ss02`. Its geometry, advances, and axis locations derive from the same face masters as the primary and web fonts. Overlapping source pieces are boolean-unioned at each master before variable compilation, avoiding renderer-dependent overlap handling while preserving the visible silhouettes.

Install only this compatibility TTF for Figma. Extrusion remains available in the primary COLRv1 TTF and its WOFF/WOFF2 aliases. The Regular export shares its family name with the primary COLRv1 font, so those two builds must not be co-installed.

## Interpolation invariant

Every master in every glyph family and colour layer has the same contour count, point count per contour, point order, and start point. Jitter only moves existing points. Frozen recipes fix wall and hatch cardinality. A mismatch, or a raised wall that collapses on the integer grid, is a hard build failure.

## Stroke model

Every glyph is built against one rule set, so a joint that is clean at Regular holds across both axes.

| Rule | Effect |
|---|---|
| Skeleton positions scale with width; stroke thickness follows weight | A stem is the same thickness at every width |
| A stroke's outer edge sits `max(canonical, actual) / 2` from its skeleton | Light cuts keep the Regular silhouette and open the counter; heavy cuts grow evenly |
| Vertical extremes stay on the alignment zones | Round letters keep cap and x-height at every weight |
| A piece is placed from the edges of the stroke it joins | Bowls share their stem's edge; diagonals leave from bar corners |
| Attached pieces overlap their parent | No joint is a zero-width seam |

## STAT and application UI

STAT describes the two registered axes and their named values. OpenType stylistic sets are GSUB features, so STAT cannot encode `ss01` and `ss02` as independent axes or guarantee a font picker exposes them.

The primary font supplies the names **Handdrawn** and **Extruded** through GSUB feature names. The compatibility family fixes the flat construction and exposes only **Handdrawn** through `ss01`.
