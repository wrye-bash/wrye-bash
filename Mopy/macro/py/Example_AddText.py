#User Python Macro for use with wx.stc

text = "Wrye Bash is Awesome!"

def macro(self):
    for i in range(0,10):
        # Do something a lot
        self.AddText("write something" + str(i) + '\n')
        if i == 5:
            self.AddText(text + '\n')