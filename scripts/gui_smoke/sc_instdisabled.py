"""The menu bar and status count when the Installers tab is selected while Installers is disabled."""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    import wx
    from bash import bass
    nb = frame.notebook; nat = nb._native_widget; fnat = frame._native_widget
    def titles(): return [nat.GetPageText(i) for i in range(nat.GetPageCount())]
    def bar():
        mb = fnat.GetMenuBar(); out = []
        if mb is None: return None
        for i in range(mb.GetMenuCount()):
            m = mb.GetMenu(i); fnat.ProcessEvent(wx.MenuEvent(wx.wxEVT_MENU_OPEN, 0, m))
            fnat.ProcessEvent(wx.MenuEvent(wx.wxEVT_MENU_CLOSE, 0, m)); out.append((mb.GetMenuLabelText(i), m.GetMenuItemCount()))
        return out
    def status(): sb = fnat.GetStatusBar(); return [sb.GetStatusText(i) for i in range(sb.GetFieldsCount())]
    try:
        t = titles(); nat.SetSelection(t.index('Installers')); pump(12); inst_bar, inst_status = bar(), status()
        nat.SetSelection(t.index('Saves')); pump(12); saves_bar, saves_status = bar(), status()
        log('Installers enabled:', inst_bar, inst_status[-1:], '| Saves:', saves_bar, saves_status[-1:])
        bass.settings['bash.installers.enabled'] = False
        nat.SetSelection(t.index('Installers')); pump(12); b, s = bar(), status()
        log('Installers DISABLED and selected: menu bar', b, '| that of Installers:', [x[0] for x in b] == [x[0] for x in inst_bar] and b != saves_bar,
            '| still that of Saves:', b == saves_bar, '| status', s[-1:], '| still that of Saves:', s[-1:] == saves_status[-1:])
        nat.SetSelection(t.index('Mods')); pump(12); log('then Mods:', bar())
    except Exception:
        log('SCENARIO FAILED', traceback.format_exc().replace('\n', ' | ')[-600:])
    finally:
        bass.settings['bash.installers.enabled'] = True
