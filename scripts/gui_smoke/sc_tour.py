"""Baseline tour: every tab, the settings dialog, a few gui dialogs - screenshots + widget tree dumps."""
import os, sys, wx, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump, save_tree
def run(frame, shot, log, auto):
    out = os.path.dirname(shot('00_boot'))
    from bash import balt, bass, gui
    from bash.basher import settings_dialog
    nb = frame.notebook._native_widget
    auto['hook'] = None
    for i in range(nb.GetPageCount()):
        title = nb.GetPageText(i).replace(' ', '_')
        nb.SetSelection(i); pump(10)
        shot('tab_%d_%s' % (i, title))
        n = save_tree(frame._native_widget, os.path.join(out, 'tree_tab_%d_%s.txt' % (i, title)))
        mb = frame._native_widget.GetMenuBar()
        log('tab', title, 'widgets', n, 'menus', [mb.GetMenuLabel(j) for j in range(mb.GetMenuCount())] if mb else None,
            'top level windows', len(wx.GetTopLevelWindows()))
    # select a plugin so the details fill in
    nb.SetSelection(1); pump(8)
    mods = frame.notebook.currentPage.uiList
    mods.SelectAndShowItem(mods.GetItem(2), deselectOthers=True); pump(10)
    shot('mods_selected'); save_tree(frame._native_widget, os.path.join(out, 'tree_mods_selected.txt'))
    # resize the frame a few times (splitters)
    for k, sz in enumerate([(700, 420), (1300, 800), (1024, 512)]):
        frame._native_widget.SetSize(sz); pump(10)
        save_tree(frame._native_widget, os.path.join(out, 'tree_resize_%d.txt' % k))
    shot('after_resizes')
    # modal dialogs: show them non-modally from the hook, dump, then cancel
    def hook(dlg):
        name = type(dlg).__name__ + '_' + ''.join(ch for ch in dlg.GetTitle() if ch.isalnum())[:24]
        try:
            dlg.Show(); pump(10)
            shot('dlg_' + name); save_tree(dlg, os.path.join(out, 'tree_dlg_%s.txt' % name))
            dlg.Hide()
        except Exception:
            log('hook failed for', name, traceback.format_exc())
        return wx.ID_CANCEL
    auto['hook'] = hook
    for label, opener in (
        ('settings', lambda: settings_dialog.SettingsDialog.display_dialog()),
        ('deletion', lambda: gui.DeletionDialog.display_dialog(frame, title='Delete Items',
            items_to_delete=['a.esp', 'b & c.esp'], default_recycle=True, sizes_dict=bass.settings,
            icon_bundle=balt.Resources.bashBlue, trash_icon=gui.get_image('trash_can.32'))),
        ('datetime', lambda: gui.DateAndTimeDialog.display_dialog(frame, warning_color=balt.colors['default.warn'],
            icon_bundle=balt.Resources.bashBlue)),
        ('continue', lambda: balt.askContinue(frame, 'Some question & more?', 'bash.test.continue')),
        ('asktext', lambda: balt.askText(frame, 'Enter text:', 'Title', 'default')),
    ):
        try:
            res = opener(); log('dialog', label, '->', repr(res)[:80])
        except Exception:
            log('dialog', label, 'FAILED', traceback.format_exc())
    log('top level windows at the end:', len(wx.GetTopLevelWindows()), [type(t).__name__ for t in wx.GetTopLevelWindows()])
