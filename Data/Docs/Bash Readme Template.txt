== $modName ===================================================#
=== Latest Version: ~~Link to preferred download site.~~ 
=== Discussion: ~~Link to discussion forum~~
=== Requirements:
~~Optional. List of required mods other than Morrowind.esm. If anything other than the official expansions are required, give the details in [[#|Installation]].~~

== Contents ===================================================================
~~You may want to cut this section out if your readme is very short. Also, you can make the contents deeper by setting CONTENTS to 2.~~
{{CONTENTS=1}}

== Overview =================================================================== 
~~This is where you talk about what your mod is/does. This should be fairly short (1-3 paragraphs). If you need more space, add more sections between [[#|Installation]] and [[#|Versions]].~~

== Installation ===============================================================
~~Optional. It's now generally assumed that players know how to install mods. So this section is primarily useful for unusual install instructions.~~

== Versions ===================================================================
~~Version notes go here.~~

=== 0.01 Bugfix [1/21/2007]
* Fixed global thermonuclear destruction bug. My bad.

=== 0.00 Initial Release [1/21/2007]
* Yay! Finally got it out the door!

== Syntax =====================================================================
~~Bash's autoconversion syntax is described here. Delete this and all other italicisized instructions before distributing your readme.~~

=== Bash Auto-Conversion
To trigger Wrye Bash's autoconversion...
* Choose the txt version of the file in Bash's Doc Browser.
* First line of txt file must look like <code>= Title ====#</code>. Note in particular, the <code>= </code> at the start and the single <code>#</code> character at the end!
* View the document in the Doc Browser. If Bash sees that the html is older than the text file, it will do the conversion. Note that this means that you can edit the text file in an external text editor and still get autoconversion.

== Custom Template
Copy this template to <code>Morrowind\Data Files\Docs\My Readme Template.txt</code> and modify as desired. That will become your default template.

=== Css
{{CSS:wtxt_teal.css}}
The default styles can be replaced by specifying css file in a CSS tag. Note that:
* Css file must be on a line by itself.
* Css file is not linked to, but is instead included on compilation. 
* Css must not contain any html markup tags (not even comments).
* Directory specification is not allowed. 
* Css file must be present either in same directory as source document or in the <code>Morrowind\Data Files\Docs</code> directory. If it's present in both, then the version in the current directory will be used.
* If no css file is specified, then a default, sand colored style set will be used.
* You can supply your own css files or one of your own. If you use your own, please give a it unique name so that it won't overwrite css files by other modders. Included css files are:
  * wtxt_teal.css
* A good place to put the CSS tag is at the end of the document.

=== Heading 3
==== Heading 4
Level of heading is determined by number of leading '='s. Trailing equal signs are ignored.

===Bullets
* Bullets1
  * Bullets 2
    * Bullets 3
      * Bullets 4
+ Alternate bullet char
o Alternate bullet char
. Invisibile bullet char

=== Styles
* ~~Italic~~
* __Bold__
* **BoldItalic**

===Links
* External Link: [[http://wrye.ufrealms.net]] or [[http://wrye.ufrealms.net | Wrye Musings]]
* Internal Link: [[#ReuseandCredits| Reuse and Credits]] or [[#| Reuse and Credits]].
* {{A:Non-Header Anchor}} is linked to by [[#|Non-Header Anchor]]
* **Notes:**
  * All section headers can be linked to by compressing the text of the header together (i.e., by stripping out all non alphabetical characters).
  * If you use the second form the link is automatically generated from the text of the link.
  * Note that all headers are autmatically anchored with with compressed text names. To create a link for non-header parts of the document, use the non-header anchor syntax.

=== Html
* <i>Html tags work fine</i>
* <code>code tag has special formatting</code> 
* **pre** tag is useful for code
<pre>
begin widgetScript
short counter
end
</pre>

=== Continued Text
These will form one
line in the compiled
html.

+ This will form one continuous 
  bullet item.

Blank lines can be used as spacers:


== Reuse and Credits ==========================================================
~~Optional. Licenses are particularly useful for keeping mods alive after the original author(s) has left the scene and/or the original download server has gone down. The default license below is fairly generous. You can find other licenses at [[http://wrye.ufrealms.net/WML%201.0.html | Wrye Modding Licenses 1.0]] or you may wish to make your own. You can skip a license altogether, but this may result in your mod becoming unavailable eventually if you can't be contacted.~~

=== License: WML 1.0 Modify and Redistribute, Share Alike
* You are free to redistribute this work in unmodified form.
* You are free to modify and re-distribute this work, so long as you: 1) give the author(s) credit proportional to their contribution to the final work, 2) distribute the final work under the same terms, and 3) make artistic resources included with the final work available under the same terms as below.
* Artistic resources (meshes, textures, sounds, etc.) included with this work  may be included in unmodified form with modified versions of this work, so long as their authors are given credit proportional to their contribution to the final work. Note that artistic resources may not be modified, or extracted from this work, unless permission is given elsewhere.

=== Courtesies
While the license above **allows** modification and redistribution, I'd **prefer** to keep it under my control for now. So, please try to contact me before modifying or redistributing it. 

=== License [Resources]
~~Optional. If the mod has resources, and they are under a different license, note that here.~~

=== Credits
~~List who did what here. E.g... ~~
* **Bethesda**, for creating a great game!

=== Contact
~~Contact info. Email address, website, preferred forums, etc.~~

