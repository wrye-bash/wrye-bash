#User Python Macro for use with wx.stc
# Call Multiple Functions Example.
# Shows both WizBAINStyledTextCtrl class functions and the STC builtin functions can be used together.
# Rect Selection Example.

def macro(self):
    self.BeginUndoAction()          #STC func
    self.OnSelectNone(self)         #WizBAIN func
    #Assuming the document is padded with chars at least this much...
    #s = start of rect selection, where the caret is at when executing the macro...
    #e = end of rect selection
    #* = selected stuff
    '''
    #   s********   #
    #   *********   #
    #   *********   #
    #   *********   #
    #   *********   #
    #   ********e   #
    '''

    '''
    #   Case "01"   #
    #       Break   #
    #   Case "02"   #
    #       Break   #
    #   Case "03"   #
    #       Break   #
    '''
    for i in range(0,9):
        self.CharRightRectExtend()
    for i in range(0,5):
        self.LineDownRectExtend()
    self.OnShowAutoCompleteBox(self)#WizBAIN func
    # self.DeleteBack()             #STC func
    self.EndUndoAction()            #STC func

