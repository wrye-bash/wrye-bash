"""The event fixes: Enter in a text field / search bar, the menu highlight handler, EventHandler skip."""
import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import *
from bash.gui import TextField, SearchBar, OkButton, DialogWindow, VLayout, GlobalMenu, Links
clicks = []
class Dlg(DialogWindow):
    title = 't'
    def __init__(self, parent):
        super().__init__(parent, 't', sizes_dict={})
        self.tf = TextField(self); self.sb = SearchBar(self)
        self.ok = OkButton(self, on_click=lambda: clicks.append(1) or __import__('bash.gui', fromlist=['EventResult']).EventResult.FINISH)
        VLayout(items=[self.tf, self.sb, self.ok]).apply_to(self)
host = wx.Frame(None); host.Show(); d = Dlg(host); d._native_widget.Show(); pump(5)
def enter(comp):
    del clicks[:]
    ev = wx.CommandEvent(wx.wxEVT_TEXT_ENTER, comp._native_widget.GetId()); ev.SetEventObject(comp._native_widget)
    handled = comp._native_widget.GetEventHandler().ProcessEvent(ev); pump(5)
    return handled, len(clicks)
h, n = enter(d.tf); print('OK ' if h and n == 1 else 'BAD', 'TextField Enter: handled (not passed on to wx)', h, '| OK button clicked', n, 'time(s)')
h, n = enter(d.sb); print('OK ' if n == 0 else 'BAD', 'SearchBar Enter: OK button clicked', n, 'time(s) | handled', h)
# the same with real key presses, through GTK
sim = wx.UIActionSimulator()
print('dialog active:', activate(d))
def real_enter(comp):
    del clicks[:]; comp._native_widget.SetFocus(); pump(8); sim.Char(wx.WXK_RETURN); pump(15); return len(clicks)
n = real_enter(d.tf); print('OK ' if n == 1 else 'BAD', 'real Enter key in the TextField: OK button clicked', n, 'time(s)')
n = real_enter(d.sb); print('OK ' if n == 0 else 'BAD', 'real Enter key in the SearchBar: OK button clicked', n, 'time(s)')
d._native_widget.Destroy(); host.Destroy(); pump(3); print('done')
