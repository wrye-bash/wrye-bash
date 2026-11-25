"""ListBox.on_context: index under the mouse, first selected from the keyboard, never skipped, not bound without a listener."""
import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import *
from bash.gui import ListBox, CheckListBox, PanelWin
ok = lambda c: 'OK ' if c else 'BAD'
host = wx.Frame(None, size=(320, 420), pos=(40, 40)); panel = PanelWin(host)
lb = ListBox(panel, choices=['a', 'b', 'c', 'd'], isSingle=False, isExtended=True)
clb = CheckListBox(panel, choices=['w', 'x', 'y', 'z'], isExtended=True)
quiet = ListBox(panel, choices=['q1', 'q2'])
sz = wx.BoxSizer(wx.VERTICAL)
for w in (lb, clb, quiet): sz.Add(w._native_widget, 1, wx.EXPAND)
panel._native_widget.SetSizer(sz); host.Show(); pump(8)
got = []
lb.on_context.subscribe(lambda dex: got.append(('lb', dex)))
clb.on_context.subscribe(lambda dex: got.append(('clb', dex)))
def point_of(nat, index):
    w, h = nat.GetClientSize()
    for y in range(1, h, 2):
        if nat.HitTest(wx.Point(12, y)) == index: return wx.Point(12, y + 2)
def send(nat, pos):
    ev = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nat.GetId(), pos); ev.SetEventObject(nat); del got[:]
    return nat.GetEventHandler().ProcessEvent(ev), ev.GetSkipped(), list(got)
for name, comp in (('lb', lb), ('clb', clb)):
    nat = comp._native_widget; pts = [point_of(nat, i) for i in range(4)]
    print(ok(all(pts)), f'{name}: a point found for each of the 4 items')
    r = [send(nat, nat.ClientToScreen(p)) for p in pts]
    print(ok(r == [(True, False, [(name, i)]) for i in range(4)]), f'{name}: context event at the mouse -> the index under it, handled, not skipped:', [x[2] for x in r])
    w, h = nat.GetClientSize(); r = send(nat, nat.ClientToScreen(wx.Point(12, h - 3)))
    print(ok(r == (True, False, [(name, wx.NOT_FOUND)])), f'{name}: below the last item -> -1:', r)
    nat.SetSelection(wx.NOT_FOUND); r0 = send(nat, wx.DefaultPosition)
    nat.SetSelection(1); nat.SetSelection(3); r1 = send(nat, wx.DefaultPosition)
    print(ok(r0[2] == [(name, -1)] and r1[2] == [(name, 1)]), f'{name}: from the keyboard -> first selected, -1 if none:', r0[2], r1[2], '| selections', list(nat.GetSelections()))
    # a real right click: wxGTK makes the context event from the right button going down
    del got[:]; sp = nat.ClientToScreen(pts[2]); sim = wx.UIActionSimulator(); sim.MouseMove(sp.x, sp.y); pump(3); sim.MouseClick(wx.MOUSE_BTN_RIGHT); pump(8)
    print(ok(got == [(name, 2)]), f'{name}: real right click on the third item ->', got)
qn = quiet._native_widget; r = send(qn, qn.ClientToScreen(wx.Point(5, 5)))
print(ok(r[0] is False), 'a list box nobody listens to does not take the context event:', r)
host.Destroy(); pump(3); print('done')
