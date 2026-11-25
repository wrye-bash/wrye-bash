import wx, time, os
def pump(n=6, sleep=0.03):
    for _ in range(n):
        wx.Yield(); time.sleep(sleep)
    wx.Yield()
def dump_tree(win, out, depth=0, max_depth=30):
    try:
        label = win.GetLabel() if hasattr(win, 'GetLabel') else ''
    except Exception: label = ''
    label = label.replace('\n', '\\n')[:40]
    out.append('%s%s shown=%d pos=%s size=%s min=%s %r' % ('  ' * depth, type(win).__name__, win.IsShown(),
        tuple(win.GetPosition()), tuple(win.GetSize()), tuple(win.GetMinSize()), label))
    if depth < max_depth:
        for c in win.GetChildren():
            if not c.IsTopLevel(): dump_tree(c, out, depth + 1, max_depth)
def save_tree(win, path):
    out = []; dump_tree(win, out)
    with open(path, 'w') as f: f.write('\n'.join(out) + '\n')
    return len(out)

def press(code, modifiers=0):
    """Press and release a key for real. On wxMSW the simulator has no
    mapping for keypad Enter (it sends F3) - send an extended Return then."""
    if code == wx.WXK_NUMPAD_ENTER and wx.Platform == '__WXMSW__':
        import ctypes
        keybd_event = ctypes.windll.user32.keybd_event
        keybd_event(0x0D, 0, 1, 0) # VK_RETURN, KEYEVENTF_EXTENDEDKEY
        keybd_event(0x0D, 0, 1 | 2, 0) # and KEYEVENTF_KEYUP
        return True
    return wx.UIActionSimulator().Char(code, modifiers)

def activate(win):
    """Make the top level window of win the active one, as a user clicking
    its title bar would - on Windows a process may not bring its own windows
    to the front, the keys it simulates would go to another window."""
    win = getattr(win, '_native_widget', win)
    top = win if win.IsTopLevel() else wx.GetTopLevelParent(win)
    top.Raise(); pump(3)
    if wx.Platform == '__WXMSW__' and not top.IsActive():
        x, y, w, _h = top.GetScreenRect()
        sim = wx.UIActionSimulator()
        sim.MouseMove(x + w // 2, y + 10); pump(2)
        sim.MouseClick(); pump(6)
    return top.IsActive()
