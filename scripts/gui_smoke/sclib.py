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
