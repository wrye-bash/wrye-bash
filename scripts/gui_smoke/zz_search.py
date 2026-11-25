"""The cancel button of a SearchBar: a real click clears the text (wx does it) and hides the button."""
import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import *
from bash.gui import SearchBar, PanelWin
host = wx.Frame(None, size=(300, 120), pos=(40, 40)); panel = PanelWin(host)
sb = SearchBar(panel); sz = wx.BoxSizer(wx.VERTICAL); sz.Add(sb._native_widget, 0, wx.EXPAND | wx.ALL, 8)
panel._native_widget.SetSizer(sz); host.Show(); host.Raise(); pump(10)
print('frame active:', activate(host))
texts = []; sb.on_text_changed.subscribe(texts.append)
nat = sb._native_widget; sim = wx.UIActionSimulator(); w, h = nat.GetSize(); res = []
for dx in (10, 14, 20, 26):
    sb.text_content = 'abc'; pump(4); del texts[:]
    shown = nat.IsCancelButtonVisible()
    sp = nat.ClientToScreen(wx.Point(w - dx, h // 2)); sim.MouseMove(sp.x, sp.y); pump(3); sim.MouseClick(wx.MOUSE_BTN_LEFT); pump(10)
    res.append((dx, shown, sb.text_content, list(texts), nat.IsCancelButtonVisible()))
    if sb.text_content == '': break
print('RESULT clicks at (width - dx): (dx, button shown before, text after, text changes seen, button shown after):', res)
print('RESULT cleared by the click:', res[-1][2] == '' and res[-1][3] == [''] and res[-1][4] is False)
host.Destroy(); pump(3)
