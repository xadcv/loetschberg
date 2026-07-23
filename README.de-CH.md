# Lötschberg

**Sproch:** [English](README.md) · Schwiizerdütsch

Lötschberg isch e variabli Schrift mit zwei Achse, wo us parametrischer Geometrie generiert wird. Gwicht und Breiti bliibed stufelos; Handdrawn isch es interpolationskompatibles `ss01`-Feature und kei dritti Achse. Optischi Grössi und Neiig sind im Release 1.0.2 absichtlich entfalle, damit die gliich variabli Familie zuverlässig i Figma und klassische Desktop-Apps lädt.

D Primärschrift isch e variabli COLRv1-Schrift im `glyf`-Format. Dezue git s e monochromi CFF2-Text-OTF und separati Regular- und Extruded-TTFs ohni Palette für Figma. I de Primärschrift wählt `ss02` d Extrusion; `ss01` und `ss02` funktioniered unabhängig und i beidne Reihefolge.

## Quälle-Regle

D Umrissgeometrie chunnt ussschliesslich vom ursprüngliche Grid-Generator `project/Loetschberg Character Grid.dc.html`. De Specimen-Generator und s Rekonstruktions-Briefing liefered nume Parameter und Designabsicht. De deterministisch Python-Port isch [src/loetschberg/generator.py](src/loetschberg/generator.py), fixiert uf de kanonische Skript-SHA-256 `b42ad1dfdf204d650da26e35624b3283466350efb0bf780ad0fb3777ee02f47a`.

## Reproduzierbare Build

```sh
uv sync
uv run python build.py
uv run pytest
```

`build.py` generiert kompatibli Masters und Designspaces, kompiliert all variable Schrifte, ergänzt GSUB/COLRv1/CPAL/STAT, produziert d Webschrifte und prüeft d Topologie.

## Usgaabdateie

| Datei | Zwäck |
|---|---|
| `Loetschberg-VF[wght,wdth].ttf` | Primäri variabli Farbschrift mit `ss01`, `ss02`, COLRv1 und CPAL |
| `Loetschberg-Text-VF[wght,wdth].otf` | Monochromi CFF2-Textfamilie mit `ss01` |
| `Loetschberg-Regular-VF[wght,wdth].ttf` | Flachi Figma-Familie mit `ss01` |
| `Loetschberg-Extruded-VF[wght,wdth].ttf` | Reini Tüüfe-Ebeni für Figma mit `ss01` |
| `Loetschberg-VF.woff2` / `.woff` | Web-Aliasse vo de Primärschrift |
| `Loetschberg-1.0.2.zip` | Versionierts Release-Paket |
| `index.html` | Interaktivs Web-Specimen |
| `VARIANTS.md` | Feature-, Farb- und Kompatibilitätsvertrag |

## Figma-Kompatibilität

Installier für Figma nume das Paar:

- **Lötschberg** — flachi Konstruktion, Handdrawn über `ss01`.
- **Lötschberg Extruded** — reini Extrusions-Ebeni mit Schraffur, Handdrawn über `ss01`.

Beidi sind echti variable `glyf`-Schrifte mit `wght`, `wdth` und identische Vorbreitene. Duplizier i Figma d Textebeni ohni si z verschiebe: **Lötschberg Extruded** chunnt unde für d Tüüfefarb, **Lötschberg** obe für d Vordersite. D Tüüfe-Ebeni enthaltet kei Vordersite und kei Keyline; Hintergrund, Innenrüüm und Schraffur bliibed drum suuber offe.

D primäri `Loetschberg-VF[wght,wdth].ttf` sött nöd gliichziitig installiert sii, will si de Familiename **Lötschberg** mit de Regular-Kompatibilitätsschrift teilt.

## Designspace

| Achse | Tag | Minimum | Standard | Maximum |
|---|---:|---:|---:|---:|
| Gwicht | `wght` | 100 | 400 | 900 |
| Breiti | `wdth` | 75 | 100 | 125 |

Zwölf exakti Quälle decked Thin, Regular, Bold und Black in Condensed, Normal und Expanded ab.

D Geometrie vo 1.0.2 koordiniert beidi Achse. Oberhalb vo Regular wird zusätzlichi Tinte weich uf s äussere Skelett und de Innenruum verteilt, statt nume de Innenruum z frässe. Rundi Forme händ expliziti Mindest-Innenrüüm, verbundeni Rundige teiled Strichmitte, und belasteti Übergäng bruuched verbindigsbegränzti Abschlüss. So bliibed Öffnige, Verbindige, Strichrhythmus und optischi Abständ vo Thin Condensed bis Black Expanded harmonisch.

## Features und Farbe

`ss01` heisst **Handdrawn** und ersetzt d Basis mit punktkompatible `jit=3.4`-Umriss. `ss02` heisst **Extruded** und ersetzt d COLRv1-Basisglyph.

| Index | Rolle | Farb |
|---:|---|---|
| 0 | Ocker-Vordersite | `#E2A250` |
| 1 | Bronzefarbigi Wand | `#B07A41` |
| 2 | Anthrazit-Wand/-Schraffur | `#3A332A` |
| 3 | Keyline | `#2A2016` |

Jedi Schraffur-Gruppe het über de ganze Designspace siebe kompatibli Vierpünkt-Forme. `PaintComposite(SRC_IN)` schniidet si zur Laufziit exakt a de variable Wandfläche ab.

## Metrike und Version

| Metrik | Wert |
|---|---:|
| Einheite pro em | 1000 |
| Versalhöchi | 700 |
| x-Höchi | 500 |
| Oberlängi / `winAscent` | 960 |
| Unterlängi | -300 |
| `winDescent` | 300 |
| Zileabstand | 0 |

All Desktop-Schrifte bruuched installierbars Embedding (`fsType=0`) und de Variation-PostScript-Prefix name ID 25. Release 1.0.2 het d interni Schriftversion `1.002`.

## Validierungsvertrag

De Build bricht ab, wenn sich zwüsche Masters d Konturzahl, Punktzahl, Pünktreiefolg oder de Startpunkt änderet. Das gilt für Basis, `.hand`, Wand, Schraffur, Keyline, Vordersite, `.ext` und `.hand.ext`.

Vor em Release:

1. `uv run pytest` usfüehre.
2. FontBakery und `ots-sanitize` uf all vier Desktop-Schrifte usfüehre.
3. `ss01`, `ss02` und beidi Feature-Reihefolge mit `hb-shape` prüefe.
4. Gwicht-/Breiti-Extrem und all benännte Instanze rendere.
5. WOFF2 und WOFF im `index.html` über beidi Achse prüefe.
