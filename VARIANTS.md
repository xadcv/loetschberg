# Lötschberg variants

The primary Lötschberg colour font has two orthogonal OpenType toggles over one four-axis designspace. They are substitutions, not boolean variation axes. Separate Regular and Extruded families are supplied only as palette-free compatibility exports for applications that cannot render COLRv1.

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
| `opsz` | Optical size | 8 | 12 | 144 | Caption applies the donor’s 81% skeleton plus optical stroke/spacing/depth values; hatch count is fixed |
| `slnt` | Slant | -12 | 0 | 0 | Transform-only post-shear; upright is the default and maximum |

Depth varies with optical size from the small `[46,54]` vector to the display `[60,70]` vector and is held constant across weight and width. At slanted locations the vector and all outline layers receive the same shear.

Complete `wght` × `wdth` source planes at both `opsz=8` and `opsz=12` make the Caption ratios exact when axes are combined; they are not reconstructed as unrelated additive deltas.

## Three locked colour decisions

### 1. Variable COLRv1

The extrusion is live text at every weight, width, optical size, and slant, so the production colour strategy is variable COLRv1. It keeps one selectable font and lets ordinary `gvar`-driven layer glyphs carry all shape variation while the COLR paint graph remains simple and interoperable with modern web and desktop applications.

### 2. Seven hatch marks per group

`HATCH_N = 7` everywhere in the designspace. Hatching is essential whenever depth is enabled; it is never removed at small optical sizes. Optical size selects the donor's nominal hatch thickness, while short projected walls compress spacing rather than dropping marks. Every emitted quad retains that per-master thickness and the nominal `0.8·|v|` length. The constant count preserves both the intended visual identity and interpolation-compatible contour topology.

### 3. Frozen decomposition recipe

Wall runs, bronze/charcoal labels, hatch-group anchors, and layer ordering are computed once at the default master, separately for regular and handdrawn outlines. That recipe is replayed at every master. Recomputing visibility or run length at arbitrary locations could change contour counts or flip the decomposition, which would make variable layer outlines incompatible.

Each frozen hatch group always emits seven four-point quads. Wall contours are rebuilt from the recipe against the current compatible edge points and current extrusion vector. A strict geometric audit showed that some concave projected transitions cannot contain a full-width centred quad by longitudinal endpoint clipping alone without changing its point model. The production COLRv1 graph therefore clips the nominal hatch paint at render time with `PaintComposite(SRC_IN)`, using the live dark/bronze wall union as the alpha mask. The result is an exact variable intersection at arbitrary axis locations while the source hatch remains a compatible, non-folding four-point quad.

This is a controlled implementation detail of the frozen-recipe clipping rule: the recipe, anchors, hatch count, and nominal mark geometry are still computed and frozen during the build; only the final intersection is delegated to the standard COLRv1 compositing operation so it remains valid between masters.

The keyline and face likewise preserve compatible topology. The production back-to-front order is:

1. dark wall (`#3A332A`)
2. bronze wall (`#B07A41`)
3. hatch (`#3A332A`), clipped to the live wall union with `SRC_IN`
4. keyline (`#2A2016`)
5. ochre face (`#E2A250`)

All colours are fixed CPAL entries. There are no variable solid colours or variable paint transforms.

## Font flavour contract

The primary `Loetschberg-VF[wght,wdth,opsz,slnt].ttf` is `glyf`-flavoured because variable COLRv1 rendering is the reliability target. Its `Loetschberg-VF.woff2` and `Loetschberg-VF.woff` web aliases carry the same variable outlines, GSUB features, COLRv1 graph, and CPAL palette.

`Loetschberg-Text-VF[wght,wdth,opsz,slnt].otf` is a CFF2 mono sidecar in the separately installable **Lötschberg Text** family. It contains base and `.hand` outlines plus `ss01`; COLR/CPAL, `.ext`, `.hand.ext`, and `ss02` are stripped. The sidecar is a pure text font, not a fallback colour family.

## Figma compatibility exports

Two palette-free `glyf` variable TTFs make the same designspace usable in Figma and conventional monochrome text applications:

| File | Install family | Default construction | OpenType variant |
|---|---|---|---|
| `Loetschberg-Regular-VF[wght,wdth,opsz,slnt].ttf` | **Lötschberg** | Regular flat outline | `ss01` → Handdrawn flat |
| `Loetschberg-Extruded-VF[wght,wdth,opsz,slnt].ttf` | **Lötschberg Extruded** | Monochrome extruded silhouette with seven hatch knockouts | `ss01` → Handdrawn extruded |

Both exports retain `wght`, `wdth`, `opsz`, and `slnt`. Neither contains COLR/CPAL or `ss02`: the extrusion is fixed at the family level, and Handdrawn remains the single user-selectable stylistic set. The Extruded export represents the extrusion and essential seven-mark hatching with ordinary outlines, so it does not reproduce the ochre/bronze/charcoal/keyline palette.

Install only these two compatibility TTFs for Figma. The Regular compatibility export intentionally shares the **Lötschberg** family name with the primary COLRv1 font, so co-installing those two builds creates a family collision. The primary COLRv1 TTF and its WOFF aliases remain the authoritative full-colour deliverables for the web and modern colour-font applications.

## Interpolation invariant

For every glyph family and every colour layer, all masters must have the same contour count, point count per contour, point order, and start point. Jitter moves existing points but never inserts or deletes them. The frozen recipe fixes wall and hatch cardinality; every hatch remains a four-point quad with the same point order. A mismatch or integer-quantized wall collapse is a hard build failure, not a warning. Paint-graph tests separately assert the `SRC_IN` wall mask used for rendered clipping.

## STAT and application UI caveat

STAT describes the four registered variation axes and their named/elidable axis values and supports the named instances. OpenType stylistic sets are GSUB features: the STAT table cannot, by itself, encode `ss01` and `ss02` as independent style axes or guarantee that an operating-system font picker exposes them.

The feature names **Handdrawn** and **Extruded** are therefore supplied through GSUB `featureNames`/name records in the primary font. Applications with OpenType feature controls can expose both toggles; applications that only expose STAT axes will show the four continuous axes but may not show either stylistic set.

The two Figma compatibility exports are a deliberate renderer fallback, not fake variation axes: each keeps the same four-axis geometry, fixes Regular or Extruded at the family level, and exposes only **Handdrawn** through `ss01`.
