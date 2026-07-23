# Lötschberg

Lötschberg is a four-axis variable typeface generated from parametric geometry. The primary font is a `glyf`-flavoured variable COLRv1 font for live colour text; a mono CFF2 OTF is provided for text workflows that do not need colour. `ss01` selects the handdrawn construction and `ss02` selects the extruded colour construction. The two features are independent and work together.

## Source governance (locked)

Outline geometry comes **exclusively** from the original grid generator, `project/Loetschberg Character Grid.dc.html`. The specimen generator and reconstruction brief contribute **parameters and design intent only**; their outlines must never be used to build the font. The handoff files are intentionally absent from the release repository; their deterministic Python port is [src/loetschberg/generator.py](src/loetschberg/generator.py), locked to the decoded canonical script SHA-256 `b42ad1dfdf204d650da26e35624b3283466350efb0bf780ad0fb3777ee02f47a`.

The two source generators have diverged for `O S G H E T L`, while only `B R` match, per the locked project rule. This statement remains authoritative even if comparisons of the current exported snapshots appear to produce a different result.

The port was extracted from `class Component extends DCLogic` in the well-formed `script[type="text/x-dc"][data-dc-script]` element. Its `data-props` JSON was HTML-entity decoded. `support.js` was a preview runtime and was never run by the font build.

## Reproducible build

