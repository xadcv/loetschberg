## FontBakery report

fontbakery version: 1.1.0







## Check results



<details><summary>[45] Loetschberg-VF[wght,wdth,opsz,slnt].ttf</summary>
<div>
<details>
    <summary>✅ <b>PASS</b> Check code page character ranges <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-code-pages">opentype/code_pages</a></summary>
    <div>


>
> At least some programs (such as Word and Sublime Text) under Windows 7
> do not recognize fonts unless code page bits are properly set on the
> ulCodePageRange1 (and/or ulCodePageRange2) fields of the OS/2 table.
>
> More specifically, the fonts are selectable in the font menu, but whichever
> Windows API these applications use considers them unsuitable for any
> character set, so anything set in these fonts is rendered with Arial as a
> fallback font.
>
> This check currently does not identify which code pages should be set.
> Auto-detecting coverage is not trivial since the OpenType specification
> leaves the interpretation of whether a given code page is "functional"
> or not open to the font developer to decide.
>
> So here we simply detect as a FAIL when a given font has no code page
> declared at all.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/2474





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> The font should not need a DSIG table anymore. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-dsig">opentype/dsig</a></summary>
    <div>


>
> Microsoft Office 2013 and below products expect fonts to have a digital
> signature declared in a DSIG table in order to implement OpenType features.
> The EOL date for Microsoft Office 2013 products was 4/11/2023.
>
> This issue does not impact Microsoft Office 2016 and above products. It is now considered better to completely remove the table.
>
> But if you still want your font to support OpenType features on Office 2013,
> then you may find it handy to add a fake signature on a placeholder DSIG table
> by running one of the helper scripts provided at
> https://github.com/googlefonts/gftools
>
> Reference: https://github.com/fonttools/fontbakery/issues/1845
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/3398
> See also: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Font follows the family naming recommendations? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-family-naming-recommendations">opentype/family_naming_recommendations</a></summary>
    <div>


>
> This check ensures that the length of various family name and style
> name strings in the name table are within the maximum length
> recommended by the OpenType specification.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Checking font version fields (head and name table). <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-font-version">opentype/font_version</a></summary>
    <div>


>
> The OpenType specification provides for two fields which contain
> the version number of the font: fontRevision in the head table,
> and nameID 5 in the name table. If these fields do not match,
> different applications will report different version numbers for
> the font.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Checking OS/2 fsSelection value. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-fsselection">opentype/fsselection</a></summary>
    <div>


>
> The OS/2.fsSelection field is a bit field used to specify the stylistic
> qualities of the font - in particular, it specifies to some operating
> systems whether the font is italic (bit 0), bold (bit 5) or regular
> (bit 6).
>
> This check verifies that the fsSelection field is set correctly for the
> font style. For a family of static fonts created in GlyphsApp, this is
> set by using the style linking checkboxes in the exports settings.
>
> Additionally, the bold and italic bits in OS/2.fsSelection must match the
> bold and italic bits in head.macStyle per the OpenType spec.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829
> See also: https://github.com/fonttools/fontbakery/pull/2382





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Axes and named instances fall within correct ranges? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-fvar-axis-ranges-correct">opentype/fvar/axis_ranges_correct</a></summary>
    <div>


>
> According to the OpenType spec's registered design-variation tags, instances in
> a variable font should have certain prescribed values.
> If a variable font has a 'wght' (Weight) axis, the valid coordinate range is 1-1000.
> If a variable font has a 'wdth' (Width) axis, the valid numeric range is strictly greater than zero.
> If a variable font has a 'slnt' (Slant) axis, then the coordinate of its 'Regular' instance is required to be 0.
> If a variable font has a 'ital' (Slant) axis, then the coordinate of its 'Regular' instance is required to be 0.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/2264
> See also: https://github.com/fonttools/fontbakery/pull/2520
> See also: https://github.com/fonttools/fontbakery/issues/2572





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Check hhea.caretSlopeRise and hhea.caretSlopeRun <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-caret-slope">opentype/caret_slope</a></summary>
    <div>


