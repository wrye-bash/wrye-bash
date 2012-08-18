#User Python Macro for use with wx.stc
# How to print various paths to use in macros or developement
import os
from ...bash import bosh #Add another dot '.' to go up two packages

def macro(self):
    print ('Hello World!')
    print ('5*6=%s' %(5*6))

    print (os.getcwd())

    print (bosh.dirs['app'])
    print (u'%s' %bosh.dirs['app'])
    
    print (bosh.dirs['bainData'])
    print (bosh.dirs['bash'])
    print (bosh.dirs['compiled'])
    print (bosh.dirs['converters'])
    print (bosh.dirs['corruptBCFs'])
    print (bosh.dirs['db'])
    print (bosh.dirs['defaultTweaks'])
    print (bosh.dirs['dupeBCFs'])
    print (bosh.dirs['images'])
    print (bosh.dirs['installers'])
    print (bosh.dirs['l10n'])
    print (bosh.dirs['mods'])
    print (bosh.dirs['modsBash'])
    print (bosh.dirs['mopy'])
    print (bosh.dirs['patches'])
    print (bosh.dirs['saveBase'])
    print (bosh.dirs['templates'])
    print (bosh.dirs['tweaks'])
    print (bosh.dirs['userApp'])

    print (bosh.tooldirs['PhotoshopPath'])
    print (bosh.tooldirs['GIMP'])
    print (bosh.tooldirs['MaxPath'])
    print (bosh.tooldirs['BlenderPath'])
    print (bosh.tooldirs['NPP'])

    print (bosh.inisettings['Tes4GeckoJavaArg'])