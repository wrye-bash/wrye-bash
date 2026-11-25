import os, sys, wx, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump, save_tree
def run(frame, shot, log, auto):
    out = os.path.dirname(shot('00'))
    from bash import balt, bass, gui
    from bash.basher import settings_dialog
    def hook(dlg):
        try:
            dlg.Show(); pump(10)
            sd = hook.sd
            tp = sd._tab_tree; nw = tp._native_widget
            paths = [tp._page_path(i) for i in range(tp.page_count)] if hasattr(tp, '_page_path') else None
            log('pages:', paths)
            log('selected at start:', tp.get_selected_page_path())
            res = {}
            for i in range(nw.GetPageCount()):
                nw.SetSelection(i); pump(2); res[i] = tp.get_selected_page_path()
            log('path of each page when selected:', list(res.values()))
            for target in ('Appearance/Language', 'Backups', 'Appearance', 'Appearance/Status Bar', 'No/Such'):
                r = tp.select_page(target); pump(2)
                log('select_page(%r) ->' % target, r, '| now selected:', tp.get_selected_page_path())
            # click a link on the Appearance link page
            tp.select_page('Appearance'); pump(3)
            link_page = nw.GetPage(nw.GetSelection())
            links = [c for c in link_page.GetChildren() if isinstance(c, wx.adv.HyperlinkCtrl)]
            ev = wx.adv.HyperlinkEvent(links[0], links[0].GetId(), links[0].GetURL())
            links[0].GetEventHandler().ProcessEvent(ev); pump(3)
            log('clicked link', repr(links[0].GetURL()), '-> selected:', tp.get_selected_page_path())
            shot('settings_after_link'); save_tree(dlg, os.path.join(out, 'tree_settings.txt'))
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
    hook.sd = None
    # initial_page support
    def hook2(dlg):
        dlg.Show(); pump(6); log('opened with initial_page -> selected:', hook.sd._tab_tree.get_selected_page_path()); dlg.Hide(); return wx.ID_CANCEL
    auto['hook'] = hook2
    for ip in ('Appearance/Colors', 'General'):
        settings_dialog.SettingsDialog.display_dialog(ip)