>
> Checks whether hhea.caretSlopeRise and hhea.caretSlopeRun
> match with post.italicAngle.
>
> For Upright fonts, you can set hhea.caretSlopeRise to 1
> and hhea.caretSlopeRun to 0.
>
> For Italic fonts, you can set hhea.caretSlopeRise to head.unitsPerEm
> and calculate hhea.caretSlopeRun like this:
> round(math.tan(
> math.radians(-1 * font["post"].italicAngle)) * font["head"].unitsPerEm)
>
> This check allows for a 0.1° rounding difference between the Italic angle
> as calculated by the caret slope and post.italicAngle
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/3670





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Axes and named instances fall within correct ranges? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-fvar-regular-coords-correct">opentype/fvar/regular_coords_correct</a></summary>
    <div>


>
> According to the Open-Type spec's registered design-variation tags,instances in a variable font should have certain prescribed values.
> If a variable font has a 'wght' (Weight) axis, the valid coordinate range is 1-1000.
> If a variable font has a 'wdth' (Width) axis, the valid numeric range is strictly greater than zero.
> If a variable font has a 'slnt' (Slant) axis, then the coordinate of its 'Regular' instance is required to be 0.
> If a variable font has a 'ital' (Slant) axis, then the coordinate of its 'Regular' instance is required to be 0.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/1707
> See also: https://github.com/fonttools/fontbakery/issues/2572





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Check mark characters are in GDEF mark glyph class. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-gdef-mark-chars">opentype/gdef_mark_chars</a></summary>
    <div>


>
> Mark characters should be in the GDEF mark glyph class.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/2877





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Check GDEF mark glyph class doesn't have characters that are not marks. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-gdef-non-mark-chars">opentype/gdef_non_mark_chars</a></summary>
    <div>


>
> Glyphs in the GDEF mark glyph class become non-spacing and may be repositioned
> if they have mark anchors.
>
> Only combining mark glyphs should be in that class. Any non-mark glyph
> must not be in that class, in particular spacing glyphs.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/2877





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Check glyphs in mark glyph class are non-spacing. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-gdef-spacing-marks">opentype/gdef_spacing_marks</a></summary>
    <div>


>
> Glyphs in the GDEF mark glyph class should be non-spacing.
>
> Spacing glyphs in the GDEF mark glyph class may have incorrect anchor
> positioning that was only intended for building composite glyphs during design.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/2877





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Check glyphs do not have duplicate components which have the same x,y coordinates. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-glyf-non-transformed-duplicate-components">opentype/glyf_non_transformed_duplicate_components</a></summary>
    <div>


>
> There have been cases in which fonts had faulty double quote marks, with each
> of them containing two single quote marks as components with the same
> x, y coordinates which makes them visually look like single quote marks.
>
> This check ensures that glyphs do not contain duplicate components
> which have the same x,y coordinates.
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/2709





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Is there any unused data at the end of the glyf table? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-glyf-unused-data">opentype/glyf_unused_data</a></summary>
    <div>


>
> This check validates the structural integrity of the glyf table,
> by checking that all glyphs referenced in the loca table are
> actually present in the glyf table and that there is no unused
> data at the end of the glyf table. A failure here indicates a
> problem with the font compiler.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>There is no unused data at the end of the glyf table.</p>




</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Is there a usable "kern" table declared in the font? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-kern-table">opentype/kern_table</a></summary>
    <div>


>
> Even though all fonts should have their kerning implemented in the GPOS table,
> there may be kerning info at the kern table as well.
>
> Some applications such as MS PowerPoint require kerning info on the kern table.
> More specifically, they require a format 0 kern subtable from a kern table
> version 0 with only glyphs defined in the cmap table, which is the only one
> that Windows understands (and which is also the simplest and more limited
> of all the kern subtables).
>
> Google Fonts ingests fonts made for download and use on desktops, and does
> all web font optimizations in the serving pipeline (using libre libraries
> that anyone can replicate.)
>
> Ideally, TTFs intended for desktop users (and thus the ones intended for
> Google Fonts) should have both KERN and GPOS tables.
>
> Given all of the above, we currently treat kerning on a v0 kern table
> as a good-to-have (but optional) feature.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/1675
> See also: https://github.com/fonttools/fontbakery/issues/3148
> See also: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>Font does not declare an optional &quot;kern&quot; table.</p>




