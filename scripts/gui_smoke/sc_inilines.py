"""INI Edits: selecting a line in the two INI line lists (INIListCtrl.OnSelect) - no error, the line is deselected again."""
import os, sys, gc, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    import wx
    from bash import balt
    nb = frame.notebook._native_widget
    try:
        nb.SetSelection([nb.GetPageText(i) for i in range(nb.GetPageCount())].index('INI Edits')); pump(12)
        uil = frame.notebook.currentPage.uiList
        log('tweaks listed:', uil.item_count)
        if uil.item_count: uil.ClearSelected(); uil.SelectItem(uil.GetItem(0)); pump(10)
        ctrls = [o for o in gc.get_objects() if isinstance(o, balt.INIListCtrl) and o]
        log('INI line lists:', [(type(c).__name__, c.GetItemCount()) for c in ctrls])
        for c in ctrls:
            n = c.GetItemCount(); res = []
            for i in (0, min(3, n - 1), n - 1) if n else ():
                seen = []
                def spy(e): seen.append(e.GetIndex()); e.Skip()
                frame._native_widget.Bind(wx.EVT_LIST_ITEM_SELECTED, spy)
                try: c.Select(i); pump(3); err = None
                except Exception as e: err = f'{type(e).__name__}: {e}'
                frame._native_widget.Unbind(wx.EVT_LIST_ITEM_SELECTED, handler=spy)
                res.append((i, 'selected after' if c.GetFirstSelected() != -1 else 'deselected again', 'reached the frame' if seen else 'stayed in the list', err))
            log(' ', type(c).__name__, '->', res)
    except Exception:
        log('SCENARIO FAILED', traceback.format_exc().replace('\n', ' | ')[-700:])
