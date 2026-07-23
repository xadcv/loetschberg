## FontBakery report

fontbakery version: 1.1.0







## Check results



<details><summary>[14] Loetschberg-VF[wght,wdth].ttf</summary>
<div>
<details>
    <summary>🔥 <b>FAIL</b> Check that format 12 cmap subtables are correctly constituted. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#cmap-format-12">cmap/format_12</a></summary>
    <div>







* 🔥 **FAIL** <p>A format 12 subtable did not contain any codepoints beyond the Basic Multilingual Plane (BMP)</p>
 [code: pointless-format-12]



</div>
</details>

<details>
    <summary>🔥 <b>FAIL</b> Checking OS/2 usWinAscent & usWinDescent. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#family-win-ascent-and-descent">family/win_ascent_and_descent</a></summary>
    <div>







* 🔥 **FAIL** <p>OS/2.usWinAscent value should be equal or greater than 1042, but got 960 instead</p>
 [code: ascent]



</div>
</details>

<details>
    <summary>🔥 <b>FAIL</b> Ensure glyphs do not have components which are themselves components. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#nested-components">nested_components</a></summary>
    <div>







* 🔥 **FAIL** <p>The following glyphs have components which themselves are component glyphs:
* Agrave.ext
* Aacute.ext
* Acircumflex.ext
* Atilde.ext
* Adieresis.ext
* Aring.ext
* Ccedilla.ext
* Egrave.ext
* Eacute.ext
* Ecircumflex.ext and 94 more.</p>
<p>Use -F or --full-lists to disable shortening of long lists.</p>
 [code: found-nested-components]



</div>
</details>

<details>
    <summary>🔥 <b>FAIL</b> Ensure font doesn't have Mac name table entries (platform=1). <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#no-mac-entries">no_mac_entries</a></summary>
    <div>







* 🔥 **FAIL** <p>Please remove name ID 1</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 2</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 3</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 4</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 5</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 6</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 16</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 17</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 25</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 283</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 284</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 285</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 286</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 287</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 288</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 289</p>
 [code: mac-names]



* 🔥 **FAIL** <p>Please remove name ID 290</p>
 [code: mac-names]



</div>
</details>

<details>
    <summary>🔥 <b>FAIL</b> Ensure smart dropout control is enabled in "prep" table instructions. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#smart-dropout">smart_dropout</a></summary>
    <div>







* 🔥 **FAIL** <p>The 'prep' table does not contain TrueType instructions enabling smart dropout control. To fix, export the font with autohinting enabled, or run ttfautohint on the font, or run the <code>gftools fix-nonhinting</code> script.</p>
 [code: lacks-smart-dropout]



</div>
</details>

<details>
    <summary>⚠️ <b>WARN</b> Ensure files are not too large. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#file-size">file_size</a></summary>
    <div>







* ⚠️ **WARN** <p>Font file is 7.4Mb; ideally it should be less than 1.0Mb</p>
 [code: large-font]



</div>
</details>

<details>
    <summary>⚠️ <b>WARN</b> Detect any interpolation issues in the font. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#interpolation-issues">interpolation_issues</a></summary>
    <div>







* ⚠️ **WARN** <p>Interpolation issues were found in the font:</p>
<pre><code>- Contour 0 start point differs in glyph 'comma.hand.ext.keyline' between location wght=400,wdth=100 and location wght=400,wdth=75

- Contour 1 start point differs in glyph 'comma.hand.ext.keyline' between location wght=400,wdth=100 and location wght=400,wdth=75

- Contour 1 start point differs in glyph 'x.hand.ext.keyline' between location wght=900,wdth=75 and location wght=100,wdth=125

- Contour 3 start point differs in glyph 'x.hand.ext.keyline' between location wght=900,wdth=75 and location wght=100,wdth=125

- Contour 0 start point differs in glyph 'Y.hand.ext.face' between location wght=900,wdth=75 and location wght=100,wdth=125

- Contour 0 start point differs in glyph 'x.hand.ext.face' between location wght=900,wdth=75 and location wght=100,wdth=125

- Contour 1 start point differs in glyph 'x.hand.ext.face' between location wght=900,wdth=75 and location wght=100,wdth=125

- Contour 9 start point differs in glyph 'percent.ext.keyline' between location wght=900,wdth=75 and location wght=100,wdth=125

- Contour 0 start point differs in glyph 'yen.ext.face' between location wght=900,wdth=75 and location wght=100,wdth=125

- Contour 5 start point differs in glyph 'four.ext.keyline' between location wght=900,wdth=75 and location wght=100,wdth=125

- 152 more.
</code></pre>
<p>Use -F or --full-lists to disable shortening of long lists.</p>
 [code: interpolation-issues]



</div>
</details>

<details>
    <summary>⚠️ <b>WARN</b> Ensure variable fonts include an avar table. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#mandatory-avar-table">mandatory_avar_table</a></summary>
    <div>







* ⚠️ **WARN** <p>This variable font does not have an avar table. Most variable fonts should include an avar table to correctly define axes progression rates.</p>
 [code: missing-avar]



</div>
</details>

<details>
    <summary>⚠️ <b>WARN</b> Check math signs have the same width. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#math-signs-width">math_signs_width</a></summary>
    <div>







