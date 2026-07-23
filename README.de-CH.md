# Lötschberg

**Sproch:** [English](README.md) · Schwiizerdütsch

Lötschberg isch e variabli Schrift mit vier Achse, wo us parametrischer Geometrie generiert wird. D Primärschrift isch e variable COLRv1-Schrift im `glyf`-Format für live Farbtext; für Text-Workflows, wo kei Farbe bruuched, git s e monochromi CFF2-OTF. Zwei zusätzligi `glyf`-TTFs ohni Palette füehred Regular und Extruded als separati, Figma-kompatibli Familie. Mit `ss01` wird d handzeichnet Konstruktion gwählt; i de primäre Farbschrift wählt `ss02` d extrudierti Farbkonstruktion. I de Primärschrift sind die zwei Features unabhängig und funktioniered mitenand.

## Quälle-Regle (fix)

D Umrissgeometrie chunnt **ussschliesslich** vom ursprüngliche Grid-Generator `project/Loetschberg Character Grid.dc.html`. De Specimen-Generator und s Rekonstruktions-Briefing liefered **nume Parameter und Designabsicht**; ihri Umriss dörfed nie für de Schrift-Build bruucht werde. D Übergabedateie sind absichtlich nöd im Release-Repository; ihre deterministischi Python-Port isch [src/loetschberg/generator.py](src/loetschberg/generator.py), fixiert uf de SHA-256 vom dekodierte kanonische Skript: `b42ad1dfdf204d650da26e35624b3283466350efb0bf780ad0fb3777ee02f47a`.

Die zwei Quellgeneratoren sind bi `O S G H E T L` usenandergloffe, während nume `B R` übereinstimmed, wie s d fixi Projektregle vorgit. Die Ussag bliibt verbindlich, au wenn Vergliich vo de aktuell exportierte Snapshots scheinbar es anders Ergebnis liefered.

De Port isch us `class Component extends DCLogic` im korrekt formatierte Element `script[type="text/x-dc"][data-dc-script]` extrahiert worde. Sis `data-props`-JSON isch mit dekodierte HTML-Entitäte gläse worde. `support.js` isch e Preview-Runtime gsi und isch vom Schrift-Build nie usgfüehrt worde.

## Reproduzierbare Build

