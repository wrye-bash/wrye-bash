
Bash Asynchronous Installer Tab (BAIT) README
Myk Taylor

Design and functional documentation is in the doc/ subdirectory.  This
document just goes over dependency requirements and testing.


Dependencies
============
The following components are required to be installed to run BAIT:
  Python-2.7.2 or later (>=3.0 will not work until wxPython supports it)
  wxPython-2.8.12 or later (http://www.wxpython.org/)

The following packages are required to run the unit tests:
  nose-1.0.0 or later
        (http://somethingaboutorange.com/mrl/projects/nose/1.0.0/)
  mock-0.7.1 or later (http://pypi.python.org/pypi/mock)


Unit Testing
============
Without testing, we can have no confidence in the quality of the code.  Each
module in BAIT is individually addressed with a full-coverage unit test.  Since
Python is not statically typed, unit tests also serve the function of ensuring
the code is free from typos.  All unit tests should be run before every svn
commit so that no regressions slip in, and if coverage ever falls below 100%,
the unit tests should be augmented to bring the number back up.

Nose reads its configuration from setup.cfg, which currently instructs nose to
use logging.conf to configure logging, measure coverage, and display a report.

Run the tests by running
  nosetests
in the top-level directory (the one with setup.cfg in it).

Modules can be tested individually by specifying the test file name.  For
example:
  nosetests bait/util/enum_test.py


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