* ⚠️ **WARN** <p>The most common width is 636 among a set of 4 math glyphs.
The following math glyphs have a different width, though:</p>
<p>Width = 700:
less, greater</p>
<p>Width = 656:
logicalnot</p>
<p>Width = 546:
multiply</p>
 [code: width-outliers]



</div>
</details>

<details>
    <summary>⚠️ <b>WARN</b> Check there are no overlapping path segments <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#overlapping-path-segments">overlapping_path_segments</a></summary>
    <div>







* ⚠️ **WARN** <p>The following glyphs have overlapping path segments:</p>
<pre><code>* dollar (U+0024): L&lt;&lt;296.0,596.0&gt;--&lt;296.0,617.0&gt;&gt; has the same coordinates as a previous segment.

* dollar (U+0024): L&lt;&lt;296.0,617.0&gt;--&lt;296.0,638.0&gt;&gt; has the same coordinates as a previous segment.

* dollar (U+0024): L&lt;&lt;296.0,638.0&gt;--&lt;296.0,658.0&gt;&gt; has the same coordinates as a previous segment.

* dollar (U+0024): L&lt;&lt;296.0,658.0&gt;--&lt;296.0,679.0&gt;&gt; has the same coordinates as a previous segment.

* dollar (U+0024): L&lt;&lt;296.0,679.0&gt;--&lt;296.0,700.0&gt;&gt; has the same coordinates as a previous segment.

* dollar (U+0024): L&lt;&lt;296.0,407.0&gt;--&lt;296.0,386.0&gt;&gt; has the same coordinates as a previous segment.

* dollar (U+0024): L&lt;&lt;296.0,386.0&gt;--&lt;296.0,365.0&gt;&gt; has the same coordinates as a previous segment.

* dollar (U+0024): L&lt;&lt;296.0,365.0&gt;--&lt;296.0,345.0&gt;&gt; has the same coordinates as a previous segment.

* dollar (U+0024): L&lt;&lt;296.0,345.0&gt;--&lt;296.0,324.0&gt;&gt; has the same coordinates as a previous segment.

* dollar (U+0024): L&lt;&lt;296.0,324.0&gt;--&lt;296.0,303.0&gt;&gt; has the same coordinates as a previous segment.

* 3659 more.
</code></pre>
<p>Use -F or --full-lists to disable shortening of long lists.</p>
 [code: overlapping-path-segments]



</div>
</details>

<details>
    <summary>⚠️ <b>WARN</b> Does the font contain a soft hyphen? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#soft-hyphen">soft_hyphen</a></summary>
    <div>







* ⚠️ **WARN** <p>This font has a 'Soft Hyphen' character.</p>
 [code: softhyphen]



</div>
</details>

<details>
    <summary>⚠️ <b>WARN</b> Checking that the typoAscender exceeds the yMax of the /Agrave. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#typoascender-exceeds-Agrave">typoascender_exceeds_Agrave</a></summary>
    <div>







* ⚠️ **WARN** <p>OS/2.sTypoAscender value should be greater than 987, but got 960 instead</p>
 [code: typoAscender]



</div>
</details>

<details>
    <summary>⚠️ <b>WARN</b> Check font contains no unreachable glyphs <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#unreachable-glyphs">unreachable_glyphs</a></summary>
    <div>







* ⚠️ **WARN** <p>The following glyphs could not be reached by codepoint or substitution rules:</p>
<pre><code>- A.ext.hatch

- A.hand.ext.hatch

- AE.ext.hatch

- AE.hand.ext.hatch

- Aacute.ext.hatch

- Aacute.hand.ext.hatch

- Acircumflex.ext.hatch

- Acircumflex.hand.ext.hatch

- Adieresis.ext.hatch

- Adieresis.hand.ext.hatch

- 370 more.
</code></pre>
<p>Use -F or --full-lists to disable shortening of long lists.</p>
 [code: unreachable-glyphs]



</div>
</details>

<details>
    <summary>⚠️ <b>WARN</b> Glyph names are all valid? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/universal.html#valid-glyphnames">valid_glyphnames</a></summary>
    <div>







* ⚠️ **WARN** <p>The following glyph names may be too long for some legacy systems which may expect a maximum 31-characters length limit:
_mark.iacute.dotlessi.acute.hand, _mark.icircumflex.dotlessi.circ.hand, _mark.idieresis.dotlessi.dier.hand, _mark.igrave.dotlessi.grave.hand, bracketright.hand.ext.wallBronze, guillemotleft.hand.ext.wallBronze, guillemotright.hand.ext.wallBronze, guillemotright.hand.ext.wallDark, ordmasculine.hand.ext.wallBronze, periodcentered.hand.ext.wallBronze and 3 more.</p>
<p>Use -F or --full-lists to disable shortening of long lists.</p>
 [code: legacy-long-names]



</div>
</details>
</div>
</details>




### Summary

| 💥 ERROR | ☠ FATAL | 🔥 FAIL | ⚠️ WARN | ⏩ SKIP | ℹ️ INFO | ✅ PASS | 🔎 DEBUG | 
| ---|---|---|---|---|---|---|---|
| 0 | 0 | 5 | 9 | 22 | 3 | 88 | 0 | 
| 0% | 0% | 4% | 7% | 17% | 2% | 69% | 0% | 



**Note:** The following loglevels were omitted in this report:


* SKIP
* INFO
* PASS
* DEBUG
