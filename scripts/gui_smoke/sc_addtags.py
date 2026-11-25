"""The add-tags button of the Mods details: opened by the mouse (left down) and from the keyboard (button click)."""
import os, sys, gc, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    import wx
    from bash import basher
    nb = frame.notebook._native_widget
    try:
        nb.SetSelection([nb.GetPageText(i) for i in range(nb.GetPageCount())].index('Mods')); pump(10)
        uil = frame.notebook.currentPage.uiList; uil.ClearSelected(); uil.SelectItem(uil.GetItem(2)); pump(8)
        md = next(o for o in gc.get_objects() if isinstance(o, basher.ModDetails))
        btn = md._add_tag_btn; nat = btn._native_widget
        log('mod shown in details:', md.file_info is not None, '| button enabled, shown:', nat.IsEnabled(), nat.IsShownOnScreen())
        def popups(): return [o for o in gc.get_objects() if type(o).__name__ == 'BashTagsPopup' and o._native_widget and o._native_widget.IsShown()]
        def close():
            for p in popups(): p._native_widget.Dismiss()
            pump(5)
        ev = wx.CommandEvent(wx.wxEVT_BUTTON, nat.GetId()); ev.SetEventObject(nat)
        handled = nat.GetEventHandler().ProcessEvent(ev); pump(6); ps = popups()
        log('button click event (what Space or Enter on the focused button sends): handled', handled, '| popups shown', len(ps),
            '| at the button:', bool(ps) and tuple(ps[0]._native_widget.GetScreenPosition()) == tuple(nat.GetScreenPosition()))
        close()
        ev = wx.MouseEvent(wx.wxEVT_LEFT_DOWN); ev.SetEventObject(nat); ev.SetPosition(wx.Point(4, 5))
        handled = nat.GetEventHandler().ProcessEvent(ev); pump(6); ps = popups()
        log('left down: handled (finished, so no click follows)', handled, '| popups shown', len(ps),
            '| at the mouse:', bool(ps) and tuple(ps[0]._native_widget.GetScreenPosition()) == tuple(nat.ClientToScreen(wx.Point(4, 5))))
        close()
        nat.SetFocus(); pump(4); wx.UIActionSimulator().Char(wx.WXK_SPACE); pump(12)
        log('real Space key with the button focused (focus may not work without a window manager): popups shown', len(popups()))
        close()
        uil.ClearSelected(); pump(6)
        ev = wx.CommandEvent(wx.wxEVT_BUTTON, nat.GetId()); ev.SetEventObject(nat); nat.GetEventHandler().ProcessEvent(ev); pump(6)
        log('after clearing the selection - mod still shown in details:', md.file_info is not None, '| popups', len(popups())); close()
        md.ClearDetails() if hasattr(md, 'ClearDetails') else md.SetFile(None); pump(4); nat.GetEventHandler().ProcessEvent(ev); pump(6)
        log('details cleared - mod shown:', md.file_info is not None, '| popups', len(popups()))
    except Exception:
        log('SCENARIO FAILED', traceback.format_exc().replace('\n', ' | ')[-700:])
