"""The menus of the list boxes (tags of the Mods details, plugin filter and sub-packages of the Installers details,
the lists of the Bashed Patch dialog), asked for with REAL input: right clicks and, from the keyboard, the menu key and
Shift+F10. Menus are recorded, not shown. How many menus each input popped is logged - it must be one."""
import os, sys, gc, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    import wx
    from bash import basher
    from bash.basher import patcher_dialog
    popped = []
    def record(self, menu, *a):
        popped.append([i.GetItemLabelText() or '---' for i in menu.GetMenuItems()][:4])
        return True
    wx.Window.PopupMenu = record
    sim = wx.UIActionSimulator()
    nb = frame.notebook._native_widget
    def tab(t): nb.SetSelection([nb.GetPageText(i) for i in range(nb.GetPageCount())].index(t)); pump(10)
    def point_of(nat, index):
        w, h = nat.GetClientSize()
        for y in range(1, h, 2):
            if nat.HitTest(wx.Point(12, y)) == index: return wx.Point(12, y + 2)
    def ask(comp, where):
        """where: an item index, 'empty' (below the items), 'menu key' or 'Shift+F10'"""
        nat = comp._native_widget; del popped[:]
        if where in ('menu key', 'Shift+F10'):
            x, y = nat.ClientToScreen(wx.Point(12, 4)); sim.MouseMove(x, y); pump(2)
            nat.SetFocus(); pump(3)
            if wx.Window.FindFocus() is not nat: return f'NOT FOCUSED ({type(wx.Window.FindFocus()).__name__})'
            fired = []
            safety = [wx.CallLater(1500 + 400 * k, lambda: (fired.append(1), sim.Char(wx.WXK_ESCAPE))) for k in range(2)]
            if where == 'menu key': sim.Char(wx.WXK_WINDOWS_MENU)
            else: sim.Char(wx.WXK_F10, wx.MOD_SHIFT)
            pump(8)
            for t in safety: t.Stop()
            if fired: popped.append(f'(a native modal loop was left open - closed with {len(fired)} Escape)')
        else:
            pt = wx.Point(12, nat.GetClientSize()[1] - 3) if where == 'empty' else point_of(nat, where)
            if pt is None: return f'no item {where}'
            x, y = nat.ClientToScreen(pt); sim.MouseMove(x, y); pump(3)
            under = wx.FindWindowAtPointer()[0]
            sim.MouseClick(wx.MOUSE_BTN_RIGHT)
        pump(8)
        res = {'menus popped': len(popped), 'first labels': list(popped), 'selected': list(nat.GetSelections())}
        if not popped and where not in ('menu key', 'Shift+F10') and under is not nat: # say where the click went
            res['mouse was over'] = f'{type(under).__name__} at {(x, y)}, list at {tuple(nat.GetScreenRect())}'
        return res
    try:
        # 1. Mods details: the tags list
        tab('Mods'); uil = frame.notebook.currentPage.uiList; uil.ClearSelected(); uil.SelectItem(uil.GetItem(2)); pump(8)
        md = next(o for o in gc.get_objects() if isinstance(o, basher.ModDetails))
        log('TAGS list items:', md.gTags._native_widget.GetCount())
        for where in ('empty', 'menu key', 'Shift+F10'): log('  tags', where, '->', ask(md.gTags, where))
        # 2. Installers details: plugin filter and sub-packages
        tab('Installers'); il = frame.notebook.currentPage.uiList
        pk = [il.GetItem(k) for k in range(il.item_count)]; il.ClearSelected(); il.SelectItem([p for p in pk if 'Second' in str(p)][0]); pump(10)
        det = next(o for o in gc.get_objects() if isinstance(o, basher.InstallersDetails))
        esp, sub = det.gEspmList, det.gSubList
        log('PLUGIN FILTER items:', esp._native_widget.GetCount(), '| SUB-PACKAGES items:', sub._native_widget.GetCount())
        for where in (0, 'empty', 'menu key'): log('  plugin filter', where, '->', ask(esp, where))
        esp._native_widget.SetSelection(0); log('  plugin filter menu key, first item selected ->', ask(esp, 'menu key'))
        for where in ('empty', 'menu key'): log('  sub-packages', where, '->', ask(sub, where))
        # 3. the Bashed Patch dialog
        tab('Mods'); uil = frame.notebook.currentPage.uiList
        bp = [uil.GetItem(k) for k in range(uil.item_count) if 'Bashed Patch' in str(uil.GetItem(k))][0]
        uil.ClearSelected(); uil.SelectItem(bp); pump(6)
        def in_dialog(native_dlg):
            title = native_dlg.GetTitle()
            if not title.startswith('Update '):
                log('  (dialog before it:', type(native_dlg).__name__, repr(title), '- answered yes)'); return wx.ID_YES
            pd = next(o for o in gc.get_objects() if isinstance(o, patcher_dialog.PatchDialog) and o._native_widget is native_dlg)
            native_dlg.Show(); native_dlg.Raise(); pump(8)
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
                res = {w: ask(lst, w) for w in (0, min(2, n - 1), 'empty', 'menu key')}
                lst._native_widget.SetSelection(min(1, n - 1)); res['menu key, item selected'] = ask(lst, 'menu key'); res['Shift+F10, item selected'] = ask(lst, 'Shift+F10')
                log(f'  {kind} panel {names[dex]!r} ({n} items):')
                for w, r in res.items(): log('     ', w, '->', r)
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
