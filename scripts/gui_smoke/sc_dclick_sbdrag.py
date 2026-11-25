"""Double clicks that are no longer finished, and a status bar button dragged and clicked with the real mouse."""
import os, sys, gc, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import pump
def run(frame, shot, log, auto):
    import wx
    from bash import basher, bass
    nb = frame.notebook._native_widget
    def tab(t): nb.SetSelection([nb.GetPageText(i) for i in range(nb.GetPageCount())].index(t)); pump(10)
    def cur(): return nb.GetPageText(nb.GetSelection())
    try:
        # 1. double click on a master in the Mods details -> jumps to it
        tab('Mods'); uil = frame.notebook.currentPage.uiList
        delta = [uil.GetItem(k) for k in range(uil.item_count) if 'Delta' in str(uil.GetItem(k))][0]
        uil.ClearSelected(); uil.SelectItem(delta); pump(8)
        md = next(o for o in gc.get_objects() if isinstance(o, basher.ModDetails))
        ml = md.uilist; glist = ml._UIList__gList; nat = glist._native_widget
        names = [str(ml.GetItem(k)) for k in range(ml.item_count)]
        row = [k for k in range(ml.item_count) if 'Alpha' in str(ml.data_store[ml.GetItem(k)].curr_name)][0]
        rect = nat.GetItemRect(row); pt = wx.Point(rect.x + 20, rect.y + rect.height // 2)
        ml.mouse_index = ml.GetItem(row)
        ev = wx.MouseEvent(wx.wxEVT_LEFT_DCLICK); ev.SetPosition(pt); ev.SetEventObject(nat)
        handled = nat.GetEventHandler().ProcessEvent(ev); pump(8)
        log('masters of Delta Patch:', len(names), '| double click on the Alpha master: passed on to the control (not finished):', not handled or ev.GetSkipped(),
            '| selected in the Mods list now:', [str(x) for x in uil.GetSelected()])
        # 2. double click in the plugin filter of the Installers details
        tab('Installers'); il = frame.notebook.currentPage.uiList
        il.ClearSelected(); il.SelectItem([il.GetItem(k) for k in range(il.item_count) if 'Second' in str(il.GetItem(k))][0]); pump(10)
        det = next(o for o in gc.get_objects() if isinstance(o, basher.InstallersDetails)); en = det.gEspmList._native_widget
        ev = wx.MouseEvent(wx.wxEVT_LEFT_DCLICK); ev.SetPosition(wx.Point(30, 8)); ev.SetEventObject(en)
        handled = en.GetEventHandler().ProcessEvent(ev); pump(6)
        log('plugin filter double click on', repr(en.GetString(0)), '(not installed): passed on:', not handled or ev.GetSkipped(), '| tab still', cur())
        # 3. status bar buttons with the real mouse: a click, then a drag over the next button
        tab('Mods'); sb = frame.statusBar; sim = wx.UIActionSimulator()
        btns = list(sb._visible_buttons.values()); log('status bar buttons:', len(btns), [type(b).__name__ for b in btns][:6])
        clicks = []
        for b in btns: b.sb_click = lambda _b=b: clicks.append(type(_b).__name__)
        def centre(b): r = b._native_widget.GetScreenRect(); return r.x + r.width // 2, r.y + r.height // 2
        order0 = list(sb._visible_buttons)
        x, y = centre(btns[1]); sim.MouseMove(x, y); pump(3); sim.MouseDown(wx.MOUSE_BTN_LEFT); pump(3); sim.MouseUp(wx.MOUSE_BTN_LEFT); pump(6)
        log('real click on the second button -> clicks', clicks, '| order unchanged:', list(sb._visible_buttons) == order0)
        del clicks[:]; x2, y2 = centre(btns[2])
        sim.MouseMove(x, y); pump(3); sim.MouseDown(wx.MOUSE_BTN_LEFT); pump(3)
        for k in range(1, 7): sim.MouseMove(x + (x2 - x) * k // 6, y); pump(2)
        sim.MouseUp(wx.MOUSE_BTN_LEFT); pump(8)
        order1 = list(sb._visible_buttons)
        log('real drag of the second button over the third -> clicks', clicks, '| order changed:', order1 != order0,
            '| second and third swapped:', order1[1:3] == order0[2:0:-1], '| dragging state reset:', sb.dragging == wx.NOT_FOUND and not sb.moved)
        del clicks[:]; b = sb._visible_buttons[order1[0]]; x, y = centre(b); sim.MouseMove(x, y); pump(3); sim.MouseDown(wx.MOUSE_BTN_LEFT); pump(3); sim.MouseUp(wx.MOUSE_BTN_LEFT); pump(6)
        log('a click after the drag still clicks once:', clicks)
        bass.settings['bash.statusbar.order'][:] = [u for u in bass.settings['bash.statusbar.order']]
    except Exception:
        log('SCENARIO FAILED', traceback.format_exc().replace('\n', ' | ')[-900:])
