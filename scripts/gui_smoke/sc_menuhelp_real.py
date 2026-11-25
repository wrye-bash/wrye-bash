"""The help of a menu item shows in the status bar while the item is hovered and
must go when the menu closes. Real menus and keys: (a) the context menu of a
mod, popped by a real right click; (b) the first menu of the menu bar, opened
with F10."""
import os, sys, wx, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    sim = wx.UIActionSimulator()
    nat = frame._native_widget
    sb = frame.statusBar._native_widget
    info = lambda: sb.GetStatusText(1) # where set_status_info writes
    nb = frame.notebook._native_widget
    nb.SetSelection([nb.GetPageText(i) for i in range(nb.GetPageCount())].index('Mods')); pump(8)
    uil = frame.notebook.currentPage.uiList
    lc = uil._UIList__gList._native_widget
    uil.ClearSelected(); uil.SelectItem(uil.GetItem(2)); pump(6)
    closes = []
    nat.Bind(wx.EVT_MENU_CLOSE, lambda e: (closes.append(info()), e.Skip()))
    def drive(name, open_menu, keys):
        """Schedule keys [(ms, key, modifiers)], open the menu, poll the info
        field while it is open, log what it showed and what it shows after."""
        seen, state = [], {'polling': True}
        def poll():
            if not state['polling']: return
            t = info()
            if not seen or seen[-1] != t: seen.append(t)
            wx.CallLater(80, poll)
        sb.SetStatusText('before the menu', 1); pump(2)
        del closes[:]
        for ms, key, mods in keys:
            wx.CallLater(ms, sim.Char, key, mods)
        last = max(ms for ms, _k, _m in keys)
        for extra in (1500, 2500): # safety nets - a menu left open would hang the run
            wx.CallLater(last + extra, sim.Char, wx.WXK_ESCAPE)
        wx.CallLater(50, poll)
        open_menu()
        for _i in range(int((last + 3000) / 60)): # until the keys and safety nets ran
            pump(1, 0.06)
        state['polling'] = False; pump(3)
        helps = [t for t in seen if t not in ('', 'before the menu')]
        log(f'{name}: help shown while open: {bool(helps)} {helps[:2]} | EVT_MENU_CLOSE seen {len(closes)} | '
            f'status text after it closed: {info()!r}')
    try:
        # (a) a real right click on the selected mod
        r = lc.GetItemRect(2)
        hdr = getattr(lc, '_header_offset', 0) or 0
        x, y = lc.ClientToScreen((r.x + 60, r.y + r.height // 2 + hdr))
        def right_click():
            sim.MouseMove(x, y); pump(3)
            sim.MouseClick(wx.MOUSE_BTN_RIGHT)
        drive('context menu of a mod', right_click,
              [(700, wx.WXK_DOWN, 0), (1300, wx.WXK_ESCAPE, 0)])
        # (b) the menu bar, from the keyboard - keys go to the window under
        # the mouse without a window manager
        sx, sy, sw, sh = sb.GetScreenRect()
        def f10():
            sim.MouseMove(sx + sw // 2, sy + sh // 2); pump(2)
            nat.Raise(); uil._UIList__gList._native_widget.SetFocus(); pump(3)
            sim.Char(wx.WXK_F10)
        drive('first menu of the menu bar', f10,
              [(700, wx.WXK_DOWN, 0), (1300, wx.WXK_ESCAPE, 0), (1600, wx.WXK_ESCAPE, 0)])
    except Exception:
        log('SCENARIO FAILED', traceback.format_exc().replace('\n', ' | ')[-900:])
