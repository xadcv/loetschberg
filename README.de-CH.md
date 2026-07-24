# Lötschberg

**Sproch:** [English](README.md) · Schwiizerdütsch

Lötschberg isch e variabli Schrift mit zwei Achse, wo us parametrischer Geometrie generiert wird. Gwicht und Breiti bliibed stufelos; Handdrawn isch es interpolationskompatibles `ss01`-Feature und kei dritti Achse. Optischi Grössi und Neiig sind im Release 1.0.3 absichtlich entfalle, damit die gliich variabli Familie zuverlässig i Figma und klassische Desktop-Apps lädt.

D Primärschrift isch e variabli COLRv1-Schrift im `glyf`-Format. Dezue git s e monochromi CFF2-Text-OTF und e überlappigsbereinigti Regular-TTF für lokali Apps und Figma. Extruded bliibt i de COLRv1-TTF und de WOFF/WOFF2-Webschrifte. I de Primärschrift wählt `ss02` d Extrusion; `ss01` und `ss02` funktioniered unabhängig und i beidne Reihefolge.

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
| `Loetschberg-Regular-VF[wght,wdth].ttf` | Überlappigsbereinigti flachi Familie für lokali Apps und Figma, mit `ss01` |
| `Loetschberg-VF.woff2` / `.woff` | Web-Aliasse vo de Primärschrift |
| `Loetschberg-1.0.3.zip` | Versionierts Release-Paket |
| `index.html` | Interaktivs Web-Specimen |
| `VARIANTS.md` | Feature-, Farb- und Kompatibilitätsvertrag |

## Figma-Kompatibilität

Installier für Figma nume `Loetschberg-Regular-VF[wght,wdth].ttf`. Si isch e ächti variabli `glyf`-Schrift mit `wght`, `wdth` und Handdrawn über `ss01`. D Forme und Vorbreitene chömed a jedem Gwicht und jeder Breiti us de gliiche Masters wie d WOFF-Version. Nume d Dateidarstellig isch anders: Für lokali Font-Broker werded überlappendi Konstruktionsteili vor em variable Build vereint.

Extruded isch nur im Web/COLRv1-Build verfügbar.

D primäri `Loetschberg-VF[wght,wdth].ttf` sött nöd gliichziitig installiert sii, will si de Familiename **Lötschberg** mit de Regular-Kompatibilitätsschrift teilt.

## Designspace

| Achse | Tag | Minimum | Standard | Maximum |
|---|---:|---:|---:|---:|
| Gwicht | `wght` | 100 | 400 | 900 |
| Breiti | `wdth` | 75 | 100 | 125 |

Zwölf exakti Quälle decked Thin, Regular, Bold und Black in Condensed, Normal und Expanded ab.

D Geometrie vo 1.0.3 koordiniert beidi Achse. Oberhalb vo Regular wird zusätzlichi Tinte weich uf s äussere Skelett und de Innenruum verteilt, statt nume de Innenruum z frässe. Rundi Forme händ expliziti Mindest-Innenrüüm, verbundeni Rundige teiled Strichmitte, und belasteti Übergäng bruuched verbindigsbegränzti Abschlüss. So bliibed Öffnige, Verbindige, Strichrhythmus und optischi Abständ vo Thin Condensed bis Black Expanded harmonisch.

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

All Desktop-Schrifte bruuched installierbars Embedding (`fsType=0`) und de Variation-PostScript-Prefix name ID 25. Release 1.0.3 het d interni Schriftversion `1.003`.

## Validierungsvertrag

De Build bricht ab, wenn sich zwüsche Masters d Konturzahl, Punktzahl, Pünktreiefolg oder de Startpunkt änderet. Das gilt für Basis, `.hand`, Wand, Schraffur, Keyline, Vordersite, `.ext` und `.hand.ext`.

Vor em Release:

1. `uv run pytest` usfüehre.
2. FontBakery und `ots-sanitize` uf all drei Desktop-Schrifte usfüehre.
3. `ss01`, `ss02` und beidi Feature-Reihefolge mit `hb-shape` prüefe.
4. Gwicht-/Breiti-Extrem und all benännte Instanze rendere.
5. WOFF2 und WOFF im `index.html` über beidi Achse prüefe.
