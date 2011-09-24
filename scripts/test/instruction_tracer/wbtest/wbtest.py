#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005, 2006, 2007, 2008, 2009 Wrye
#
# =============================================================================

import os
import subprocess
import sys
import win32api
import wx


class TestPanel(wx.Panel):
    def __init__(self, wxParent, runWryeBashFn, runOblivionFn):
        wx.Panel.__init__(self, wxParent)

        # state
        self._initialTest = True
        self._knownGoodInst = 1
        # initial value is approximate number of instructions it takes to quiesce the UI
        self._knownBadInst = 4400000
        self._crashed = False
        self._runWryeBashFn = runWryeBashFn
        self._runOblivionFn = runOblivionFn

        panelSizer = wx.BoxSizer(wx.VERTICAL)
        self._slider = wx.Slider(self, value=self._knownGoodInst, minValue=self._knownGoodInst,
                                 maxValue=self._knownBadInst,
                                 style=wx.SL_HORIZONTAL|wx.SL_AUTOTICKS|wx.SL_LABELS)
        panelSizer.Add(self._slider, 0, wx.EXPAND)

        instructionSizer = wx.BoxSizer(wx.VERTICAL)
        initialInstruction = "First, we'll verify our expectation that Oblivion should still work after executing only 1 instruction of Wrye Bash"
        self._instructionLabel = wx.StaticText(self, label=initialInstruction)
        instructionSizer.Add(self._instructionLabel, 0, wx.EXPAND)
        panelSizer.Add(instructionSizer, 1, wx.EXPAND|wx.ALL, 10)

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)

        self._runWryeBashButton = wx.Button(self, label="Run Wrye Bash")
        buttonSizer.Add(self._runWryeBashButton, 0, wx.ALIGN_CENTER_VERTICAL)
        self._runOblivionButton = wx.Button(self, label="Run Oblivion")
        buttonSizer.Add(self._runOblivionButton, 0, wx.ALIGN_CENTER_VERTICAL)

        decisionSizer = wx.BoxSizer(wx.VERTICAL)
        self._oblivionWorkedButton = wx.Button(self, label="Oblivion worked")
        decisionSizer.Add(self._oblivionWorkedButton, 0, wx.ALIGN_CENTER_HORIZONTAL)
        self._oblivionCrashedButton = wx.Button(self, label="Oblivion crashed")
        decisionSizer.Add(self._oblivionCrashedButton, 0, wx.ALIGN_CENTER_HORIZONTAL)
        buttonSizer.Add(decisionSizer, 0, wx.ALIGN_CENTER_VERTICAL)

        restoreSizer = wx.BoxSizer(wx.VERTICAL)
        self._nextButton = wx.Button(self, label="Do next iteration")
        restoreSizer.Add(self._nextButton, 0, wx.ALIGN_CENTER_HORIZONTAL)
        self._backButton = wx.Button(self, label="Whoops, go back")
        restoreSizer.Add(self._backButton, 0, wx.ALIGN_CENTER_HORIZONTAL)
        buttonSizer.Add(restoreSizer, 0, wx.ALIGN_CENTER_VERTICAL)

        self._doneButton = wx.Button(self, wx.ID_CLOSE, "Done")
        buttonSizer.Add(self._doneButton, 0, wx.ALIGN_CENTER_VERTICAL)

        panelSizer.Add(buttonSizer, 0, wx.ALIGN_CENTER_HORIZONTAL)

        # disable initially non-functional buttons
        self._runOblivionButton.Disable()
        self._oblivionWorkedButton.Disable()
        self._oblivionCrashedButton.Disable()
        self._nextButton.Disable()
        self._backButton.Disable()
        self._doneButton.Disable()
        
        self.SetSizer(panelSizer)
        self.Fit()

        # bind events
        self.Bind(wx.EVT_SLIDER, self._on_slider_update)
        self._runWryeBashButton.Bind(wx.EVT_BUTTON, self._on_run_wrye_bash_click)
        self._runOblivionButton.Bind(wx.EVT_BUTTON, self._on_run_oblivion_click)
        self._oblivionWorkedButton.Bind(wx.EVT_BUTTON, self._on_oblivion_worked_click)
        self._oblivionCrashedButton.Bind(wx.EVT_BUTTON, self._on_oblivion_crashed_click)
        self._nextButton.Bind(wx.EVT_BUTTON, self._on_next_click)
        self._backButton.Bind(wx.EVT_BUTTON, self._on_back_click)
        self._doneButton.Bind(wx.EVT_BUTTON, self._on_done_click)
  

    def _update_instructions(self, instStr):
        self._instructionLabel.SetLabel(instStr)
        self._instructionLabel.Wrap(self.GetSize()[0]-20)
        self.Layout()
        self._instructionLabel.Fit()
        self._instructionLabel.Wrap(self.GetSize()[0]-20)

    def _on_slider_update(self, event):
        self._sliderPos = self._slider.GetValue()
    def _on_run_wrye_bash_click(self, event):
        self._runWryeBashButton.Disable()
        self._update_instructions("Running Wrye Bash (if the Wrye Bash UI finishes loading, just close it)...")
        try:
            self._runWryeBashFn(self._slider.GetValue())
        except Exception as e:
            print e
            self._update_instructions("There was a problem running Wrye Bash: " + str(e))
            self._doneButton.Enable()
            return
        self._update_instructions("Ready to test Oblivion.")
        self._runOblivionButton.Enable()
    def _on_run_oblivion_click(self, event):
        self._runOblivionButton.Disable()
        self._update_instructions("Running Oblivion and waiting for it to crash/exit...")
        try:
            self._runOblivionFn()
        except Exception as e:
            print e
            self._update_instructions("There was a problem running Oblivion: " + str(e))
            self._doneButton.Enable()
            return
        self._update_instructions("Please select whether Oblivion crashed")
        self._oblivionWorkedButton.Enable()
        self._oblivionCrashedButton.Enable()
    def _on_oblivion_worked_click(self, event):
        self._crashed = False
        self._oblivionWorkedButton.Disable()
        self._oblivionCrashedButton.Disable()
        self._update_instructions("Click 'Next' when you are ready to start the next iteration, or 'Back' if you accidentally clicked the wrong button.")
        self._nextButton.Enable()
        self._backButton.Enable()
    def _on_oblivion_crashed_click(self, event):
        self._oblivionWorkedButton.Disable()
        self._oblivionCrashedButton.Disable()
        self._crashed = True
        self._update_instructions("Click 'Next' when you have restored a working Oblivion install with MOM and are ready to start the next iteration, or 'Back' if you accidentally clicked the wrong button.")
        self._nextButton.Enable()
        self._backButton.Enable()
    def _on_next_click(self, event):
        self._nextButton.Disable()
        self._backButton.Disable()
        # log status
        if self._crashed:
            # if it crashed, reduce knownBadInst to current slider value
            self._knownBadInst = self._slider.GetValue()
            print "Oblivion crashed after running WB to instruction %d" % self._knownBadInst
        else:
            # if it did not crash, raise knownGoodInst to current slider value
            self._knownGoodInst = self._slider.GetValue()
            print "Oblivion didn't crash after running WB to instruction %d" % self._knownGoodInst
        print "problem narrowed down to somewhere between %d and %d" % (self._knownGoodInst, self._knownBadInst)
        if self._knownBadInst <= self._knownGoodInst+10:
            self._update_instructions("This is close enough.  I can take it from here.  Please upload the BashBugDump.log file to my server at http://myk.gotdns.com/upload_form.html.  Thank you so much for this!")
            self._doneButton.Enable()
        else:
            # update slider and repeat test
            self._slider.SetRange(self._knownGoodInst, self._knownBadInst)
            if self._initialTest:
                self._update_instructions("Now we'll make sure Oblivion does crash after allowing the maximum number of instructions to execute.  If it doesn't, please contact me.")
                self._instructionLabel.Wrap(self.GetSize()[0])
                # set slider to max
                self._slider.SetValue(self._knownBadInst)
                self._initialTest = False
            else:
                self._update_instructions("Instruction ranges updated.  Ready to run next iteration.")
                # set slider halfway between knowns
                self._slider.SetValue((self._knownGoodInst+self._knownBadInst)/2)
            self._runWryeBashButton.Enable()
    def _on_back_click(self, event):
        self._nextButton.Disable()
        self._backButton.Disable()
        self._oblivionWorkedButton.Enable()
        self._oblivionCrashedButton.Enable()
    def _on_done_click(self, event):
        self.GetParent().Destroy()



if __name__ == '__main__':
    oblivionDir = "../oblivion"
    oblivionProg = "Oblivion.exe"
    wbDir = oblivionDir + "/Mopy"
    wbProg = "Wrye Bash Launcher.pyw"
    r, executable = win32api.FindExecutable(wbDir + "/" + wbProg)
    executable = win32api.GetLongPathName(executable)
    curCwd = os.getcwd()

    def runWryeBash(instructionLimit):
        args = '"%s" "%s" -d %d' % (executable, wbProg, instructionLimit)
        print "running %s" % args
        sys.stdout.flush()
        try:
            os.chdir(wbDir)
            subprocess.call(args, bufsize=1, stdout=sys.stdout, stderr=sys.stderr)
        finally:
            os.chdir(curCwd)

    def runOblivion():
        print "running %s" % oblivionProg
        sys.stdout.flush()
        try:
            os.chdir(oblivionDir)
            subprocess.call(oblivionProg, close_fds=True)
        finally:
            os.chdir(curCwd)

    app = wx.PySimpleApp()
    frame = wx.Frame(None, -1, "wbtest", size=(600,200))
    TestPanel(frame, runWryeBash, runOblivion)
    frame.Show(True)
    app.MainLoop()
