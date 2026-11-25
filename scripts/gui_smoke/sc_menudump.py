"""Dump every context, column and global menu of the tabs, the status bar button menus - as json, to compare two versions.
Works whether Link.AppendToMenu takes a wx.Menu or a gui.Menu wrapper."""
import os, sys, wx, json, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    out = os.path.dirname(shot('00_menudump'))
    from bash import balt, bass, gui
    breaks = []
    _orig_break = wx.Menu.Break
    def _rec_break(self): breaks.append(self.GetMenuItemCount()); return _orig_break(self)
    try: wx.Menu.Break = _rec_break
    except Exception as e: log('cannot record menu breaks:', repr(e))
    wrapped = hasattr(gui, 'Menu')
    def new_menu(): return gui.Menu() if wrapped else wx.Menu()
    nat = lambda m: m._native_widget if hasattr(m, '_native_widget') else m
    def dump(wxmenu):
        res = []
        for it in wxmenu.GetMenuItems():
            sub = it.GetSubMenu()
            res.append([it.GetItemLabel(), it.GetHelp(), it.GetKind(), it.IsEnabled(), bool(it.IsCheckable() and it.IsChecked()),
                        it.IsSeparator(), dump(sub) if sub else None])
        return res
    lazy = hasattr(gui.Links, 'show_links')   # the menu and its items are kept: show the links again, read the native menu
    def build(links, window, selection):
        del breaks[:]
        if lazy:
            try:
                links.show_links(window, selection)
                return {'items': dump(links._native_widget), 'breaks': list(breaks)}
            except Exception as e:
                return {'error': traceback.format_exc().strip().splitlines()[-1][:200]}
        m = new_menu()
        try:
            for link in links: link.AppendToMenu(m, window, selection)
            return {'items': dump(nat(m)), 'breaks': list(breaks)}
        except Exception as e:
            return {'error': traceback.format_exc().strip().splitlines()[-1][:200]}
        finally: nat(m).Destroy()
    res = {}
    nb = frame.notebook._native_widget
    all_res = [res, {}]
    for res, order in ((all_res[0], 1), (all_res[1], -1)):
     for i in range(nb.GetPageCount())[::order]:
         title = nb.GetPageText(i)
         nb.SetSelection(i); pump(8)
         uil = getattr(frame.notebook.currentPage, 'uiList', None)
         if uil is None: res[title] = 'no list'; continue
         tab = res[title] = {}
         items = [uil.GetItem(k) for k in range(min(3, uil.item_count))] if hasattr(uil, 'item_count') else []
         sels = {'none': [], 'one': items[:1], 'two': items[:2], 'third': items[2:3]}
         if order < 0: sels = dict(reversed([*sels.items()]))
         for name, sel in sels.items():
             try:
                 uil.ClearSelected() if hasattr(uil, 'ClearSelected') else None
                 for it in sel: uil.SelectItem(it) if hasattr(uil, 'SelectItem') else None
                 pump(2)
             except Exception as e: tab['select_' + name] = repr(e)[:120]
             selected = uil.GetSelected()
             if uil.context_links and selected: tab['context_' + name] = build(uil.context_links, uil, selected)
         if uil.column_links: tab['column'] = build(uil.column_links, uil, 0)
         for cat, links in (uil.global_links or {}).items(): tab['global_' + cat] = build(links, uil, 0)
    res = all_res[0]
    nb.SetSelection(nb.GetPageCount() - 1); pump(8)   # end on the last tab, as a single pass does
    sb = frame.statusBar
    for uid, btn in getattr(sb, 'all_sb_links', {}).items():
        mm = getattr(btn, 'mainMenu', None)
        if mm and btn._is_created():
            for r in all_res: r.setdefault('statusbar', {})[uid] = build(mm, btn, 0)
    json.dump(all_res[1], open(os.path.join(out, 'menus_pass2.json'), 'w'), indent=1, sort_keys=True, default=str)
    def count(d):
        return sum(count(v) if isinstance(v, dict) and 'items' not in v else (len(v.get('items', [])) if isinstance(v, dict) else 0) for v in d.values())
    json.dump(res, open(os.path.join(out, 'menus.json'), 'w'), indent=1, sort_keys=True, default=str)
    n_menus = sum(1 for t in res.values() if isinstance(t, dict) for v in t.values() if isinstance(v, dict))
    n_err = sum(1 for t in res.values() if isinstance(t, dict) for v in t.values() if isinstance(v, dict) and 'error' in v)
    log('menus dumped:', n_menus, '| top level items:', count(res), '| build errors:', n_err, '| wrapper api:', wrapped, '| tabs:', list(res))
    # the real global menu: open each category as wx does and read it back
    mb = frame._native_widget.GetMenuBar()
    glob = {}
    if mb:
        for j in range(mb.GetMenuCount()):
            m = mb.GetMenu(j); ev = wx.MenuEvent(wx.wxEVT_MENU_OPEN, 0, m); ev.SetEventObject(frame._native_widget)
            frame._native_widget.GetEventHandler().ProcessEvent(ev)
            first = dump(m)
            frame._native_widget.GetEventHandler().ProcessEvent(ev)   # reopen: cleared and repopulated
            glob[mb.GetMenuLabel(j)] = {'items': first, 'stable_on_reopen': dump(m) == first}
            cl = wx.MenuEvent(wx.wxEVT_MENU_CLOSE, 0, m); cl.SetEventObject(frame._native_widget); frame._native_widget.GetEventHandler().ProcessEvent(cl)
    json.dump(glob, open(os.path.join(out, 'globalmenu.json'), 'w'), indent=1, sort_keys=True, default=str)
    log('global menu categories:', {k: (len(v['items']), v['stable_on_reopen']) for k, v in glob.items()})
    wx.Menu.Break = _orig_break