S Projekt brucht [uv](https://docs.astral.sh/uv/) für d Isolation vo Abhängigkeit und Befähl. Verwänd nume `uv sync` und `uv run`; weder `pip` no `uv pip` ghöred zum Build.

```sh
uv sync
uv run python build.py
uv run pytest
```

Füehr die Befähl im Wurzelverzeichnis vom Repository us. `build.py` füehrt de iicheckte kanonische Python-Port us, erstellt kompatibli Masters und Designspaces, kompiliert die variable Schrifte, füegt GSUB/COLRv1/CPAL/STAT-Date dezue, produziert d Webschrifte und füehrt Topologie-Prüefige während em Build us. Wenn de Build us eme saubere Checkout nomal lauft, entstönd die gliiche Schriftdateie.

## Usgaabdateie im Wurzelverzeichnis

De fertigi Build stellt die folgende Dateie für Nutzerinne und Nutzer im Wurzelverzeichnis vom Repository bereit:

| Datei | Zwäck |
|---|---|
| `Loetschberg-VF[wght,wdth,opsz,slnt].ttf` | Primäri variabli `glyf`-Schrift mit `ss01`, `ss02`, COLRv1 und CPAL |
| `Loetschberg-Text-VF[wght,wdth,opsz,slnt].otf` | Monochromi CFF2-Text-Sidecar-Schrift mit Basisumriss und `ss01`; ohni COLR/CPAL oder `ss02` (installiert d Familie `Lötschberg Text`) |
| `Loetschberg-Regular-VF[wght,wdth,opsz,slnt].ttf` | Variabli `glyf`-Schrift ohni Palette für Figma und klassischi Text-Apps; vier Achse plus `ss01` (installiert d Familie `Lötschberg`) |
| `Loetschberg-Extruded-VF[wght,wdth,opsz,slnt].ttf` | Variabli, extrudierti `glyf`-Schrift ohni Palette, mit Silhouette und siebe usgsparte Schraffure; vier Achse plus `ss01` (installiert d Familie `Lötschberg Extruded`) |
| `Loetschberg-VF.woff2` | Komprimierte Web-Alias vo de primäre variable Farbschrift; fürs Specimen bevorzugt |
| `Loetschberg-VF.woff` | WOFF-Web-Alias vo de primäre variable Farbschrift und Fallback fürs Specimen |
| `Loetschberg-1.0.1.zip` | Versionierts Release-Paket mit all sechs Produktionsschrifte plus `README.md`, `README.de-CH.md` und `VARIANTS.md` |
| `index.html` | GitHub-Pages-Schriftmuster; sis `@font-face` lädt d WOFF-Datei us em Wurzelverzeichnis |
| `README.md` | Vertrag für Build, Quälle-Regle und Validierig |
| `README.de-CH.md` | Vollständigi Schwiizerdütsch-Lokalisierig vom README |
| `VARIANTS.md` | Vertrag für Achse, Features, Farbkonstruktion und Kompatibilität |
| `fontbakery-primary-report.{json,md}` | Vollständige Offline-FontBakery-Bericht für d Lötschberg-Farbfamilie |
| `fontbakery-sidecar-report.{json,md}` | Vollständige Offline-FontBakery-Bericht für d separat installierbari Familie Lötschberg Text |
| `fontbakery-regular-report.{json,md}` | Vollständige Offline-FontBakery-Bericht für d Figma-kompatibli Familie Lötschberg |
| `fontbakery-extruded-report.{json,md}` | Vollständige Offline-FontBakery-Bericht für d Figma-kompatibli Familie Lötschberg Extruded |
| `interpolatable-report.json` | Vollständigi 26-Master-Diagnose vo `varLib.interpolatable` für d Quellkonture |
| `validation-report.json` | Maschinenlesbari Release-Prüefig für Tabelle, Achse und Artefakt |

De Python-Port, d UFO-Masters, de Designspace, d Tests und de FontBakery-Bericht sind Engineering-Lieferobjekt, wo mit em reproduzierbare Build erhalte bliibed. Generierti Zwüscheartefakt dörfed nöd für alternativi Autoritäte vo de Umriss ghalte werde.

## Figma-Kompatibilität

Bruuch die zwei kompatible TTFs zäme i Figma:

- **Lötschberg** — reguläri flachi Konstruktion, mit Handdrawn über `ss01`.
- **Lötschberg Extruded** — monochromi extrudierti Silhouette mit siebe usgsparte Schraffure, mit Handdrawn über `ss01`.

Beidi sind echti variabli `glyf`-Schrifte mit vier Achse. D kompatibli Extruded-Familie isch absichtlich monochrom, will Figma d COLRv1-Palettekonstruktion nöd rendert; d Extrusion und d Schraffure stecked stattdesse i gewöhnliche Umriss.

Für e suuberi Figma-Installation installier **nume das kompatible Paar**. Entfern oder deaktivier `Loetschberg-VF[wght,wdth,opsz,slnt].ttf` vorher, will d primäri Farbschrift und d kompatibli Regular-TTF absichtlich de Familiename `Lötschberg` teiled. D vollständige COLRv1-TTF-/WOFF-Versione blibed fürs Specimen, fürs Web und für moderni Farbfont-Apps.

## Designspace

| Achse | Tag | Minimum | Standard | Maximum | Verhalte |
|---|---:|---:|---:|---:|---|
| Gwicht | `wght` | 100 | 400 | 900 | Variiert `s`/`sh`; öppe 40 bi Thin, 104/100 bi Regular und 200 bi Black |
| Breiti | `wdth` | 75 | 100 | 125 | Variiert d Platzierig vom Skelett mit em Specimen-Parameter `w`; d Stammdicki bliibt konstant |
| Optischi Grössi | `opsz` | 8 | 12 | 144 | Interpoliert Parameter für Strich, Tiefe, Abstand, Tracking und Kerning zwüsche Small und Display; d Aazahl Schraffure änderet nie |
| Neiig | `slnt` | -12 | 0 | 0 | Schert d Geometrie nachträglich mit `x' = x + tan(θ)y`; d geneigti Quälle wird generiert und nöd separat zeichnet |

De Build brucht vollständigi 4×3-Kompatibilitätsebenene für `wght` × `wdth`, sowohl bi de standardmässige wie au bi de optische Caption-Grössi, inklusive exakte Quälle für Thin, Regular, Bold und Black. En Display-Endpunkt und e generierti Scher-Quälle stellid `opsz=144` und `slnt=-12` bereit. Die 26 Quälle bewahred de nichtlineari Schutz vo de Innenrüüm und de multiplikativi Caption-Schnitt vom Donor, wenn Achse mitenand kombiniert werded. Benännti Instanze decked Thin, Regular, Bold und Black in Condensed, Normal und Expanded ab, plus Caption (8) und Display (144).

Rundi Forme werded us breiteskalierten mediale Skelett mit physische Strich-Offsets und explizite Untergränze für d Innenrüüm konstruiert. Verbundeni Rundige teilid Strichmitte, diagonali Bänder werded us Mittellinie usgschnitte, und `H`, `G`, `M`, Chlammere, Wälle, Pünkt, Akzent und Endige bruuched eigeti Verbindigsgeometrie. S `R`-Bei, d `1`-Fahne und beidi diagonale `N`-Abschlüss sind verbindigsbegränzti Bänder: D kanonische Standardkoordinate bliibed unberüehrt, während en nöd standardmässige Verbindigsabschluss nume denn entlang vo de eigete Mittellinie verlängert wird, wenn das nötig isch, zum e chlini Überlappig mit em Elterestrich z bhalte. Zäme mit em Schutz vo de Innenrüüm verhindert das de früehneri Fählerfall vo unabhängig zämegsetzte Stück, bi dem sich dünni Verbindige trennt händ, während bi Black Condensed d Innenrüüm zämegheit sind.

D Wandfläche werded nach em vollständige Glyph-Shift, Y-Flip und Slant-Transform mit de OpenType-Rundigsregle vom Compiler prüeft. Wenn e gültigi Fläche mit Fliesskommazahle uf eini ganzzahligi Linie zämefalle würd, bliibt ihri gmeinsami Vorderkante unberüehrt, und nume ihri hinder Kante überchunnt di chlinscht, höchstens zwei Einheite grossi Gitterkorrektur, wo d Windigsrichtig und en Flächebereich über null erhaltet. Echti Übergäng, wo zwüsche Masters uf de Kante stönd, bliibed glatt, statt en Sichtbarkeitswechsel z erzwinge.

## Features und Farbe

`ss01` heisst **Handdrawn** und ersetzt Umriss mit eme interpolationskompatible `jit=3.4`. `ss02` heisst **Extruded** und ersetzt d COLRv1-Basisglyph. Wenn beidi Features aktiv sind, wird unabhängig vo de Feature-Reihefolg d handzeichnet extrudierti Glyph gwählt. S exakte Ersetzigsmodell und d STAT-Gränze stönd in [VARIANTS.md](VARIANTS.md).

Die einzigi CPAL-Palette isch:

| Index | Rolle | Farb |
|---:|---|---|
| 0 | Ocker-Vordersite | `#E2A250` |
| 1 | Bronzefarbigi Wand | `#B07A41` |
| 2 | Anthrazit-Wand/-Schraffur | `#3A332A` |
| 3 | Keyline | `#2A2016` |

De `#7C453B`-Hintergrund vom Specimen isch e Sitefarb und kei Glyph-Farb us de Palette. Die fünf logische COLRv1-Paints sind vo hinder nach vorne so sortiert: dunkli Wand, bronzefarbigi Wand, Schraffur, Keyline und denn d Vordersite. De Schraffur-Paint isch en standardmässige `PaintComposite` im `SRC_IN`-Modus: Sini nominale anthrazitfarbige Viereck sind d Quälle, und d aktuell Vereinigung vo de dunkle und bronzefarbige Wand isch d Hintergrundmaske. So werded d grenderte Schraffure a jedere interpolierte Position exakt abgschnitte, während ihri volli nominali Dicki, d Längi vo `0.8·|v|`, ihri fixi Aazahl und d Umrisstopologie mit vier Pünkt erhalte bliibed.

De zur Laufziit variable Usschnitt isch e kontrollierti Umsetzig vo de Clipping-Regle mit em fixierte Rezept. E Build-Ziit-Prüefig het zeigt, dass mittig usgrichteti Viereck mit voller Breiti a gewisse konkave Übergäng nöd nume mit em längsseitige Abschniide vo de Endpünkt uf es einzelns vierpünktigs Polygon reduziert werde chönd. D Überschniidig im COLRv1-Paint-Graph verhindert gfalteti oder verschwindendi Quellkonture und bliibt zwüsche de Masters mathematisch gültig. D Palettefarbe bliibed konstant; d Variation chunnt vo de gewöhnliche variable Umriss, wo de Paint-Graph referenziert.

## Koordinate und Metrike

D Quellkoordinate laufed uf de Y-Achse abwärts. D Schrifttransformation isch `font_x = src_x` und `font_y = 700 - src_y`, bi 1000 Einheite pro em.

| Metrik | Wert |
|---|---:|
| Einheite pro em | 1000 |
| Versalhöchi | 700 |
| x-Höchi | 500 |
| Oberlängi / `winAscent` | 960 |
| Unterlängi | -300 |
| `winDescent` | 300 |
| Zileabstand | 0 |

`hhea` widerspiegelt d typografisch Oberlängi, Unterlängi und de Zileabstand. Rundi Forme händ 10–14 Einheite Überschwinge. D Vorbreitene variiered pro Master und werded in HVAR erfasst.

All vier Desktop-Schriftdateie bruuched installierbars Embedding mit `fsType=0`. Jedi benännti `fvar`-Instanz het en explizite PostScript-Name; jedi standardmässigi Regular-Instanz brucht name ID 6 nomal. S Release 1.0.1 het d interni Schriftversion `1.001`, damit Schrift-Caches es vom ursprüngliche Build unterscheide chönd. D Installationsfamilie sind `Lötschberg`, `Lötschberg Extruded` und `Lötschberg Text`; d primäri Farbschrift und d kompatibli Regular-Version teiled absichtlich `Lötschberg` und dörfed drum nöd gliichziitig installiert sii.

## Validierungsvertrag

De Build bricht ab, wenn e Glyph zwüsche Masters d Aazahl Konture, d Aazahl Pünkt, d Pünktreiefolg oder de Startpunkt änderet. Die Invariant gilt für d Basis, `.hand` und jedi Wand-, Schraffur-, Keyline- und Vordersite-Schicht, wo vo `.ext` und `.hand.ext` bruucht wird. D Quell-Prüefige verlanget zusätzlich ganzzahlig quantisierti Wänd, wo nöd zämefalled, und pro fixierti Gruppe siebe korrekt zentrierti, vierpünktigi Schraffure mit voller Dicki. D Tests vo de kompilierten Schrift verlanget, dass de Schraffur-`PaintComposite` `SRC_IN` gege die zwei aktuelle Wand-Paints brucht.

Vor em Release:

1. Füehr `uv run pytest` us und stell sicher, dass d Tests für Topologie, Achse, cmap, GSUB-Konvergenz, COLR/CPAL, STAT, Metrike und d Artefakt im Wurzelverzeichnis bestönd.
2. Füehr FontBakery `check-opentype` und `ots-sanitize` uf all vier Desktop-Schrifte us; bhalt d FontBakery-Bericht.
3. Prüef mit `hb-shape`, dass Basisglyph mit `ss01`, `ss02` und `ss01,ss02` in beide Feature-Reihefolge ersetzt werded.
4. Fixier und render d Achseextrem und benännte Instanze, inklusive `slnt=-12`, und vergliich d Waterfalls vo 8–144 px mit de Grid-Referenze und de Specimen-Fotografie.
5. Bestätig, dass d Aliasse `Loetschberg-VF.woff2`/`Loetschberg-VF.woff` im Wurzelverzeichnis in `index.html` laded, über all vier Achse variabel bliibed und COLRv1 in de aktuelle Versione vo Chrome, Firefox, macOS, Illustrator und InDesign renderet. De monochromi Fallback muess lesbar bliibe, wo COLRv1 nöd unterstützt wird.

D visuell Prüefig vergliicht d Formtreui mit de Grid-Renders und d Designabsicht mit de Specimen-Fotografie. Si darf d veraltete Specimen-Umriss nöd zur Build-Geometrie befördere.

## Release-Ergebnis

- `uv run pytest -q`: 37 Tests bestande, inklusive Quell- und Kompilat-Interpolationsprüefige für d dünne `R`-/`N`-/`1`-Verbindige, all 380 COLRv1-Paint-Graphs, beidi Kompatibilitätsfamilie und ihri `ss01`-Formig.
- Topologie-Bericht: 26 Masters, 3,147 prüefti Umriss-Signature über d Produktions-Farbschichte und d separate Extruded-Kompatibilitätsumriss, null Signaturabweichige und siebe Schraffure pro fixierti Gruppe.
- FontBakery 1.1.0: Primärschrift 46 bestande / 7 übersprunge / 0 fehlgschlage; CFF2-Sidecar 43 bestande / 10 übersprunge / 0 fehlgschlage; Regular-Kompatibilität 46 bestande / 7 übersprunge / 0 fehlgschlage; Extruded-Kompatibilität 43 bestande / 10 übersprunge / 0 fehlgschlage. Jedi Installationsfamilie wird absichtlich separat prüeft.
- OTS 9.2.0: All vier Desktop-Schrifte werded erfolgriich saniert.
- `varLib.interpolatable`: Kei fehlende oder offeni Pfad, kei Abweichige bi Pfad-, Chnote- oder Chnotetyp-Aazahl und kei Knick. De ufbewahrti JSON-Bericht enthaltet 616 Vorschläg für neui Startpünkt und 8 Vorschläg für e anderi Konturreiefolg, konzentriert uf wiederholti Farbschichtkonture und Vergliich zwüsche Display und Slant; das sind visuell Heuristike und kei Änderige a de fixierte Kontur- oder Chnotefolg.
- Chromium: D echte WOFF2 und de erzwungeni WOFF-Fallback laded; all vier Feature-Zueständ, d 25-Positione-Matrix für dünni Breiti/optischi Grössi und die bekannte `@`-/`t`-/`~`-Prüefige fürs Schraffur-Clipping renderet bi Desktop- und 390-px-Mobilgrössi suuber und ohni Überlauf im Specimen.
- Figma-Agent: Beidi installierte Kompatibilitätsfamilie werded mit all benännte Instanze und vier Variationsachse erkannt; de Font-Datei-Endpunkt liefert byte-identischi TTFs, und de SVG-Vorschau-Endpunkt rendert beidi standardmässige Regular-Schnitt erfolgriich.

Firefox, macOS, Illustrator und InDesign bliibed externi Prüefige vo de Release-Matrix, will die Laufziitumgebige i dere Build-Umgebig nöd verfügbar sind.
