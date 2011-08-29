<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="text"/>
<xsl:param name="release_num"/>
<xsl:param name="release_theme"/>

<xsl:template match="/">[size="4"][color="#FF8C00"]Bug tracking and progress towards next release[/color][/size]
Here's a rundown of what the next release will contain, as well as a list of all known bugs and requested enhancements.  Links lead to the sourceforge tracker artifacts.  If you have information or opinions pertaining to any particular bug or enhancement, please comment at the tracker link.  If you have screenshots or sample files, you can attach them (or links to them) to the trackers too.  Any information helps!

Users who have reported bugs and are updating from svn: please check the following for any closed/fixed bugs (indicated with a [color="#FF8C00"][s]strikethrough[/s][/color]).  Confirmation of the fix would be much appreciated.

[b]Upcoming release <xsl:value-of select="$release_num"/>[/b]: <xsl:value-of select="$release_theme"/>
[list]<xsl:for-each select="//trackers/tracker[name='Bugs']/tracker_items/tracker_item[status_id=1 and group_id=2061786]">
        <xsl:sort select="id" order="descending"/>
[*] [b][url=http://sourceforge.net/support/tracker.php?aid=<xsl:value-of select="id"/>]Bug <xsl:value-of select="id"/>[/url][/b] <xsl:value-of select="summary"/><xsl:if test="assignee!='nobody'"> [color="#00FF00"][<xsl:value-of select="assignee"/>][/color]</xsl:if></xsl:for-each>
    <xsl:for-each select="//trackers/tracker[name='Enhancements']/tracker_items/tracker_item[status_id=1 and group_id=2061780]">
        <xsl:sort select="id" order="descending"/>
[*] [b][url=http://sourceforge.net/support/tracker.php?aid=<xsl:value-of select="id"/>]Enhancement <xsl:value-of select="id"/>[/url][/b] <xsl:value-of select="summary"/><xsl:if test="assignee!='nobody'"> [color="#00FF00"][<xsl:value-of select="assignee"/>][/color]</xsl:if></xsl:for-each>
    <xsl:for-each select="//trackers/tracker[name='Bugs']/tracker_items/tracker_item[status_id=2 and group_id=2061786]">
        <xsl:sort select="id" order="descending"/>
[*] [color="#FF8C00"][s][url=http://sourceforge.net/support/tracker.php?aid=<xsl:value-of select="id"/>]Bug <xsl:value-of select="id"/>[/url][/s][/color] <xsl:value-of select="summary"/><xsl:if test="assignee!='nobody'"> [color="#00FF00"][<xsl:value-of select="assignee"/>][/color]</xsl:if></xsl:for-each>
    <xsl:for-each select="//trackers/tracker[name='Enhancements']/tracker_items/tracker_item[status_id=2 and group_id=2061780]">
        <xsl:sort select="id" order="descending"/>
[*] [color="#FF8C00"][s][url=http://sourceforge.net/support/tracker.php?aid=<xsl:value-of select="id"/>]Enhancement <xsl:value-of select="id"/>[/url][/s][/color] <xsl:value-of select="summary"/><xsl:if test="assignee!='nobody'"> [color="#00FF00"][<xsl:value-of select="assignee"/>][/color]</xsl:if></xsl:for-each>
[/list]

[b][url=https://sourceforge.net/tracker/?group_id=284958&amp;atid=1207901&amp;status=1]Additional known bugs[/url][/b]:[spoiler][list]<xsl:for-each select="//trackers/tracker[name='Bugs']/tracker_items/tracker_item[status_id=1 and group_id!=2061786]">
        <xsl:sort select="id" order="descending"/>
[*] [b][url=http://sourceforge.net/support/tracker.php?aid=<xsl:value-of select="id"/>]Bug <xsl:value-of select="id"/>[/url][/b] <xsl:value-of select="summary"/>
    </xsl:for-each>
[/list][/spoiler]

[b][url=https://sourceforge.net/tracker/?group_id=284958&amp;atid=1207904&amp;status=1]Current enhancement requests[/url][/b]:[spoiler][list]<xsl:for-each select="//trackers/tracker[name='Enhancements']/tracker_items/tracker_item[status_id=1 and group_id!=2061780]">
        <xsl:sort select="id" order="descending"/>
[*] [b][url=http://sourceforge.net/support/tracker.php?aid=<xsl:value-of select="id"/>]Enhancement <xsl:value-of select="id"/>[/url][/b] <xsl:value-of select="summary"/>
    </xsl:for-each>
[/list][/spoiler]
</xsl:template>
</xsl:stylesheet>
