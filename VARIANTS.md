# Lötschberg variants

The primary Lötschberg colour font has two orthogonal OpenType toggles over one two-axis designspace. The toggles are substitutions, not boolean variation axes. Separate Regular and Extruded families are supplied as palette-free compatibility exports for applications that cannot render COLRv1.

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

Twelve exact sources cover four weights at three widths. Optical size and slant are intentionally absent from version 1.0.2. Handdrawn remains a stylistic set, so it does not consume an axis and works at every weight/width location.

## Colour construction

The production colour strategy is variable COLRv1. Ordinary `gvar`-driven layer glyphs carry shape variation while the paint graph remains fixed.

`HATCH_N = 7` everywhere. Frozen wall runs, wall colours, hatch anchors, and layer order are computed once at the default master, separately for Regular and Handdrawn, then replayed at every source. Each hatch remains a compatible four-point quad. The COLRv1 graph clips the nominal hatch paint to the live wall union with `PaintComposite(SRC_IN)`.

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
| `Loetschberg-Regular-VF[wght,wdth].ttf` | **Lötschberg** | Regular flat outline | `ss01` → Handdrawn flat |
| `Loetschberg-Extruded-VF[wght,wdth].ttf` | **Lötschberg Extruded** | Extrusion-only depth layer with hatch knockouts | `ss01` → Handdrawn depth |

Both exports retain only `wght` and `wdth`; neither contains COLR/CPAL or `ss02`. Their advances and axis locations match exactly. To reproduce separate face and extrusion colours in Figma, duplicate a text object in place, apply **Lötschberg Extruded** to the lower object and **Lötschberg** to the upper object, then choose each object’s colour independently. The depth layer omits face and keyline outlines; its reversed hatches only knock through wall ink.

Install only these two compatibility TTFs for Figma. The Regular export shares its family name with the primary COLRv1 font, so those two builds must not be co-installed.

## Interpolation invariant

Every master in every glyph family and colour layer has the same contour count, point count per contour, point order, and start point. Jitter only moves existing points. Frozen recipes fix wall and hatch cardinality. A mismatch or integer-quantized wall collapse is a hard build failure.

## STAT and application UI

STAT describes the two registered axes and their named values. OpenType stylistic sets are GSUB features, so STAT cannot encode `ss01` and `ss02` as independent axes or guarantee a font picker exposes them.

The primary font supplies the names **Handdrawn** and **Extruded** through GSUB feature names. The compatibility families fix Regular or Extruded at the family level and expose only **Handdrawn** through `ss01`.
