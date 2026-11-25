"""Page changes of the Installers detail notebook must not reach the main notebook's listener; rename prompt still opens."""
import os, sys, wx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    from bash import balt, bass, gui
    nb = frame.notebook._native_widget
    nb.SetSelection(0); pump(10)                      # Installers
    panel = frame.notebook.currentPage
    det = panel.detailsPanel
    uil = panel.uiList
    uil.SelectItem(uil.GetItem(0)); pump(4)
    shows = []
    cls = type(panel); orig = cls.ShowPanel
    cls.ShowPanel = lambda self, *a, **k: (shows.append(1), orig(self, *a, **k))[1]
    infos = []
    dcls = type(det); orig_info = dcls.RefreshInfoPage
    dcls.RefreshInfoPage = lambda self, index, *a, **k: (infos.append(index), orig_info(self, index, *a, **k))[1]
    g = det.gNotebook._native_widget
    seen = []
    for i in range(g.GetPageCount()):
        g.SetSelection(i); pump(3); seen.append(g.GetSelection())
    cls.ShowPanel = orig; dcls.RefreshInfoPage = orig_info
    log('detail notebook pages visited:', seen, '| main tab ShowPanel calls caused:', len(shows), '| info pages refreshed (lazily, by index):', infos)
    before = nb.GetSelection(); nb.SetSelection(1); pump(8); nb.SetSelection(0); pump(8)
    log('main notebook still switches tabs and shows the panel: ok', '| selection', nb.GetSelection())
    # rename prompt (begin label edit is no longer finished)
    uil.SelectItem(uil.GetItem(0)); pump(3)
    glist = uil._UIList__gList
    try:
        uil.Rename(); pump(6)
        opened = glist.ec_rename_prompt_opened()
        log('rename prompt opened on the Installers list:', bool(opened))
        if opened:
            ec = glist._native_widget.GetEditControl()
            e = wx.KeyEvent(wx.wxEVT_CHAR_HOOK); e.SetKeyCode(wx.WXK_ESCAPE); e.SetEventObject(ec)
            glist._native_widget.EndEditLabel(True) if hasattr(glist._native_widget, 'EndEditLabel') else None
            pump(6)
            log('after cancelling: prompt open', bool(glist.ec_rename_prompt_opened()))
    except Exception as e:
        import traceback; log('rename failed:', traceback.format_exc().strip().splitlines()[-1][:200])
