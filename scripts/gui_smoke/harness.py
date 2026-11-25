"""Boot just enough of Wrye Bash to import bash.gui under a real wx.App -
or use the app running, when wbdrive.py runs the test in its main loop."""
import sys, os, builtins
MOPY = os.path.abspath(os.environ['WB_MOPY'])
sys.path.insert(0, MOPY)
import wx
app = wx.GetApp() or wx.App()
from bash import localize  # installs _()
if not hasattr(builtins, '_'):
    builtins._ = lambda s: s
from bash import bolt, bass
from bash import gui
from bash.gui import _gui_globals
_gui_globals.init_image_resources(bolt.GPath(MOPY + '/bash/images'))
from sclib import activate, press # real input helpers

def pump(n=5):
    for _i in range(n):
        wx.Yield()
        wx.WakeUpIdle()
        app.ProcessPendingEvents()
