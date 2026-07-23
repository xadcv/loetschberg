# Lötschberg variants

Lötschberg has two orthogonal OpenType toggles over one four-axis designspace. They are substitutions, not separate font families and not boolean variation axes.

## The two toggles

| Feature | Name | Off | On |
|---|---|---|---|
| `ss01` | Handdrawn | Regular parametric outline (`jit=0`) | Smoothly displaced, point-compatible outline (`jit=3.4`) |
| `ss02` | Extruded | Mono face outline | Variable COLRv1 extrusion with walls, seven-mark hatch groups, keyline, and face |

This creates four reachable states:

| `ss01` | `ss02` | Glyph family | Result |
|---:|---:|---|---|
| off | off | `base` | Regular, flat, cmapped default |
| on | off | `.hand` | Handdrawn, flat |
| off | on | `.ext` | Regular, extruded COLRv1 |
| on | on | `.hand.ext` | Handdrawn, extruded COLRv1 |

The substitutions converge in either application order:

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

Thus `ss01` followed by `ss02` and `ss02` followed by `ss01` both finish at `.hand.ext`.

## Registered axes

| Tag | Name | Min | Default | Max | Notes |
|---|---|---:|---:|---:|---|
| `wght` | Weight | 100 | 400 | 900 | Stroke values follow the specified Thin→Regular→Black ramp |
| `wdth` | Width | 75 | 100 | 125 | Specimen `w` controls skeleton/layout x positions while stems retain their weight |
| `opsz` | Optical size | 8 | 12 | 144 | Interpolates small/display geometry and spacing parameters; hatch count is fixed |
| `slnt` | Slant | -12 | 0 | 0 | Transform-only post-shear; upright is the default and maximum |

Depth varies with optical size from the small `[46,54]` vector to the display `[60,70]` vector and is held constant across weight and width. At slanted locations the vector and all outline layers receive the same shear.

## Three locked colour decisions

### 1. Variable COLRv1

The extrusion is live text at every weight, width, optical size, and slant, so the production colour strategy is variable COLRv1. It keeps one selectable font and lets ordinary `gvar`-driven layer glyphs carry all shape variation while the COLR paint graph remains simple and interoperable with modern web and desktop applications.

### 2. Seven hatch marks per group

`HATCH_N = 7` everywhere in the designspace. Hatching is essential whenever depth is enabled; it is never removed at small optical sizes. Optical size may shrink hatch thickness, spacing, and length, but not count. The constant count preserves both the intended visual identity and interpolation-compatible contour topology.

### 3. Frozen decomposition recipe

Wall runs, bronze/charcoal labels, hatch-group anchors, and layer ordering are computed once at the default master, separately for regular and handdrawn outlines. That recipe is replayed at every master. Recomputing visibility or run length at arbitrary locations could change contour counts or flip the decomposition, which would make variable layer outlines incompatible.

Each frozen hatch group always emits seven clipped four-point quads. Wall contours are rebuilt from the recipe against the current compatible edge points and current extrusion vector. The keyline and face likewise preserve compatible topology. The required back-to-front order is:

1. dark wall (`#3A332A`)
2. bronze wall (`#B07A41`)
3. hatch (`#3A332A`)
4. keyline (`#2A2016`)
5. ochre face (`#E2A250`)

All colours are fixed CPAL entries. There are no variable solid colours or variable paint transforms.

## Font flavour contract

The primary `Loetschberg-VF[wght,wdth,opsz,slnt].ttf` is `glyf`-flavoured because variable COLRv1 rendering is the reliability target. Its `Loetschberg-VF.woff2` and `Loetschberg-VF.woff` web aliases carry the same variable outlines, GSUB features, COLRv1 graph, and CPAL palette.

`Loetschberg-Text-VF[wght,wdth,opsz,slnt].otf` is a CFF2 mono sidecar in the separately installable **Lötschberg Text** family. It contains base and `.hand` outlines plus `ss01`; COLR/CPAL, `.ext`, `.hand.ext`, and `ss02` are stripped. The sidecar is a pure text font, not a fallback colour family.

## Interpolation invariant

For every glyph family and every colour layer, all masters must have the same contour count, point count per contour, point order, and start point. Jitter moves existing points but never inserts or deletes them. The frozen recipe fixes wall and hatch cardinality. A mismatch is a hard build failure, not a warning.

## STAT and application UI caveat

STAT describes the four registered variation axes and their named/elidable axis values and supports the named instances. OpenType stylistic sets are GSUB features: the STAT table cannot, by itself, encode `ss01` and `ss02` as independent style axes or guarantee that an operating-system font picker exposes them.

The feature names **Handdrawn** and **Extruded** are therefore supplied through GSUB `featureNames`/name records. Applications with OpenType feature controls can expose both toggles; applications that only expose STAT axes will show the four continuous axes but may not show either stylistic set. Do not add fake variation axes or separate families to work around that UI limitation.
