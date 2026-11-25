import os, sys, wx, time, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    from bash import balt, bass, gui, bosh, load_order
    nb = frame.notebook._native_widget
    nb.SetSelection(1); pump(8)
    mods = frame.notebook.currentPage.uiList
    lc = mods._UIList__gList._native_widget
    order = lambda: [mods.GetItem(i) for i in range(mods.item_count)]
    log('sort column:', mods.sort_column, '| order before:', order())
    src, dst = 2, 5
    mods.SelectAndShowItem(mods.GetItem(src), deselectOthers=True); pump(6)
    def center(i):
        r = lc.GetItemRect(i)   # the 197 override: y without the header
        hdr = lc._header_offset or 0
        # mouse coordinates are relative to the list's main window, below the header
        x, y = lc.ClientToScreen((r.x + 60, r.y + r.height // 2 + hdr))
        return x, y
    (sx, sy), (dx, dy) = center(src), center(dst)
    log('item rects:', tuple(lc.GetItemRect(src)), tuple(lc.GetItemRect(dst)), 'header offset', lc._header_offset, 'screen', (sx, sy), (dx, dy))
    sim = wx.UIActionSimulator()
    steps = [lambda: sim.MouseMove(sx, sy), lambda: sim.MouseDown()]
    n = 12
    for k in range(1, n + 1):
        steps.append(lambda k=k: sim.MouseMove(sx + 3 * min(k, 3), sy + (dy + 6 - sy) * k // n))
    steps += [lambda: sim.MouseMove(dx, dy + 6), lambda: sim.MouseUp()]
    loop = wx.GUIEventLoop()
    state = {'i': 0}
    def tick():
        try:
            if state['i'] < len(steps):
                steps[state['i']](); state['i'] += 1
                wx.CallLater(60, tick)
            else:
                wx.CallLater(600, loop.Exit)
        except Exception:
            log('tick failed', traceback.format_exc()); loop.Exit()
    wx.CallLater(100, tick)
    wx.CallLater(15000, lambda: (log('TIMEOUT waiting for the drag'), loop.Exit()))
    loop.Run()
    pump(10)
    log('order after :', order())
    shot('after_dnd')
