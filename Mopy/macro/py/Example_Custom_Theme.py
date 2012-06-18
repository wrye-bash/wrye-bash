#User Python Macro for use with wx.stc
# Custom Theme Example for Python or WizBAIN lexers
import os
import wx
import wx.stc as stc

def macro(self):
    if wx.Platform == '__WXMSW__':
        faces = { 'times': 'Times New Roman',
                  'mono' : 'Courier New',
                  'helv' : 'Arial',
                  'other': 'Comic Sans MS',
                  'size' : 10,
                  'size2': 8,
                 }
    else:
        faces = { 'times': 'Times',
                  'mono' : 'Courier',
                  'helv' : 'Helvetica',
                  'other': 'new century schoolbook',
                  'size' : 12,
                  'size2': 10,
                 }

    # Global default styles for all languages
    self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#000000,back:#F6F68C,face:%(mono)s,size:%(size)d' % faces)

    self.ClearDocumentStyle()
    self.StyleClearAll()

    self.SetCaretLineBackground('#959595')
    self.SetCaretForeground('#000000')

    self.rmousegesture.SetGesturePen('#C6C63C', 5)

    #Set the colours used as a chequerboard pattern in the fold margin
    #Sometimes Visually, this is glitchy looking when moving the window with colors other than default.
    self.SetFoldMarginHiColour(True, '#FFFFFF')
    self.SetFoldMarginColour(True, '#E6E64C')

    ### self.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#F6F68C,face:Daedric,size:12')
    self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     'fore:#000000,back:#F6F68C,face:%(mono)s,size:%(size)d' % faces)
    self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#222222,back:#C6C63C')
    self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  'fore:#000000,back:#C6C63C,bold,face:%(mono)s,size:%(size2)d')
    # self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, 'fore:#1EFF00,back:#1EFF00')
    self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  'fore:#0000FF,back:#F6F68C,bold')
    self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    'fore:#FF0000,back:#F6F68C,bold')

    self.SetWhitespaceForeground(True,'#000000')
    self.SetWhitespaceBackground(False,'#000000')

    self.SetSelForeground(False,  '#FFFFCC')
    self.SetSelBackground(True,  '#707070')

    # # Python styles
    self.StyleSetSpec(stc.STC_P_DEFAULT,        'fore:#000000,back:#F6F68C,face:%(mono)s,size:%(size)d' % faces)
    self.StyleSetSpec(stc.STC_P_COMMENTLINE,    'fore:#000000,back:#E6E64C')
    self.StyleSetSpec(stc.STC_P_NUMBER,         'fore:#FF0000,back:#F6F68C')
    self.StyleSetSpec(stc.STC_P_STRING,         'fore:#F0712E,back:#F6F68C')
    self.StyleSetSpec(stc.STC_P_CHARACTER,      'fore:#F0712E,back:#F6F68C')
    self.StyleSetSpec(stc.STC_P_WORD,           'fore:#000080,back:#F6F68C,bold')
    self.StyleSetSpec(stc.STC_P_WORD2,          'fore:#0000BB,back:#F6F68C,bold')
    self.StyleSetSpec(stc.STC_P_TRIPLE,         'fore:#FF9000,back:#F6F68C')
    self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,   'fore:#E6DB74,back:#F6F68C')
    # self.StyleSetSpec(stc.STC_P_CLASSNAME,      'fore:#FFFFFF,back:#F6F68C,bold,underline')
    # self.StyleSetSpec(stc.STC_P_DEFNAME,        'fore:#A6E22E,back:#F6F68C,bold')
    self.StyleSetSpec(stc.STC_P_OPERATOR,       'fore:#000080,back:#F6F68C,bold')
    # self.StyleSetSpec(stc.STC_P_IDENTIFIER,     'fore:#66D9EF,back:#F6F68C')
    self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,   'fore:#000000,back:#FFFFCC,italic')
    self.StyleSetSpec(stc.STC_P_STRINGEOL,      'fore:#000000,back:#FF0000,eol')
    # self.StyleSetSpec(stc.STC_P_DECORATOR,      'fore:#BBBBBB,back:#000000')

    self.StyleSetHotSpot(stc.STC_P_WORD, True)  #This keeps the hotspots active when moused over
    self.StyleSetHotSpot(stc.STC_P_WORD2, True)

    self.Colourise(0, self.GetLength())

    #Folder Margin
    self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_ARROWDOWN, '#000000' , '#C6C63C')
    self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_ARROW,     '#000000' , '#C6C63C')
    self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY,     '#000000' , '#C6C63C')
    self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY,     '#000000' , '#C6C63C')
    self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY,     '#000000' , '#C6C63C')
    self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY,     '#000000' , '#C6C63C')
    self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY,     '#000000' , '#C6C63C')

    # Change the caretline bookmark image to something more fitting the theme
    #self.MarkerDefineBitmap(0, wx.Image(self.imgstcDir + os.sep + '..' + os.sep + 'bash_16.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap())
