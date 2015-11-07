Wrye Bash
=========

###About

Wrye Bash is a mod management utility for Oblivion and Skyrim with a rich set
 of features. This is a fork of the Wrye Bash related code from the
 [SVN 3177 trunk revision][1].
 We are in the process of refactoring the code to eventually support more
 games, offering the same feature set for all of them.
 Please read the [Contributing](#contributing) section below if interested in
 contributing.

###Download

* [Oblivion Nexus][2]
* [Skyrim Nexus][3]
* [Github][4] (all releases)

Docs are included in the download but we are setting them up also online
 [here][5].

###Installation

* Short version: just use the installer, and install everything to their
 default locations.
* Long version: see the [General Readme][6] for information, and the
 [Advanced Readme][7] for even more details.

To run Wrye Bash from the latest `dev` code (download from [here][8])
you need:

* A game to manage (currently Oblivion or Skyrim)
* [Python 2.7](http://www.python.org/) (latest 2.7 is recommended)
* [wxPython 2.8.12.1 Unicode][9] (do **not** get a newer version)
* [pywin32 build 218 or newer](https://sourceforge.net/projects/pywin32/files/pywin32/)
for your Python
* [comtypes 0.6.2 or later](https://sourceforge.net/projects/comtypes/files/comtypes/)
for your Python

**NB**: the 32-bit versions are required even if you are on a 64-bit
operating system.

Refer to the readmes for [detailed instructions][6]. In short:

1. Install one of the supported games (Oblivion, Skyrim).
2. Install Python and plugins above.
3. Extract the downloaded Wrye Bash archive into your game folder.
4. Run Wrye Bash by double-clicking "Wrye Bash Launcher.pyw" in the new Mopy
 folder.

####WINE

Wrye Bash 306 runs on WINE - with some hiccups. In short:

1. Do not use the installer - instead wine-install the python prerequisites
above, then unzip/clone the python version in your game folder
2. Edit `Mopy/bash/balt.py` - add `canVista = False` just above the
[`def setUAC(button_,uac=True):`][10] so it becomes

 ```
...
canVista = False
def setUAC(button_,uac=True):
...
```

3. Run Bash as `wine python /path/to/Mopy/Wrye Bash Launcher.pyw`

For details see our [wiki article][11].
Wine issue: [#240][12]


###Contributing

To contribute to the code, fork the repo and set your fork up as
detailed in [\[git\] Syncing a Fork with the main repository][13].
A good starting point is the [currently worked on issues][14]
 (see also [issue 200][15] for some refactoring tasks we need help with).
The recommended way to code for Bash is Pycharm ([set up instructions][16]).
Please also read at least:

* **[\[github\] Branching Model & Using The Repository][17]**
* **[\[github\] Branching and merging to dev using rebase][18]**
* **[\[dev\] Coding Style][19]**

When ready do not issue a pull request - contact instead a member of the team
in the relevant issue and let them review. Then those branches can be pulled
from your fork and integrated with upstream. Once this is done a couple times
you get write rights.

####Main Branches

- [`dev`](https://github.com/wrye-bash/wrye-bash/tree/dev): the main development
 branch - approved commits end up here. _Do not directly push to this branch_ -
 push to your branches and contact someone from the owners team in the relevant
 issue.
- [`master`](https://github.com/wrye-bash/wrye-bash/tree/master): the production
 branch, contains stable releases. Use it _only_ as reference.
- [`utumno-wip`](https://github.com/wrye-bash/wrye-bash/tree/utumno-wip):
bleeding edge dev branch. Do have a look if interested in contributing or
testing very latest features/fixes.


  [1]: http://sourceforge.net/p/oblivionworks/code/3177/tree/
  [2]: http://www.nexusmods.com/oblivion/mods/22368/?tab=2&navtag=http%3A%2F%2Fwww.nexusmods.com%2Foblivion%2Fajax%2Fmodfiles%2F%3Fid%3D22368&pUp=1
  [3]: http://www.nexusmods.com/skyrim/mods/1840/?tab=2&navtag=http%3A%2F%2Fwww.nexusmods.com%2Fskyrim%2Fajax%2Fmodfiles%2F%3Fid%3D1840&pUp=1
  [4]: https://github.com/wrye-bash/wrye-bash/releases
  [5]: http://wrye-bash.github.io/
  [6]: http://wrye-bash.github.io/docs/Wrye%20Bash%20General%20Readme.html#install
  [7]: http://wrye-bash.github.io/docs/Wrye%20Bash%20Advanced%20Readme.html#install
  [8]: https://github.com/wrye-bash/wrye-bash/archive/dev.zip
  [9]: http://sourceforge.net/projects/wxpython/files/wxPython/2.8.12.1/wxPython2.8-win32-unicode-2.8.12.1-py27.exe
  [10]: https://github.com/wrye-bash/wrye-bash/blob/0a47238de9e7f46f55fe755f2744e2cea521f514/Mopy/bash/balt.py#L678
  [11]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Running-Wrye-Bash-on-WINE-%28Arch-Linux%29
  [12]: https://github.com/wrye-bash/wrye-bash/issues/240
  [13]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgit%5D-Syncing-a-Fork-with-the-main-repository
  [14]: https://github.com/wrye-bash/wrye-bash/issues?utf8=%E2%9C%93&q=sort%3Aupdated-desc%20is%3Aopen
  [15]: https://github.com/wrye-bash/wrye-bash/issues/200
  [16]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Set-up-Pycharm-for-wrye-bash
  [17]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-Model-&-Using-The-Repository
  [18]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-and-merging-to-dev-using-rebase
  [19]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Coding-Style
