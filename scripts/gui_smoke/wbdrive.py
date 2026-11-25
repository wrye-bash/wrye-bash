"""Run Wrye Bash in-process and drive it: wbdrive.py <scenario.py> <out_dir>

WB_MOPY is the Mopy folder to run, WB_FAKE the fake game made by mkgame.py.
The scenario defines run(frame, shot, log, auto), called once the main loop
runs. Modal dialogs are answered OK while booting - after that the scenario
decides, through auto['hook'](dialog) for wx dialogs and
auto['task_hook'](task_dialog, show_it) for the native TaskDialog of Windows,
returning None to answer OK. auto['real'] maps each patched class to its
unpatched ShowModal (show for TaskDialog), to show a dialog for real."""
import importlib.abc
import importlib.util
import os
import runpy
import sys
import time
import traceback

MOPY = os.path.abspath(os.environ['WB_MOPY'])
FAKE = os.path.abspath(os.environ['WB_FAKE'])
scenario_path = os.path.abspath(sys.argv[1])
out_dir = os.path.abspath(sys.argv[2])
os.makedirs(out_dir, exist_ok=True)
os.chdir(MOPY)
sys.path.insert(0, MOPY)
import wx

LOG = open(os.path.join(out_dir, 'drive.log'), 'w', encoding='utf-8')
def log(*a):
    print(*a, file=LOG, flush=True)
    print('[drive]', *a, flush=True)

_dialogs = (wx.Dialog, wx.MessageDialog, wx.TextEntryDialog, wx.FileDialog,
            wx.DirDialog)
# real: the unpatched methods, taken before patching any (subclasses inherit)
auto = {'active': True, 'seen': [], 'real': {c: c.ShowModal for c in _dialogs}}
def _patch_modal(cls):
    def ShowModal(self):
        try: title = self.GetTitle()
        except Exception: title = '?'
        auto['seen'].append((cls.__name__, title))
        if auto['active']:
            log('auto-dismiss', cls.__name__, repr(title))
            return wx.ID_OK
        hook = auto.get('hook')
        if hook:
            res = hook(self)
            if res is not None: return res
        log('unexpected modal', cls.__name__, repr(title), '- answering OK')
        return wx.ID_OK
    cls.ShowModal = ShowModal
for c in _dialogs:
    _patch_modal(c)

def _patch_task_dialog(task_dialog):
    """The TaskDialog of bash.env.windows is native, ShowModal is not called -
    answer it with its first button, as the wx dialogs are answered OK."""
    orig_init, orig_show = task_dialog.__init__, task_dialog.show
    auto['real'][task_dialog] = orig_show
    def __init__(self, title, heading, content, tsk_buttons=(), *a, **k):
        self._drive_buttons = [*tsk_buttons]
        orig_init(self, title, heading, content, tsk_buttons, *a, **k)
    def show(self, *a, **k):
        title = getattr(self, '_title', '?')
        first = (self._drive_buttons or ['ok'])[0].removeprefix('+')
        auto['seen'].append(('TaskDialog', title))
        if auto['active']:
            log('auto-dismiss TaskDialog', repr(title), '- answering', first)
            return first, None, False
        hook = auto.get('task_hook')
        if hook:
            res = hook(self, lambda: orig_show(self, *a, **k))
            if res is not None: return res
        log('unexpected TaskDialog', repr(title), '- answering', first)
        return first, None, False
    task_dialog.__init__, task_dialog.show = __init__, show

class _PatchOnImport(importlib.abc.MetaPathFinder):
    """Patch TaskDialog as bash.env.windows is imported, not importing it
    ourselves - that would change the order Wrye Bash boots in."""
    def find_spec(self, name, path, target=None):
        if name != 'bash.env.windows': return None
        sys.meta_path.remove(self)
        spec = importlib.util.find_spec(name)
        exec_module = spec.loader.exec_module
        def exec_and_patch(module):
            exec_module(module)
            _patch_task_dialog(module.TaskDialog)
        spec.loader.exec_module = exec_and_patch
        return spec
if wx.Platform == '__WXMSW__':
    sys.meta_path.insert(0, _PatchOnImport())

def shot(name):
    """Save a screenshot, return its path - scenarios use its folder."""
    wx.Yield(); time.sleep(0.15); wx.Yield()
    p = os.path.join(out_dir, name + '.png')
    try:
        sdc = wx.ScreenDC()
        w, h = sdc.GetSize()
        bmp = wx.Bitmap(w, h)
        mdc = wx.MemoryDC(bmp)
        mdc.Blit(0, 0, w, h, sdc, 0, 0)
        mdc.SelectObject(wx.NullBitmap)
        bmp.SaveFile(p, wx.BITMAP_TYPE_PNG)
    except Exception:
        log('screenshot failed', traceback.format_exc().splitlines()[-1])
    return p

spec = importlib.util.spec_from_file_location('scenario', scenario_path)
scenario = importlib.util.module_from_spec(spec)
def _run_scenario():
    auto['active'] = False
    rc = 0
    try:
        spec.loader.exec_module(scenario)
        from bash import balt
        frame = balt.Link.Frame
        nat = frame._native_widget
        log('screen', tuple(wx.GetDisplaySize()), '| frame size',
            tuple(nat.GetSize()), '| active', nat.IsActive())
        scenario.run(frame, shot, log, auto)
    except Exception:
        log('SCENARIO FAILED:\n' + traceback.format_exc()); rc = 1
    LOG.flush()
    os._exit(rc)
_orig_ml = wx.PyApp.MainLoop
def _ml(self, *a, **k):
    wx.CallLater(int(os.environ.get('WB_DELAY', '2500')), _run_scenario)
    return _orig_ml(self, *a, **k)
wx.PyApp.MainLoop = _ml
sys.excepthook = lambda *a: log('UNCAUGHT:\n' + ''.join(
    traceback.format_exception(*a)))
sys.argv = ['Wrye Bash Launcher.pyw', '-o', os.path.join(FAKE, 'Oblivion'),
    '-p', os.path.join(FAKE, 'home', 'Documents'),
    '-l', os.path.join(FAKE, 'home', 'AppData', 'Local'), '--no-uac']
runpy.run_path(os.path.join(MOPY, 'Wrye Bash Launcher.pyw'),
               run_name='__main__')
