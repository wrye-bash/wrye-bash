
Bash Asynchronous Installer Tab (BAIT) README
Myk Taylor

Design and functional documentation is in the doc/ subdirectory.  This
document just goes over dependency requirements and testing procedures.


Dependencies
============
The following components are required to be installed to run BAIT:
  1) Python-2.7.2 or later
       http://www.python.org/getit/
       >=3.0 will not work until wxPython supports it
  2) wxPython-2.8.12 or later
       http://www.wxpython.org/
       GUI library and framework

The following components are not required, but are used if installed:
  1) psutil-0.2.1 or later
       http://code.google.com/p/psutil/
       used for memory and CPU utilization profiling and for determining when
         we should reduce our cache sizes to avoid OOM errors

The following packages are required to run the unit tests:
  1) nose-1.0.0 or later
       http://somethingaboutorange.com/mrl/projects/nose/1.0.0/
       provides automatic test detection and execution and manages coverage
         reporting and performance profiling
  2) mock-0.7.1 or later
       http://pypi.python.org/pypi/mock
       ensures dummy objects used for unit tests accurately clone the APIs of
         the classes they are representing

The following packages are being considered for supporting possible future
functionality:
  1) PIL (Python Imaging Library)
       http://www.pythonware.com/products/pil/index.htm
       can be used for image manipulation for file previews
  2) pymedia
       http://pymedia.org/docs/pymedia.audio.sound.html#SpectrAnalyzer
       can be used for spectral analysis of mp3 files so we can determine
         which voice files are silent


Unit Testing
============
Without testing, we can have no confidence in the quality of the code.  Each
Python module (i.e. each .py file) in BAIT is individually addressed with a
full-coverage unit test.  Since Python is not statically typed, unit tests also
serve the function of ensuring the code is free from typos.  All unit tests
should be run before every svn commit so that no regressions slip in, and if
coverage ever falls below 100%, the unit tests should be augmented to bring the
number back up.

Nose reads its configuration from setup.cfg, which currently instructs nose to
use logging.conf to configure logging, measure coverage, and display a report.

Run the tests by running
  nosetests
in the top-level directory (the one with setup.cfg in it).

Modules can be tested individually by specifying the test file name.  For
example:
  nosetests bait/util/enum_test.py

If you have renamed or deleted any .py files, be sure to remove the associated
.pyc file before running the tests, or references to the deleted files may be
erroneously valid.


Integration Testing
===================
The file baittest.py exists so we can test the integration of the entire BAIT
stack.  It will bring up an interactive wxWindows application that houses an
instance of the BAIT installers tab.  It will use data in the testdata/
directory and will not save its state by default, but can be instructed to
use other directories (including the real Oblivion Data/ directory) and have
different behaviors by specifying options on the commandline.  Run:
  ./baittest.py --help
for a full list of options.


Logging
=======
Logging verbosity is controlled by logging.conf.  To set the logging verbosity
for tests, edit that file, then run the tests.  The output will appear in
bait.log.  On Linux, a convenient idiom is to run:
  tail -F bait.log &
and then run the test.  This will display the log messages in the console in
realtime as the test is running.  It detects when the current bait.log gets
rotated as well, and will correctly start tailing the new file.
