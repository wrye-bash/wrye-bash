"""askYes with the real prompt shown and Enter or Escape pressed: which button is the default?
On Windows the prompt is the native TaskDialog, elsewhere a wx.MessageDialog."""
import os, sys, wx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    from bash import balt
    sim = wx.UIActionSimulator()
    nat = frame._native_widget
    def real_wx(dlg): # show the wx dialog for real
        return next(auto['real'][k] for k in type(dlg).__mro__ if k in auto['real'])(dlg)
    auto['hook'] = real_wx
    auto['task_hook'] = lambda task_dialog, show_it: show_it()
    def ask(default_is_yes, key, key_name):
        seen = []
        def press():
            focus = wx.Window.FindFocus()
            seen.append('focus %s' % (type(focus).__name__ if focus else 'not in a wx window'))
            sim.Char(key)
        # without a window manager the keys go to the window under the mouse - the prompt is centred on the frame
        x, y, w, h = nat.GetScreenRect(); sim.MouseMove(x + w // 2, y + h // 2); pump(3)
        wx.CallLater(800, press)
        safety = wx.CallLater(3000, lambda: (seen.append('still open 2 s after the key - Alt+N'), sim.Char(ord('N'), wx.MOD_ALT)))
        answer = balt.askYes(frame, 'Question?', 'Title', default_is_yes=default_is_yes)
        safety.Stop(); pump(3)
        log(f'askYes(default_is_yes={default_is_yes}), {key_name} -> {"Yes" if answer else "No"} | {", ".join(seen)}')
    try:
        for key, key_name in ((wx.WXK_RETURN, 'Enter'), (wx.WXK_ESCAPE, 'Escape')):
            for default_is_yes in (False, True):
                ask(default_is_yes, key, key_name)
    finally:
        auto['hook'] = auto['task_hook'] = None
