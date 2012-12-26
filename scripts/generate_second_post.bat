::
:: generate_second_post.bat

@ECHO OFF

IF "%1" == "" GOTO HELP
IF "%2" == "" GOTO HELP


SET XMLFile=%3
IF "%3" == "" SET XMLFile=oblivionworks_export.xml

SET OUTFile=%4
IF "%4" == "" SET OUTFile=second_post.txt

:: --novalid is required since the DTD specification in sourceforge's exported XML
:: isn't available online yet
xsltproc --novalid --stringparam release_num "%1" --stringparam release_theme "%2" second_post_template.xsl %XMLFile% > %OUTFile%
ECHO Output sent to "%OUTFile%"
ECHO.
GOTO QUIT

:HELP
ECHO.
ECHO generate_second_post
ECHO.
ECHO USAGE:
ECHO   generate_second_post.bat release_num release_theme [exported_XML_filename] [output_filename]
ECHO.
ECHO EXAMPLE:
ECHO   generate_second_post 294 "Getting CBash patchers on par with the Python patchers"
ECHO.
ECHO project admin must export tracker data from:
ECHO   https://sourceforge.net/export/xml_export2.php?group_id=284958
ECHO then pass the name of the downloaded file to this script
ECHO.
ECHO to run this script, you must have xsltproc installed, which is part of the
ECHO standard libxslt package on Linux.  Windows users can get it from
ECHO   http://www.zlatkovic.com/libxml.en.html
ECHO alternately, most browsers have xsl functionality and can do the conversion,
ECHO though the exported XML must be modified to directly refer to the xsl
ECHO transformation file first.
ECHO.


:QUIT
PAUSE
