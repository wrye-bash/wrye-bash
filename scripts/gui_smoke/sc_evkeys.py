"""Key downs on the Mods list: Ctrl+Tab, Ctrl+Up when reordering is not allowed, Ctrl+Z, a plain Ctrl+key."""
import os, sys, wx, io, contextlib, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    from bash import balt, bass, gui
    nb = frame.notebook._native_widget
    nb.SetSelection(1); pump(8)
    uil = frame.notebook.currentPage.uiList
    glist = uil._UIList__gList; native = glist._native_widget
    def key(code, ctrl=True, shift=False):
        ev = wx.KeyEvent(wx.wxEVT_KEY_DOWN); ev.SetKeyCode(code); ev.SetControlDown(ctrl); ev.SetShiftDown(shift); ev.SetEventObject(native)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            try: handled = native.GetEventHandler().ProcessEvent(ev)
            except Exception as e: handled = 'raised ' + repr(e)[:80]
        pump(3)
        tb = [l for l in err.getvalue().splitlines() if 'Error' in l]
        return handled, tb[-1][:110] if tb else None
    sel0 = nb.GetSelection(); h, tb = key(wx.WXK_TAB); pump(6)
    log('Ctrl+Tab on the Mods list: handled', h, '| tab', sel0, '->', nb.GetSelection(), '| error', tb)
    nb.SetSelection(1); pump(8)
    uil.SelectItem(uil.GetItem(2)); pump(2)
    bass.settings['bash.mods.dnd.column.continue'] = True      # no dialog asking to continue
    uil.SortItems('File'); pump(4)
    order = [uil.GetItem(i) for i in range(uil.item_count)]
    h, tb = key(wx.WXK_UP)
    log('Ctrl+Up, sorted by File (reordering not allowed): handled', h, '| error', tb, '| order kept', order == [uil.GetItem(i) for i in range(uil.item_count)])
    uil.SortItems('Load Order'); pump(4)
    h, tb = key(ord('Z')); log('Ctrl+Z: handled', h, '| error', tb)
    h, tb = key(ord('Q')); log('Ctrl+Q (nothing of ours): handled', h, '(False = passed on to the list control) | error', tb)
    h, tb = key(wx.WXK_NUMPAD_ADD); log('Ctrl+Num+ key down: handled', h, '(False = passed on to the list control) | error', tb)
