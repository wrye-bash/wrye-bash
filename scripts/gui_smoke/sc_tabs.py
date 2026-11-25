"""Hiding and showing the main tabs as the tab toggle links do: which tab is
selected after hiding the current one, is the menu bar and the status count
that of the selected tab, was Installers refreshed, does a tab shown again
show up and get selected."""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    import wx
    from bash import bass
    from bash.basher import _keyed_tabs, TabInfo
    nb = frame.notebook; nat = nb._native_widget; fnat = frame._native_widget
    def titles(): return [nat.GetPageText(i) for i in range(nat.GetPageCount())]
    def selected(): return nat.GetPageText(nat.GetSelection())
    def bar():
        mb = fnat.GetMenuBar()
        if mb is None: return None
        out = []
        for i in range(mb.GetMenuCount()):
            m = mb.GetMenu(i)
            fnat.ProcessEvent(wx.MenuEvent(wx.wxEVT_MENU_OPEN, 0, m))
            fnat.ProcessEvent(wx.MenuEvent(wx.wxEVT_MENU_CLOSE, 0, m))
            out.append((mb.GetMenuLabelText(i), m.GetMenuItemCount()))
        return out
    def count(): sb = fnat.GetStatusBar(); return sb.GetStatusText(sb.GetFieldsCount() - 1)
    key_of = {t.tab_title: k for k, t in _keyed_tabs.items()}
    def toggle(title): # what the link of the tab does
        k = key_of[title]
        nb.show_hide(k)
        bass.settings['bash.tabs.order'][k] ^= True
        pump(12)
    inst_shows = []
    try:
        # every tab once, to know its menu bar and count - Installers first,
        # answering its 'Enable Installers?' on a fresh game
        known = {}
        for t in titles():
            nat.SetSelection(titles().index(t)); pump(12)
            known[t] = (bar(), count())
        ip = TabInfo.INSTALLERS.tab_panel
        orig_show = ip.ShowPanel
        ip.ShowPanel = lambda *a, **k: (inst_shows.append(1), orig_show(*a, **k))[1]
        def state(what):
            sel = selected()
            log(f'{what}: tabs {titles()} | selected {sel!r} | menu bar of {sel}: {bar() == known[sel][0]} | '
                f'count of {sel}: {count() == known[sel][1]} | Installers refreshed {len(inst_shows)}x')
            del inst_shows[:]
        state('start')
        for title in ('Saves', 'Mods', 'Screenshots'): # middle, right after Installers, last
            nat.SetSelection(titles().index(title)); pump(12); del inst_shows[:]
            toggle(title)
            state(f'hid the current tab {title!r}')
            toggle(title)
            i = titles().index(title) if title in titles() else -1
            shown = i != -1 and nat.GetPage(i).IsShown()
            nat.SetSelection(i); pump(12)
            sel_page = nat.GetPage(nat.GetSelection())
            log(f'  shown again: on the tab bar at {i} | its page shown {shown} | selected now {selected()!r} | '
                f'page visible on screen {sel_page.IsShownOnScreen()}')
            state(f'  then selected {title!r}')
    except Exception:
        log('SCENARIO FAILED', traceback.format_exc().replace('\n', ' | ')[-900:])
