"""The menus of the list boxes (tags of the Mods details, plugin filter and sub-packages of the Installers details,
the lists of the Bashed Patch dialog): asked for with the mouse and from the keyboard.
Runs on the code before the change too (right down + right up there, no keyboard path)."""
import os, sys, gc, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    import wx
    from bash import basher, balt
    from bash.basher import patcher_dialog
    popped = []
    wx.Window.PopupMenu = lambda self, menu, *a: (popped.append([i.GetItemLabelText() or '---' for i in menu.GetMenuItems()][:5]), True)[1]
    nb = frame.notebook._native_widget
    def tab(t): nb.SetSelection([nb.GetPageText(i) for i in range(nb.GetPageCount())].index(t)); pump(10)
    def point_of(nat, index):
        w, h = nat.GetClientSize()
        for y in range(1, h, 2):
            if nat.HitTest(wx.Point(12, y)) == index: return wx.Point(12, y + 2)
    def ask(comp, where):
        """where: an item index, 'empty' (below the items) or 'keyboard'"""
        nat = comp._native_widget; new = not hasattr(comp, 'on_mouse_right_up'); del popped[:]
        if where == 'keyboard':
            if not new: return 'no keyboard path'
            pt = None
        elif where == 'empty': pt = wx.Point(12, nat.GetClientSize()[1] - 3)
        else:
            pt = point_of(nat, where)
            if pt is None: return f'no item {where}'
        try:
            if new:
                ev = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU, nat.GetId(), wx.DefaultPosition if pt is None else nat.ClientToScreen(pt))
                ev.SetEventObject(nat); nat.GetEventHandler().ProcessEvent(ev)
            else:
                for t in (wx.wxEVT_RIGHT_DOWN, wx.wxEVT_RIGHT_UP):
                    ev = wx.MouseEvent(t); ev.SetPosition(pt); ev.SetEventObject(nat); nat.GetEventHandler().ProcessEvent(ev)
            err = None
        except Exception as e: err = f'{type(e).__name__}: {e}'
        pump(3)
        return {'menus': list(popped), 'selected': list(nat.GetSelections()), 'error': err}
    try:
        # 1. Mods details: the tags list
        tab('Mods'); uil = frame.notebook.currentPage.uiList; uil.ClearSelected(); uil.SelectItem(uil.GetItem(2)); pump(8)
        md = next(o for o in gc.get_objects() if isinstance(o, basher.ModDetails))
        log('TAGS list items:', md.gTags._native_widget.GetCount())
        for where in (0, 'empty', 'keyboard'): log('  tags', where, '->', ask(md.gTags, where))
        # 2. Installers details: plugin filter and sub-packages
        tab('Installers'); il = frame.notebook.currentPage.uiList
        pk = [il.GetItem(k) for k in range(il.item_count)]; il.ClearSelected(); il.SelectItem([p for p in pk if 'Second' in str(p)][0]); pump(10)
        det = next(o for o in gc.get_objects() if isinstance(o, basher.InstallersDetails))
        esp, sub = det.gEspmList, det.gSubList
        log('PLUGIN FILTER items:', esp._native_widget.GetCount(), '| SUB-PACKAGES items:', sub._native_widget.GetCount())
        for where in (0, 'empty', 'keyboard'): log('  plugin filter', where, '->', ask(esp, where))
        esp._native_widget.SetSelection(0); log('  plugin filter keyboard, first item selected ->', ask(esp, 'keyboard'))
        for where in ('empty', 'keyboard'): log('  sub-packages', where, '->', ask(sub, where))
        # 3. the Bashed Patch dialog
        tab('Mods'); uil = frame.notebook.currentPage.uiList
        bp = [uil.GetItem(k) for k in range(uil.item_count) if 'Bashed Patch' in str(uil.GetItem(k))][0]
        uil.ClearSelected(); uil.SelectItem(bp); pump(6)
        def in_dialog(native_dlg):
            title = native_dlg.GetTitle()
            if not title.startswith('Update '):
                log('  (dialog before it:', type(native_dlg).__name__, repr(title), '- answered yes)'); return wx.ID_YES
            pd = next(o for o in gc.get_objects() if isinstance(o, patcher_dialog.PatchDialog) and o._native_widget is native_dlg)
            native_dlg.Show(); pump(8)
            names = [pd.gPatchers._native_widget.GetString(i) for i in range(pd.gPatchers._native_widget.GetCount())]
            log('PATCH DIALOG shown with', len(names), 'patchers')
            done = {'tweak': 0, 'list': 0}
            for dex, panel in enumerate(pd._gui_patchers):
                kind = 'tweak' if hasattr(type(panel), 'TweakOnListCheck') else 'list' if hasattr(type(panel), 'ShowChoiceMenu') else None
                if kind is None or done[kind] >= 2: continue
                pd.OnSelect(dex, names[dex]); pump(6)
                lst = panel.gTweakList if kind == 'tweak' else panel.gList
                n = lst._native_widget.GetCount()
                if not n: continue
                got = []; orig = panel.ShowChoiceMenu
                panel.ShowChoiceMenu = lambda i, _o=orig: (got.append(i), _o(i))[1]
                # the listeners were subscribed with the bound method - call through the events all the same
                res = {w: ask(lst, w) for w in (0, min(2, n - 1), 'empty', 'keyboard')}
                lst._native_widget.SetSelection(min(1, n - 1)); res['keyboard, item selected'] = ask(lst, 'keyboard')
                log(f'  {kind} panel {names[dex]!r} ({n} items):')
                for w, r in res.items(): log('     ', w, '->', r)
                if kind == 'tweak':
                    nat = lst._native_widget; tips = []
                    for i in (0, min(1, n - 1)):
                        ev = wx.MouseEvent(wx.wxEVT_MOTION); ev.SetPosition(point_of(nat, i)); ev.SetEventObject(nat); nat.GetEventHandler().ProcessEvent(ev)
                        tips.append(pd.gTipText.label_text[:40])
                    ev = wx.MouseEvent(wx.wxEVT_LEAVE_WINDOW); ev.SetEventObject(nat); nat.GetEventHandler().ProcessEvent(ev)
                    log('      tip while the mouse moves over items 0 and 1:', tips, '| after it left:', repr(pd.gTipText.label_text[:20]))
                done[kind] += 1
            native_dlg.Hide(); return wx.ID_CANCEL
        auto['hook'] = in_dialog
        link = next(o for o in gc.get_objects() if type(o).__name__ == 'Mod_RebuildPatch')
        link._initData(uil, [bp])
        log('rebuild patch link enabled:', link._enable())
        try: log('rebuild patch link returned', link.Execute())
        except Exception: log('rebuild patch link FAILED', traceback.format_exc().replace('\n', ' | ')[-500:])
        auto['hook'] = None
    except Exception:
        log('SCENARIO FAILED', traceback.format_exc().replace('\n', ' | ')[-900:])
