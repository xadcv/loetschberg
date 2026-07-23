# Lötschberg

**Language:** English · [Schwiizerdütsch](README.de-CH.md)

Lötschberg is a two-axis variable typeface generated from parametric geometry. Weight and width remain continuous; Handdrawn is an interpolation-compatible `ss01` stylistic set rather than a third axis. Optical size and slant were deliberately removed in 1.0.2 so the same variable family loads reliably in Figma and conventional desktop applications.

The primary font is a `glyf` variable COLRv1 font for live colour text. A mono CFF2 OTF is provided for text workflows, and separate palette-free Regular and Extruded `glyf` TTFs provide Figma-compatible families. In the primary colour font, `ss02` selects the extruded construction. `ss01` and `ss02` are independent and converge in either order.

## Source governance

Outline geometry comes exclusively from the original grid generator, `project/Loetschberg Character Grid.dc.html`. The specimen generator and reconstruction brief contribute parameters and design intent only. Their outlines are not font sources. The deterministic Python port is [src/loetschberg/generator.py](src/loetschberg/generator.py), locked to canonical script SHA-256 `b42ad1dfdf204d650da26e35624b3283466350efb0bf780ad0fb3777ee02f47a`.

The port was extracted from `class Component extends DCLogic` in the well-formed `script[type="text/x-dc"][data-dc-script]` element. Its `data-props` JSON was HTML-entity decoded. `support.js` was a preview runtime and was never run by the font build.

## Reproducible build

The project uses [uv](https://docs.astral.sh/uv/) for dependency and command isolation:

```sh
uv sync
uv run python build.py
uv run pytest
```

Run these commands from the repository root. `build.py` creates the compatible masters and designspaces, compiles all variable fonts, adds GSUB/COLRv1/CPAL/STAT data, produces the web fonts, and runs topology assertions.

## Root deliverables

| File | Purpose |
|---|---|
| `Loetschberg-VF[wght,wdth].ttf` | Primary variable colour font with `ss01`, `ss02`, COLRv1, and CPAL |
| `Loetschberg-Text-VF[wght,wdth].otf` | Mono CFF2 text sidecar with base outlines and `ss01` |
| `Loetschberg-Regular-VF[wght,wdth].ttf` | Palette-free Regular family for Figma, with `ss01` |
| `Loetschberg-Extruded-VF[wght,wdth].ttf` | Palette-free extrusion-only registration layer for Figma, with `ss01` |
| `Loetschberg-VF.woff2` / `.woff` | Web aliases of the primary colour font |
| `Loetschberg-1.0.2.zip` | Versioned release package |
| `index.html` | Interactive web specimen |
| `VARIANTS.md` | Feature, colour, and compatibility contract |
| `fontbakery-*-report.{json,md}` | Offline checks for each install family |
| `interpolatable-report.json` | Source interpolation diagnostic |
| `validation-report.json` | Machine-readable release gate |

The Python port, 12 UFO masters per designspace, tests, and reports are retained engineering artifacts. They are not alternate outline authorities.

## Figma compatibility

Install only this pair for Figma:

- **Lötschberg** — flat construction, with Handdrawn through `ss01`.
- **Lötschberg Extruded** — extrusion-only depth layer with hatch knockouts, with Handdrawn through `ss01`.

Both are true two-axis variable `glyf` fonts with identical advances and registration. In Figma, duplicate the text layer without moving it: use **Lötschberg Extruded** on the lower layer for the depth colour and **Lötschberg** on the upper layer for the face colour. The depth glyph deliberately omits the face and keyline, so the background remains visible through counters and hatch knockouts and no reversed hatch can cut through the foreground face.

Do not co-install the primary `Loetschberg-VF[wght,wdth].ttf`: it intentionally shares the **Lötschberg** family name with the Regular compatibility font.

## Designspace

| Axis | Tag | Minimum | Default | Maximum | Behaviour |
|---|---:|---:|---:|---:|---|
| Weight | `wght` | 100 | 400 | 900 | Continuous Thin→Regular→Black stroke and counter system |
| Width | `wdth` | 75 | 100 | 125 | Continuous Condensed→Normal→Expanded skeleton and spacing |

The source plane contains exact Thin, Regular, Bold, and Black masters at Condensed, Normal, and Expanded widths. Named instances cover all 12 combinations.

The 1.0.2 geometry coordinates the two axes instead of scaling independent pieces. Above Regular, added ink is eased across the external skeleton and the internal counter rather than consuming the counter alone. The width extremes apply matching black skeleton compensation, and curve strokes bias outward as weight rises. Round forms retain explicit counter floors; joined bowls share stroke centres; diagonal bands are clipped from centre lines; and load-bearing joins use attachment-constrained caps. This keeps apertures, joins, stroke rhythm, and apparent spacing coherent from Thin Condensed through Black Expanded.

Wall planes are checked after the complete glyph shift and y-flip using OpenType rounding. If a valid floating plane would collapse onto one integer line, only its rear edge receives the smallest at-most-two-unit lattice correction that preserves winding and area.

## Features and colour

`ss01` is named **Handdrawn** and substitutes point-compatible `jit=3.4` outlines. `ss02` is named **Extruded** and substitutes COLRv1 base glyphs. Enabling both selects the handdrawn extrusion regardless of feature order.

The CPAL palette is:

| Index | Role | Colour |
|---:|---|---|
| 0 | Ochre face | `#E2A250` |
| 1 | Bronze wall | `#B07A41` |
| 2 | Charcoal wall/hatch | `#3A332A` |
| 3 | Keyline | `#2A2016` |

The five logical COLRv1 paints are ordered dark wall, bronze wall, hatch, keyline, then face. Hatch quads are clipped at render time to the live wall union with `PaintComposite(SRC_IN)`. This preserves seven compatible four-point marks per group across the entire designspace.

## Coordinates and metrics

Source coordinates are y-down. The font transform is `font_x = src_x` and `font_y = 700 - src_y`, at 1000 units per em.

| Metric | Value |
|---|---:|
| Units per em | 1000 |
| Cap height | 700 |
| x-height | 500 |
| Ascender / `winAscent` | 960 |
| Descender | -300 |
| `winDescent` | 300 |
| Line gap | 0 |

Advances vary by weight and width and are captured in HVAR. All desktop binaries use installable embedding (`fsType=0`) and carry variation PostScript prefix name ID 25. Release 1.0.2 carries internal font version `1.002`.

## Validation contract

The build fails if any glyph changes contour count, point count, point order, or start point between masters. This applies to base, `.hand`, wall, hatch, keyline, face, `.ext`, and `.hand.ext` outlines. Source gates also require non-collapsing integer-quantized walls and seven correctly centred hatch marks per frozen group.

Before release:

1. Run `uv run pytest`.
2. Run FontBakery and `ots-sanitize` on all four desktop fonts.
3. Verify `hb-shape` for `ss01`, `ss02`, and their two application orders.
4. Freeze and render weight/width extrema and all named instances.
5. Confirm the WOFF2 and WOFF aliases load in `index.html` and remain variable across both axes.

Firefox, macOS, Illustrator, InDesign, and Figma remain external visual checks when those runtimes are unavailable in the build environment.
