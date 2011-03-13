
== What is this? ======================================================
It's instructions and files necessary to create a standalone
Wrye Bash executable (i.e. on that doesn't require python installed).

I'm still messing around with it trying to get everything to work well,
but I'm at a point that I think it's ready for testing.


== Instructions =======================================================
1) Install 'py2exe':
      Download and install the appropriate package from:
     
      http://sourceforge.net/projects/py2exe/files/

      For example, I'm running on Python 2.7.1 (x86), so I downloaded
      the 'py2exe-0.6.9.win32-py2.7.exe' installer.

2) Setup a 'clean' copy of Wrye Bash to work on.  For example, using
   the archive version from TESNexus, extract all the files to a
   location.  For example 'C:\WB'.  Or you can just use your svn
   directory.

3) Do either step 3a or step 3b below (3b is easier)

   a) Copy the files in this folder to on directory up from the 'Mopy'
      directory.  In the above example, the directory structure would
      look like:

      + WB
       - bash.ico
       - build.py
       - readme.txt
       - ResHacker.exe
       - upx.exe
       + Data
         ... WB Data Files ...
       + Mopy
         ... WB Python Files ...

   -- OR --

   b) If 'build.py' is located in the svn, you can run it straight
      from there, no copying needed.

3) Run 'build.py' to create the executable.  This automates the
   process of:

   a) Running the py2exe script 'setup.py'
   b) Fixing the output executable's icon so it will show up
      in Vista/Win7.  For some reason, py2exe can't make proper exe's
      with icons for Vista/Win7.
   c) Compress the exe with UPX
   d) Cleanup of the files
   e) Make a 7z archive of the standalone

4) If you used step 3a, delete the files used to make the standalone.