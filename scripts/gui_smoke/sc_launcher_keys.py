"""Real Enter keys in the launcher fields of the Status Bar settings page: is the launcher saved, does wx click OK?"""
import os, sys, wx, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    from bash.basher import settings_dialog
    def hook(dlg):
        try:
            dlg.Show(); dlg.Raise(); pump(10)
            sd = hook.sd
            page = next(p for p in sd._tab_tree.get_leaf_pages() if isinstance(p, settings_dialog.StatusBarPage))
            tb = sd._tab_tree._native_widget # select it through the Treebook - select_page of nightly raises on a top level page
            tb.SetSelection(next(i for i in range(tb.GetPageCount()) if tb.GetPage(i) is page._native_widget)); pump(6)
            log('page shown:', sd._tab_tree.get_selected_page_path(), page._native_widget.IsShownOnScreen())
            calls = []
            page._save_launcher = lambda: calls.append('launcher saved')
            ok = dlg.FindWindow(wx.ID_OK)
            h = wx.EvtHandler(); h.Bind(wx.EVT_BUTTON, lambda e: calls.append('OK CLICKED'))
            ok.PushEventHandler(h)
            di = dlg.GetDefaultItem()
            log('default item is OK:', di is not None and di.GetId() == wx.ID_OK, '| save enabled:', page._save_launcher_btn.enabled)
            sim = wx.UIActionSimulator()
            def enter(native, key):
                x, y = native.ClientToScreen((8, 8)); sim.MouseMove(x, y); pump(3)
                native.SetFocus(); pump(4)
                focused = wx.Window.FindFocus() is native
                del calls[:]; sim.Char(key); pump(10)
                return focused, list(calls)
            def native_of(f):
                nw = f._native_widget
                return nw.GetTextCtrl() if isinstance(nw, wx.PickerBase) else nw
            fields = (('name', page._launcher_name_txt), ('arguments', page._launcher_args_txt),
                      ('path picker', page._launcher_path), ('start in picker', page._launcher_start_in),
                      ('icon picker', page._launcher_icon))
            for nm, fld in fields:
                for key, kn in ((wx.WXK_RETURN, 'Enter'), (wx.WXK_NUMPAD_ENTER, 'keypad Enter')):
                    log('%-12s in the %-15s field: focused %s -> %s' % ((kn, nm) + enter(native_of(fld), key)))
            page._save_launcher_btn.enabled = False
            for nm, fld in fields[::2]:
                log('Save disabled, Enter in the %-15s field: focused %s -> %s' % ((nm,) + enter(native_of(fld), wx.WXK_RETURN)))
            ok.PopEventHandler(True)
            dlg.Hide()
        except Exception:
            log('hook failed', traceback.format_exc())
        return wx.ID_CANCEL
    auto['hook'] = hook
    orig_init = settings_dialog.SettingsDialog.__init__
    def patched(self, *a, **k):
        orig_init(self, *a, **k); hook.sd = self
    settings_dialog.SettingsDialog.__init__ = patched
    settings_dialog.SettingsDialog.display_dialog()