</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Does the font have any invalid feature tags? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-layout-valid-feature-tags">opentype/layout_valid_feature_tags</a></summary>
    <div>


>
> Incorrect tags can be indications of typos, leftover debugging code or
> questionable approaches, or user error in the font editor. Such typos can
> cause features and language support to fail to work as intended.
>
> Font vendors may use private tags to identify private features. These tags
> must be four uppercase letters (A-Z) with no punctuation, spaces, or numbers.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/3355





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Does the font have any invalid language tags? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-layout-valid-language-tags">opentype/layout_valid_language_tags</a></summary>
    <div>


>
> Incorrect language tags can be indications of typos, leftover debugging code
> or questionable approaches, or user error in the font editor. Such typos can
> cause features and language support to fail to work as intended.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/3355





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Does the font have any invalid script tags? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-layout-valid-script-tags">opentype/layout_valid_script_tags</a></summary>
    <div>


>
> Incorrect script tags can be indications of typos, leftover debugging code
> or questionable approaches, or user error in the font editor. Such typos can
> cause features and language support to fail to work as intended.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/3355





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Does the number of glyphs in the loca table match the maxp table? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-loca-maxp-num-glyphs">opentype/loca/maxp_num_glyphs</a></summary>
    <div>


>
> The 'maxp' table contains various statistics about the font, including the
> number of glyphs in the font. The 'loca' table contains the offsets to the
> locations of the glyphs in the font. The number of offsets in the 'loca' table
> should match the number of glyphs in the 'maxp' table. A failure here indicates
> a problem with the font compiler.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Checking head.macStyle value. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-mac-style">opentype/mac_style</a></summary>
    <div>


>
> The values of the flags on the macStyle entry on the 'head' OpenType table
> that describe whether a font is bold and/or italic must be coherent with the
> actual style of the font as inferred by its filename.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>head macStyle ITALIC bit is properly set.</p>




* ✅ **PASS** <p>head macStyle BOLD bit is properly set.</p>




</div>
</details>

<details>
    <summary>✅ <b>PASS</b> MaxAdvanceWidth is consistent with values in the Hmtx and Hhea tables? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-maxadvancewidth">opentype/maxadvancewidth</a></summary>
    <div>


>
> The 'hhea' table contains a field which specifies the maximum
> advance width. This value should be consistent with the maximum
> advance width of all glyphs specified in the 'hmtx' table.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Checking correctness of monospaced metadata. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-monospace">opentype/monospace</a></summary>
    <div>


