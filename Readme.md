Wrye Bash
=========

### About

Wrye Bash is a mod management utility for Oblivion and Skyrim with a rich set
 of features. This is a fork of the Wrye Bash related code from the
 [SVN 3177 trunk revision][1].
 We are in the process of refactoring the code to eventually support more
 games, offering the same feature set for all of them.
 Please read the [Contributing](#contributing) section below if interested in
 contributing.

#### Supported Games

Here is a list of supported games with the minimal patch version that Bash was
tested on (previous versions or latest versions may or may not work):

* Oblivion (patch 1.2.0416)
* Skyrim (patch 1.9.32.0.8)
* Fallout 4 (patch 1.8.7.0)
* Skyrim Special Edition (patch 1.2.39.0.8)

### Download

* [Oblivion Nexus][2]
* [Skyrim Nexus][3]
* [Fallout 4 Nexus][4]
* [Skyrim Special Edition Nexus][5]
* [Github][6] (all releases)

Docs are included in the download but we are setting them up also online
 [here][7].

### Installation

* Short version: just use the installer, and install everything to their
 default locations.
* Long version: see the [General Readme][8] for information, and the
 [Advanced Readme][9] for even more details.

To run Wrye Bash from the latest `dev` code (download from [here][10])
you need:

* A game to manage from the supported games.
* [Python 2.7](http://www.python.org/) (latest 2.7 is recommended)
* [wxPython 2.8.12.1 Unicode][11] (do **not** get a newer version)
* [pywin32 build 220 or newer](https://sourceforge.net/projects/pywin32/files/pywin32/)
for your Python
* [comtypes 0.6.2 or later](https://sourceforge.net/projects/comtypes/files/comtypes/)
for your Python

**NB**: the 32-bit versions are required even if you are on a 64-bit
operating system.

Refer to the readmes for [detailed instructions][8]. In short:

1. Install one of the supported games (Oblivion, Skyrim).
2. Install Python and plugins above.
3. Extract the downloaded Wrye Bash archive into your game folder.
4. Run Wrye Bash by double-clicking "Wrye Bash Launcher.pyw" in the new Mopy
 folder.

#### WINE

Wrye Bash 306 runs on WINE - with some hiccups. In short:

1. Do not use the installer - instead wine-install the python prerequisites
above, then unzip/clone the python version in your game folder
2. Edit `Mopy/bash/balt.py` - add `canVista = False` just above the
[`def setUAC(button_,uac=True):`][12] so it becomes

 ```
...
canVista = False
def setUAC(button_,uac=True):
...
```

3. Run Bash as `wine python /path/to/Mopy/Wrye Bash Launcher.pyw`

For details see our [wiki article][13].
Wine issue: [#240][14]

### Questions ? Feedback ?

We are currently monitoring [this thread][15] at the Bethesda.net SSE forums,
for all supported games. Please address your comments there. If reporting a bug
please see our "Reporting a bug" [wiki page][16]. It is essential you produce
a [bashbugdump.log][17] to get a chance your bug is fixed.

#### Latest betas

In the [second post][18] of the Oblivion thread there are links to latest
python and standalone (exe) builds. Be sure to check those out for bleeding
edge bugfixes and enhancements. Feedback appreciated!

### Contributing

To contribute to the code, fork the repo and set your fork up as
detailed in [\[git\] Syncing a Fork with the main repository][19].
A good starting point is the [currently worked on issues][20]
 (see also [issue 200][21] for some refactoring tasks we need help with).
The recommended way to code for Bash is Pycharm ([set up instructions][22]).
Please also read at least:

* **[\[github\] Branching Model & Using The Repository][23]**
* **[\[github\] Branching and merging to dev using rebase][24]**
* **[\[dev\] Coding Style][25]**

When ready do not issue a pull request - contact instead a member of the team
in the relevant issue and let them review. Then those branches can be pulled
from your fork and integrated with upstream. Once this is done a couple times
you get write rights.

#### Main Branches

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
  [4]: http://www.nexusmods.com/fallout4/mods/20032
  [5]: http://www.nexusmods.com/skyrimspecialedition/mods/6837
  [6]: https://github.com/wrye-bash/wrye-bash/releases
  [7]: http://wrye-bash.github.io/
  [8]: http://wrye-bash.github.io/docs/Wrye%20Bash%20General%20Readme.html#install
  [9]: http://wrye-bash.github.io/docs/Wrye%20Bash%20Advanced%20Readme.html#install
  [10]: https://github.com/wrye-bash/wrye-bash/archive/dev.zip
  [11]: http://sourceforge.net/projects/wxpython/files/wxPython/2.8.12.1/wxPython2.8-win32-unicode-2.8.12.1-py27.exe
  [12]: https://github.com/wrye-bash/wrye-bash/blob/0a47238de9e7f46f55fe755f2744e2cea521f514/Mopy/bash/balt.py#L678
  [13]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Running-Wrye-Bash-on-WINE-%28Arch-Linux%29
  [14]: https://github.com/wrye-bash/wrye-bash/issues/240
  [15]: https://bethesda.net/community/topic/38798/relz-wrye-bash-oblivion-skyrim-skyrim-se-fallout-4
  [16]: https://github.com/wrye-bash/wrye-bash/wiki/[github]-Reporting-a-bug
  [17]: https://github.com/wrye-bash/wrye-bash/wiki/[github]-Reporting-a-bug#the-bashbugdumplog
  [18]: http://forums.bethsoft.com/topic/1606578-wrye-bash-thread-111/#entry25216860
  [19]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgit%5D-Syncing-a-Fork-with-the-main-repository
  [20]: https://github.com/wrye-bash/wrye-bash/issues?utf8=%E2%9C%93&q=sort%3Aupdated-desc%20is%3Aopen
  [21]: https://github.com/wrye-bash/wrye-bash/issues/200
  [22]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Set-up-Pycharm-for-wrye-bash
  [23]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-Model-&-Using-The-Repository
  [24]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-and-merging-to-dev-using-rebase
  [25]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Coding-Style
