"""Real Enter keys in path pickers and text fields of a dialog whose default button is OK: who gets the Enter?"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import *
dlg = wx.Dialog(None, title='pickers', size=(500, 400))
calls = []
ok = gui.OkButton(dlg)
ok._native_widget.Bind(wx.EVT_BUTTON, lambda e: calls.append('OK clicked'))
rec = lambda what: (lambda *a: calls.append(what))
fields = [
    ('FilePicker, no on_enter', gui.FilePicker(dlg)),
    ('FilePicker, on_enter', gui.FilePicker(dlg, on_enter=rec('on_enter'))),
    ('DirPicker, on_enter', gui.DirPicker(dlg, on_enter=rec('on_enter'))),
    ('TextField, no on_enter', gui.TextField(dlg)),
    ('TextField, on_enter', gui.TextField(dlg, on_enter=rec('on_enter'))),
]
sizer = wx.BoxSizer(wx.VERTICAL)
for _n, f in fields: sizer.Add(f._native_widget, 0, wx.EXPAND | wx.ALL, 4)
sizer.Add(ok._native_widget, 0, wx.ALL, 4)
dlg.SetSizer(sizer); dlg.Layout(); dlg.Show(); dlg.Raise(); pump(10)
print('default item is OK:', dlg.GetDefaultItem() is ok._native_widget)
sim = wx.UIActionSimulator()
def text_native(f):
    nw = f._native_widget
    return nw.GetTextCtrl() if isinstance(nw, wx.PickerBase) else nw
def enter(native, key):
    x, y = native.ClientToScreen((8, 8)); sim.MouseMove(x, y); pump(3)
    native.SetFocus(); pump(4)
    focused = wx.Window.FindFocus() is native
    del calls[:]; sim.Char(key); pump(10)
    return focused, list(calls)
for name, f in fields:
    for key, kname in ((wx.WXK_RETURN, 'Enter'), (wx.WXK_NUMPAD_ENTER, 'keypad Enter')):
        focused, got = enter(text_native(f), key)
        print(f'{name:25} {kname:12} focused {focused!s:5} -> {got}')
dlg.Destroy(); pump(3); print('done')
