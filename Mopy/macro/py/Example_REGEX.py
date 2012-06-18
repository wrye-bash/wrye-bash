#User Python Macro for use with wx.stc
# Dialog/Widget and Regular Expression Example
import os
import wx
import re
import wx.lib.dialogs

def macro(self):
    str = self.GetText()
    findall = re.findall(r'SelectSubPackage\s*".*"', str)

    # If-statement after search() tests if it succeeded
    if findall:
        foundlist = findall
        message = ''
        for textfound in foundlist:#format for dialog
            message += textfound
            message += '\n'

        dialog = wx.lib.dialogs.ScrolledMessageDialog(self, u'%s' %message, u'SelectSubPackage\s*".*"', size=(500, 400))
        dialog.SetIcon(wx.Icon(self.imgstcDir + os.sep + u'regex16.png', wx.BITMAP_TYPE_PNG))
        dialog.ShowModal()
        dialog.Destroy()
    else:
        wx.MessageBox(u'REGEX\nSelectSubPackage\s*".*"\n\nDidn\'t Find Anything', u'', wx.OK|wx.ICON_EXCLAMATION)