>
> There are various metadata in the OpenType spec to specify if a font is
> monospaced or not. If the font is not truly monospaced, then no monospaced
> metadata should be set (as sometimes they mistakenly are...)
>
> Requirements for monospace fonts:
>
> * post.isFixedPitch - "Set to 0 if the font is proportionally spaced,
> non-zero if the font is not proportionally spaced (monospaced)"
> (https://www.microsoft.com/typography/otspec/post.htm)
>
> * hhea.advanceWidthMax must be correct, meaning no glyph's width value
> is greater. (https://www.microsoft.com/typography/otspec/hhea.htm)
>
> * OS/2.panose.bProportion must be set to 9 (monospace) on latin text fonts.
>
> * OS/2.panose.bSpacing must be set to 3 (monospace) on latin hand written
> or latin symbol fonts.
>
> * Spec says: "The PANOSE definition contains ten digits each of which currently
> describes up to sixteen variations. Windows uses bFamilyType, bSerifStyle
> and bProportion in the font mapper to determine family type. It also uses
> bProportion to determine if the font is monospaced."
> (https://www.microsoft.com/typography/otspec/os2.htm#pan
> https://monotypecom-test.monotype.de/services/pan2)
>
> * OS/2.xAvgCharWidth must be set accurately.
> "OS/2.xAvgCharWidth is used when rendering monospaced fonts,
> at least by Windows GDI"
> (http://typedrawers.com/discussion/comment/15397/#Comment_15397)
>
> Also we should report an error for glyphs not of average width.
>
>
> Please also note:
>
> Thomas Phinney told us that a few years ago (as of December 2019), if you gave
> a font a monospace flag in Panose, Microsoft Word would ignore the actual
> advance widths and treat it as monospaced.
>
> Source: https://typedrawers.com/discussion/comment/45140/#Comment_45140
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>Font is not monospaced and all related metadata look good.</p>
 [code: good]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Check name table for empty records. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-name-empty-records">opentype/name/empty_records</a></summary>
    <div>


>
> Check the name table for empty records,
> as this can cause problems in Adobe apps.
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/2369





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Does full font name begin with the font family name? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-name-match-familyname-fullfont">opentype/name/match_familyname_fullfont</a></summary>
    <div>


>
> The FULL_FONT_NAME entry in the ‘name’ table should start with the same string
> as the Family Name (FONT_FAMILY_NAME, TYPOGRAPHIC_FAMILY_NAME or
> WWS_FAMILY_NAME).
>
> If the Family Name is not included as the first part of the Full Font Name, and
> the user embeds the font in a document using a Microsoft Office app, the app
> will fail to render the font when it opens the document again.
>
> NOTE: Up until version 1.5, the OpenType spec included the following exception
> in the definition of Full Font Name:
>
> "An exception to the [above] definition of Full font name is for Microsoft
> platform strings for CFF OpenType fonts: in this case, the Full font name
> string must be identical to the PostScript FontName in the CFF Name INDEX."
>
> https://docs.microsoft.com/en-us/typography/opentype/otspec150/name#name-ids
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Name table ID 6 (PostScript name) must be consistent across platforms. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-name-postscript-name-consistency">opentype/name/postscript_name_consistency</a></summary>
    <div>


>
> The PostScript name entries in the font's 'name' table should be
> consistent across platforms.
>
> This is the TTF/CFF2 equivalent of the CFF 'name/postscript_vs_cff' check.
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/2394





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> PostScript name follows OpenType specification requirements? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-postscript-name">opentype/postscript_name</a></summary>
    <div>


>
> The PostScript name is used by some applications to identify the font.
> It should only consist of characters from the set A-Z, a-z, 0-9, and hyphen.
>
>




> Original proposal: https://github.com/miguelsousa/openbakery/issues/62





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Font has correct post table version? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-post-table-version">opentype/post_table_version</a></summary>
    <div>


>
> Format 2.5 of the 'post' table was deprecated in OpenType 1.3 and
> should not be used.
>
> According to Thomas Phinney, the possible problem with post format 3
> is that under the right combination of circumstances, one can generate
> PDF from a font with a post format 3 table, and not have accurate backing
> store for any text that has non-default glyphs for a given codepoint.
>
> It will look fine but not be searchable. This can affect Latin text with
> high-end typography, and some complex script writing systems, especially
> with higher-quality fonts. Those circumstances generally involve creating
> a PDF by first printing a PostScript stream to disk, and then creating a
> PDF from that stream without reference to the original source document.
> There are some workflows where this applies,but these are not common
> use cases.
>
> Apple recommends against use of post format version 4 as "no longer
> necessary and should be avoided". Please see the Apple TrueType reference
> documentation for additional details.
>
> https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6post.html
>
> Acceptable post format versions are 2 and 3 for TTF and OTF CFF2 builds,
> and post format 3 for CFF builds.
>




> Original proposal: https://github.com/google/fonts/issues/215
> See also: https://github.com/fonttools/fontbakery/issues/2638
> See also: https://github.com/fonttools/fontbakery/issues/3635
> See also: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>Font has an acceptable post format 2.0 table version.</p>




</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Checking direction of slnt axis angles. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-slant-direction">opentype/slant_direction</a></summary>
    <div>


>
> The 'slnt' axis values are defined as negative values for a clockwise (right)
> lean, and positive values for counter-clockwise lean. This is counter-intuitive
> for many designers who are used to think of a positive slant as a lean to
> the right.
>
> This check ensures that the slant axis direction is consistent with the specs.
>
> https://docs.microsoft.com/en-us/typography/opentype/spec/dvaraxistag_slnt
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/3910





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Checking unitsPerEm value is reasonable. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-unitsperem">opentype/unitsperem</a></summary>
    <div>


>
> According to the OpenType spec:
>
> The value of unitsPerEm at the head table must be a value
> between 16 and 16384. Any value in this range is valid.
>
> In fonts that have TrueType outlines, a power of 2 is recommended
> as this allows performance optimizations in some rasterizers.
>
> But 1000 is a commonly used value. And 2000 may become
> increasingly more common on Variable Fonts.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Are there unwanted Apple tables? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-unwanted-aat-tables">opentype/unwanted_aat_tables</a></summary>
    <div>


>
> Apple's TrueType reference manual [1] describes SFNT tables not in the
> Microsoft OpenType specification [2] and these can sometimes sneak into final
> release files.
>
> This check ensures fonts only have OpenType tables.
>
> [1] https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6.html
> [2] https://docs.microsoft.com/en-us/typography/opentype/spec/
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/2190





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Validates that all of the instance records in a given font have distinct data. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-varfont-distinct-instance-records">opentype/varfont/distinct_instance_records</a></summary>
    <div>


>
> According to the 'fvar' documentation in OpenType spec v1.9
> https://docs.microsoft.com/en-us/typography/opentype/spec/fvar
>
> All of the instance records in a font should have distinct coordinates
> and distinct subfamilyNameID and postScriptName ID values. If two or more
> records share the same coordinates, the same nameID values or the same
> postScriptNameID values, then all but the first can be ignored.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/3706





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Validate foundry-defined design-variation axis tag names. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-varfont-foundry-defined-tag-name">opentype/varfont/foundry_defined_tag_name</a></summary>
    <div>


>
> According to the OpenType spec's syntactic requirements for
> foundry-defined design-variation axis tags available at
> https://learn.microsoft.com/en-us/typography/opentype/spec/dvaraxisreg
>
> Foundry-defined tags must begin with an uppercase letter
> and must use only uppercase letters or digits.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4043





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Validates that all of the instance records in a given font have the same size. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-varfont-same-size-instance-records">opentype/varfont/same_size_instance_records</a></summary>
    <div>


>
> According to the 'fvar' documentation in OpenType spec v1.9
> https://docs.microsoft.com/en-us/typography/opentype/spec/fvar
>
> All of the instance records in a given font must be the same size, with
> all either including or omitting the postScriptNameID field. [...]
> If the value is 0xFFFF, then the value is ignored, and no PostScript name
> equivalent is provided for the instance.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/3705





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> All fvar axes have a correspondent Axis Record on STAT table? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-varfont-STAT-axis-record-for-each-axis">opentype/varfont/STAT_axis_record_for_each_axis</a></summary>
    <div>


>
> According to the OpenType spec, there must be an Axis Record
> for every axis defined in the fvar table.
>
> https://docs.microsoft.com/en-us/typography/opentype/spec/stat#axis-records
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/3017





* ✅ **PASS** <p>STAT table has all necessary Axis Records.</p>




</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Validates subfamilyNameID and postScriptNameID for the default instance record <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-varfont-valid-default-instance-nameids">opentype/varfont/valid_default_instance_nameids</a></summary>
    <div>


>
> According to the 'fvar' documentation in OpenType spec v1.9.1
> https://docs.microsoft.com/en-us/typography/opentype/spec/fvar
>
> The default instance of a font is that instance for which the coordinate
> value of each axis is the defaultValue specified in the corresponding
> variation axis record. An instance record is not required for the default
> instance, though an instance record can be provided. When enumerating named
> instances, the default instance should be enumerated even if there is no
> corresponding instance record. If an instance record is included for the
> default instance (that is, an instance record has coordinates set to default
> values), then the nameID value should be set to either 2 or 17 or to a
> name ID with the same value as name ID 2 or 17. Also, if a postScriptNameID is
> included in instance records, and the postScriptNameID value should be set
> to 6 or to a name ID with the same value as name ID 6.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/3708





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Validates that all of the name IDs in an instance record are within the correct range <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-varfont-valid-nameids">opentype/varfont/valid_nameids</a></summary>
    <div>


>
> According to the 'fvar' documentation in OpenType spec v1.9
> https://docs.microsoft.com/en-us/typography/opentype/spec/fvar
>
> The axisNameID field provides a name ID that can be used to obtain strings
> from the 'name' table that can be used to refer to the axis in application
> user interfaces. The name ID must be greater than 255 and less than 32768.
>
> The postScriptNameID field provides a name ID that can be used to obtain
> strings from the 'name' table that can be treated as equivalent to name
> ID 6 (PostScript name) strings for the given instance. Values of 6 and
> "undefined" can be used; otherwise, values must be greater than 255 and
> less than 32768.
>
> The subfamilyNameID field provides a name ID that can be used to obtain
> strings from the 'name' table that can be treated as equivalent to name
> ID 17 (typographic subfamily) strings for the given instance. Values of
> 2 or 17 can be used; otherwise, values must be greater than 255 and less
> than 32768.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/3702
> See also: https://github.com/fonttools/fontbakery/issues/3703





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Checking if OS/2 usWeightClass matches fvar. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-weight-class-fvar">opentype/weight_class_fvar</a></summary>
    <div>


>
> According to Microsoft's OT Spec the OS/2 usWeightClass
> should match the fvar default value.
>




> Original proposal: https://github.com/googlefonts/gftools/issues/477





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Check if OS/2 xAvgCharWidth is correct. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-xavgcharwidth">opentype/xavgcharwidth</a></summary>
    <div>


>
> The OS/2.xAvgCharWidth field is used to calculate the width of a string of
> characters. It is the average width of all non-zero width glyphs in the font.
>
> This check ensures that the value is correct. A failure here may indicate
> a bug in the font compiler, rather than something that the designer can
> do anything about.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>OS/2 xAvgCharWidth value is correct.</p>




</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Check for points out of bounds. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-points-out-of-bounds">opentype/points_out_of_bounds</a></summary>
    <div>


>
> The glyf table specifies a bounding box for each glyph. This check
> ensures that all points in all glyph paths are within the bounding
> box. Glyphs with out-of-bounds points can cause rendering issues in
> some software, and should be corrected.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/735





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Checking post.italicAngle value. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-italic-angle">opentype/italic_angle</a></summary>
    <div>


>
> The 'post' table italicAngle property should be a reasonable amount, likely
> not more than 30°. Note that in the OpenType specification, the value is
> negative for a rightward lean.
>
> https://docs.microsoft.com/en-us/typography/opentype/spec/post
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>Value of post.italicAngle is 0.0 with style=&quot;Regular&quot;.</p>




</div>
</details>

<details>
    <summary>⏩ <b>SKIP</b> Is the CFF2 subr/gsubr call depth > 10? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-cff2-call-depth">opentype/cff2_call_depth</a></summary>
    <div>


>
> Per "The CFF2 CharString Format", the "Subr nesting, stack limit" is 10.
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/2425





* ⏩ **SKIP** <p>Unfulfilled Conditions: is_cff2</p>
 [code: unfulfilled-conditions]



</div>
</details>

<details>
    <summary>⏩ <b>SKIP</b> Does the font use deprecated CFF operators or operations? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-cff-deprecated-operators">opentype/cff_deprecated_operators</a></summary>
    <div>


>
> The 'dotsection' operator and the use of 'endchar' to build accented characters
> from the Adobe Standard Encoding Character Set ("seac") are deprecated in CFF.
> Adobe recommends repairing any fonts that use these, especially endchar-as-seac,
> because a rendering issue was discovered in Microsoft Word with a font that
> makes use of this operation. The check treats that usage as a FAIL.
> There are no known ill effects of using dotsection, so that check is a WARN.
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/3033





* ⏩ **SKIP** <p>Unfulfilled Conditions: is_cff</p>
 [code: unfulfilled-conditions]



</div>
</details>

<details>
    <summary>⏩ <b>SKIP</b> Is the CFF subr/gsubr call depth > 10? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-cff-call-depth">opentype/cff_call_depth</a></summary>
    <div>


>
> Per "The Type 2 Charstring Format, Technical Note #5177",
> the "Subr nesting, stack limit" is 10.
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/2425





* ⏩ **SKIP** <p>Unfulfilled Conditions: is_cff</p>
 [code: unfulfilled-conditions]



</div>
</details>

<details>
    <summary>⏩ <b>SKIP</b> CFF table FontName must match name table ID 6 (PostScript name). <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-name-postscript-vs-cff">opentype/name/postscript_vs_cff</a></summary>
    <div>


>
> The PostScript name entries in the font's 'name' table should match
> the FontName string in the 'CFF ' table.
>
> The 'CFF ' table has a lot of information that is duplicated in other tables.
> This information should be consistent across tables, because there's
> no guarantee which table an app will get the data from.
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/2229





* ⏩ **SKIP** <p>Unfulfilled Conditions: is_cff</p>
 [code: unfulfilled-conditions]



</div>
</details>

<details>
    <summary>⏩ <b>SKIP</b> Checking OS/2 achVendID against configuration. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-vendor-id">opentype/vendor_id</a></summary>
    <div>


>
> When a font project's Vendor ID is specified explicitly on FontBakery's
> configuration file, all binaries must have a matching vendor identifier
> value in the OS/2 table.
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/3941





* ⏩ **SKIP** <p>Add the <code>vendor_id</code> key to a <code>fontbakery.yaml</code> file on your font project directory to enable this check.
You'll also need to use the <code>--configuration</code> flag when invoking fontbakery.</p>




</div>
</details>

<details>
    <summary>⏩ <b>SKIP</b> Does the font's CFF table top dict strings fit into the ASCII range? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-cff-ascii-strings">opentype/cff_ascii_strings</a></summary>
    <div>


>
> All CFF Table top dict string chars should fit into the ASCII range.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4619





* ⏩ **SKIP** <p>Unfulfilled Conditions: is_cff</p>
 [code: unfulfilled-conditions]



</div>
</details>
</div>
</details>

<details><summary>[8] Family checks</summary>
<div>
<details>
    <summary>✅ <b>PASS</b> Check that OS/2.fsSelection bold & italic settings are unique for each NameID1 <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-family-bold-italic-unique-for-nameid1">opentype/family/bold_italic_unique_for_nameid1</a></summary>
    <div>


>
> Per the OpenType spec: name ID 1 'is used in combination with Font Subfamily
> name (name ID 2), and should be shared among at most four fonts that differ
> only in weight or style.
>
> This four-way distinction should also be reflected in the OS/2.fsSelection
> field, using bits 0 and 5.
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/2388





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Verify that family names in the name table are consistent across all fonts in the family. Checks Typographic Family name (nameID 16) if present, otherwise uses Font Family name (nameID 1) <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-family-consistent-family-name">opentype/family/consistent_family_name</a></summary>
    <div>


>
> Per the OpenType spec:
>
> * "...many existing applications that use this pair of names assume that a
> Font Family name is shared by at most four fonts that form a font
> style-linking group"
>
> * "For extended typographic families that includes fonts other than the
> four basic styles(regular, italic, bold, bold italic), it is strongly
> recommended that name IDs 16 and 17 be used in fonts to create an
> extended, typographic grouping."
>
> * "If name ID 16 is absent, then name ID 1 is considered to be the
> typographic family name."
>
> https://learn.microsoft.com/en-us/typography/opentype/spec/name
>
> Fonts within a font family all must have consistent names
> in the Typographic Family name (nameID 16)
> or Font Family name (nameID 1), depending on which it uses.
>
> Inconsistent font/typographic family names across fonts in a family
> can result in unexpected behaviors, such as broken style linking.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4112





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Make sure all font files have the same version value. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-family-equal-font-versions">opentype/family/equal_font_versions</a></summary>
    <div>


>
> Within a family released at the same time, all members of the family
> should have the same version number in the head table.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Verify that each group of fonts with the same nameID 1 has maximum of 4 fonts. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-family-max-4-fonts-per-family-name">opentype/family/max_4_fonts_per_family_name</a></summary>
    <div>


>
> Per the OpenType spec:
>
> 'The Font Family name [...] should be shared among at most four fonts that
> differ only in weight or style [...]'
>




> Original proposal: https://github.com/fonttools/fontbakery/pull/2372





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Fonts have consistent PANOSE family type? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-family-panose-familytype">opentype/family/panose_familytype</a></summary>
    <div>


>
> The [PANOSE value](https://monotype.github.io/panose/) in the OS/2 table is a
> way of classifying a font based on its visual appearance and characteristics.
>
> The first field in the PANOSE classification is the family type: 2 means Latin
> Text, 3 means Latin Script, 4 means Latin Decorative, 5 means Latin Symbol.
> This check ensures that within a family, all fonts have the same family type.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Fonts have consistent underline thickness? <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-family-underline-thickness">opentype/family/underline_thickness</a></summary>
    <div>


>
> Dave C Lemon (Adobe Type Team) recommends setting the underline thickness to be
> consistent across the family.
>
> If thicknesses are not family consistent, words set on the same line which have
> different styles look strange.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4829





* ✅ **PASS** <p>Fonts have consistent underline thickness.</p>




</div>
</details>

<details>
    <summary>✅ <b>PASS</b> Check that family axis ranges are indentical <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-varfont-family-axis-ranges">opentype/varfont/family_axis_ranges</a></summary>
    <div>


>
> Between members of a family (such as Roman & Italic),
> the ranges of variable axes must be identical.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/4445





* ✅ **PASS** <p>All looks good!</p>
 [code: ok]



</div>
</details>

<details>
    <summary>⏩ <b>SKIP</b> Ensure VFs have 'ital' STAT axis. <a href="https://fontbakery.readthedocs.io/en/stable/fontbakery/checks/opentype.html#opentype-STAT-ital-axis">opentype/STAT/ital_axis</a></summary>
    <div>


>
> Check that related Upright and Italic VFs have an
> 'ital' axis in the STAT table.
>
> Since the STAT table can be used to create new instances, it is
> important to ensure that such an 'ital' axis be the last one
> declared in the STAT table so that the eventual naming of new
> instances follows the subfamily traditional scheme (RIBBI / WWS)
> where "Italic" is always last.
>
> The 'ital' axis should also be strictly boolean, only accepting
> values of 0 (for Uprights) or 1 (for Italics). This usually works
> as a mechanism for selecting between two linked variable font files.
>
> Also, the axis value name for uprights must be set as elidable.
>




> Original proposal: https://github.com/fonttools/fontbakery/issues/2934
> See also: https://github.com/fonttools/fontbakery/issues/3668
> See also: https://github.com/fonttools/fontbakery/issues/3669





* ⏩ **SKIP** <p>Font {font.file} doesn't have an ital axis</p>




</div>
</details>
</div>
</details>




### Summary

| 💥 ERROR | ☠ FATAL | 🔥 FAIL | ⚠️ WARN | ⏩ SKIP | ℹ️ INFO | ✅ PASS | 🔎 DEBUG |
| ---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 7 | 0 | 46 | 0 |
| 0% | 0% | 0% | 0% | 13% | 0% | 87% | 0% |



**Note:** The following loglevels were omitted in this report:


* DEBUG