The project uses [uv](https://docs.astral.sh/uv/) for dependency and command isolation. Use `uv sync` and `uv run` only; neither `pip` nor `uv pip` is part of the build.

```sh
uv sync
uv run python build.py
uv run pytest
```

Run those commands from the repository root. `build.py` runs the checked-in canonical Python port, creates compatible masters and designspaces, compiles the variable fonts, adds GSUB/COLRv1/CPAL/STAT data, produces the web fonts, and runs build-time topology assertions. Re-running it from a clean checkout reproduces the same font binaries.

## Root deliverables

The completed build exposes these user-facing files at the repository root:

| File | Purpose |
|---|---|
| `Loetschberg-VF[wght,wdth,opsz,slnt].ttf` | Primary `glyf` variable font with `ss01`, `ss02`, COLRv1, and CPAL |
| `Loetschberg-Text-VF[wght,wdth,opsz,slnt].otf` | CFF2 mono text sidecar with base outlines and `ss01`; no COLR/CPAL or `ss02` (install family `Lötschberg Text`) |
| `Loetschberg-VF.woff2` | Compressed web alias of the primary variable colour font, preferred by the specimen |
| `Loetschberg-VF.woff` | WOFF web alias of the primary variable colour font and specimen fallback |
| `index.html` | GitHub Pages type specimen; its `@font-face` loads the root WOFF file |
| `README.md` | Build, source-governance, and validation contract |
| `VARIANTS.md` | Axes, features, colour construction, and compatibility contract |
| `fontbakery-primary-report.{json,md}` | Full offline FontBakery report for the Lötschberg colour family |
| `fontbakery-sidecar-report.{json,md}` | Full offline FontBakery report for the separately installable Lötschberg Text family |
| `interpolatable-report.json` | Full 26-master `varLib.interpolatable` diagnostic for source contours |
| `validation-report.json` | Machine-readable release table/axis/artifact gate |

The Python port, UFO masters, designspace, tests, and FontBakery report are engineering deliverables retained with the reproducible build. Generated intermediates should not be mistaken for alternate outline authorities.

## Designspace

| Axis | Tag | Minimum | Default | Maximum | Behaviour |
|---|---:|---:|---:|---:|---|
| Weight | `wght` | 100 | 400 | 900 | Varies `s`/`sh`; approximately 40 at Thin, 104/100 at Regular, and 200 at Black |
| Width | `wdth` | 75 | 100 | 125 | Varies skeleton placement with specimen parameter `w`; stem thickness stays invariant |
| Optical size | `opsz` | 8 | 12 | 144 | Interpolates small/display stroke, depth, spacing, tracking, and kerning parameters; hatch count never changes |
| Slant | `slnt` | -12 | 0 | 0 | Post-shears geometry with `x' = x + tan(θ)y`; the slanted source is generated, not independently drawn |

The build uses complete 4×3 `wght` × `wdth` compatibility planes at both the default and Caption optical sizes, including exact Thin, Regular, Bold, and Black sources. A Display endpoint and one generated shear source provide `opsz=144` and `slnt=-12`. These 26 sources preserve the nonlinear counter protection and the donor’s multiplicative Caption cut when axes are combined. Named instances cover Thin, Regular, Bold, and Black across Condensed, Normal, and Expanded widths, plus Caption (8) and Display (144).

Round forms are constructed from width-scaled medial skeletons with physical stroke offsets and explicit counter floors. Joined bowls share stroke centres, diagonal bands are clipped from centerlines, and `H`, `G`, `M`, braces, waves, dots, accents, and terminals use dedicated attachment geometry. The `R` leg, `1` flag, and both `N` diagonal caps are attachment-constrained bands: canonical default coordinates remain untouched, while a non-default joining cap extends along its own centerline only when needed to retain a small overlap with its parent stroke. Together with counter protection, this avoids the former independent-piece failure mode in which Thin junctions separated while Black Condensed counters collapsed.

Wall planes are checked after the complete glyph shift, y-flip, and slant transform using the compiler's OpenType rounding rule. If a valid floating plane would collapse onto one integer line, its shared face edge remains untouched and only its rear edge receives the smallest at-most-two-unit lattice correction that preserves winding and a nonzero area margin. Genuine edge-on transitions between masters remain smooth rather than forcing a visibility change.

## Features and colour

`ss01` is named **Handdrawn** and substitutes interpolation-compatible `jit=3.4` outlines. `ss02` is named **Extruded** and substitutes COLRv1 base glyphs. Enabling both features selects the handdrawn extruded glyph regardless of feature order. See [VARIANTS.md](VARIANTS.md) for the exact substitution model and STAT limitations.

The single CPAL palette is:

| Index | Role | Colour |
|---:|---|---|
| 0 | Ochre face | `#E2A250` |
| 1 | Bronze wall | `#B07A41` |
| 2 | Charcoal wall/hatch | `#3A332A` |
| 3 | Keyline | `#2A2016` |

The specimen's `#7C453B` ground is page colour, not a glyph palette entry. The five logical COLRv1 paints are ordered back-to-front as dark wall, bronze wall, hatch, keyline, then face. The hatch paint is a standard `PaintComposite` in `SRC_IN` mode: its nominal charcoal quads are the source and the live dark/bronze wall union is the backdrop mask. This clips the rendered hatches exactly at every interpolated location while preserving their full nominal thickness, `0.8·|v|` length, fixed count, and four-point outline topology.

This runtime-variable clip is a controlled implementation of the frozen-recipe clipping rule. A build-time audit proved that full-width centred quads at some concave transitions cannot be reduced to a single four-point polygon by longitudinal endpoint clipping alone. Performing the intersection in the COLRv1 paint graph avoids folded or disappearing source contours and remains mathematically valid between masters. Palette colours remain constant; variation comes from the ordinary variable outlines referenced by the paint graph.

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

`hhea` mirrors the typo ascender, descender, and line gap. Round forms use 10–14 units of overshoot. Advances vary by master and are captured in HVAR.

## Validation contract

The build fails if any glyph changes contour count, point count, point order, or start point between masters. This invariant applies to base, `.hand`, and every wall, hatch, keyline, and face layer used by `.ext` and `.hand.ext`. Source gates additionally require non-collapsing integer-quantized walls and seven correctly centred, full-thickness four-point hatches per frozen group. Compiled-font tests require the hatch `PaintComposite` to use `SRC_IN` against the two live wall paints.

Before release:

1. Run `uv run pytest` and confirm topology, axis, cmap, GSUB convergence, COLR/CPAL, STAT, metrics, and root-artifact tests pass.
2. Run FontBakery `check-opentype` and `ots-sanitize` on both desktop fonts; retain the FontBakery report.
3. Verify `hb-shape` swaps base glyphs with `ss01`, `ss02`, and `ss01,ss02` in either feature order.
4. Freeze and render axis extrema and named instances, including `slnt=-12`, and compare waterfalls from 8–144 px with the grid references and the specimen photographs.
5. Confirm the root `Loetschberg-VF.woff2`/`Loetschberg-VF.woff` aliases load in `index.html`, remain variable across all four axes, and render COLRv1 in current Chrome, Firefox, macOS, Illustrator, and InDesign. Mono fallback must remain readable where COLRv1 is unsupported.

The visual gate checks shape fidelity against the grid renders and design intent against the specimen photographs. It must not promote the stale specimen outlines into build geometry.

## Release results

- `uv run pytest -q`: 30 passed, including source and compiled-interpolation gates for the Thin `R`/`N`/`1` joins and all 380 COLRv1 paint graphs.
- Topology report: 26 masters, 2,767 colour-source glyphs per master, zero signature mismatches, and seven hatches per frozen group.
- FontBakery 1.1.0: primary 46 pass / 7 skip / 0 fail; CFF2 sidecar 43 pass / 10 skip / 0 fail. The two install families are checked separately by design.
- OTS 9.2.0: both desktop fonts sanitize successfully.
- `varLib.interpolatable`: zero missing paths, open paths, path-count mismatches, node-count mismatches, node-type mismatches, or kinks. Its retained JSON report contains 616 start-point and 8 contour-order rematching suggestions concentrated in repeated colour-layer contours and display-to-slant comparisons; these are visual heuristics, not changes to the frozen contour/node sequence.
- Chromium: the real WOFF2 and forced WOFF fallback both load; all four feature states, the 25-location Thin width/optical-size matrix, and the known `@`/`t`/`~` hatch-clipping probes render cleanly at desktop and 390px mobile sizes without specimen overflow.

Firefox, macOS, Illustrator, and InDesign remain external release-matrix checks because those runtimes are not available in this build environment.
