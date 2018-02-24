Wrye Bash
=========

### About

Wrye Bash is a mod management utility for Oblivion, Fallout 3, Fallout NV, Skyrim,
 Fallout 4 and Skyrim Special Edition, with a rich set of features.
 This is a fork of the Wrye Bash related code from the
 [SVN 3177 trunk revision][1].
 We are in the process of refactoring the code to eventually support more games,
 offering the same feature set for all of them.
 Please read the [Contributing](#contributing) section below if interested in
 contributing.

#### Supported Games

Here is a list of supported games with the minimal patch version that Bash was
tested on (previous versions or latest versions may or may not work):

* Oblivion (patch 1.2.0416)
* Fallout 3 (patch 1.7.0.3)
* Fallout New Vegas (patch 1.4.0.525)
* Skyrim (patch 1.9.36.0)
* Fallout 4 (patch 1.10.50.01)
* Skyrim Special Edition (patch 1.5.23.08)

### Download

* [Oblivion Nexus][2]
* [Fallout 3][3]
* [Fallout New Vegas][4]
* [Skyrim Nexus][5]
* [Fallout 4 Nexus][6]
* [Skyrim Special Edition Nexus][7]
* [Github][8] (all releases)

Docs are included in the download but we are setting them up also online
 [here][9].

### Installation

* Short version: just use the installer, and install everything to their
 default locations.
* Long version: see the [General Readme][10] for information, and the
 [Advanced Readme][11] for even more details.

To run Wrye Bash from the latest `dev` code (download from [here][12])
you need:

* A game to manage from the supported games.
* [Python 2.7](http://www.python.org/) (latest 2.7 is recommended)
* [wxPython 2.8.12.1 Unicode][13] (do **not** get a newer version)
* [pywin32 build 220 or newer](https://sourceforge.net/projects/pywin32/files/pywin32/)
for your Python
* [comtypes 0.6.2 or later](https://sourceforge.net/projects/comtypes/files/comtypes/)
for your Python
* Optionally [scandir](https://pypi.python.org/pypi/scandir) - recommended.

**NB**: the 32-bit versions are required even if you are on a 64-bit
operating system.

Refer to the readmes for [detailed instructions][12]. In short:

1. Install one of the supported games (Oblivion, Skyrim, Fallout).
2. Install Python and plugins above.
3. Extract the downloaded Wrye Bash archive into your game folder.
4. Run Wrye Bash by double-clicking "Wrye Bash Launcher.pyw" in the new Mopy
 folder.

#### WINE

Wrye Bash 306 runs on WINE - with some hiccups. In short:

1. Do not use the installer - instead wine-install the python prerequisites
above, then unzip/clone the python version in your game folder
2. Edit `Mopy/bash/balt.py` - add `canVista = False` just above the
[`def setUAC(button_,uac=True):`][14] so it becomes

 ```
...
canVista = False
def setUAC(button_,uac=True):
...
```

3. Run Bash as `wine python /path/to/Mopy/Wrye Bash Launcher.pyw`

For details see our [wiki article][15].
Wine issue: [#240][16]

### Questions ? Feedback ?

We are currently monitoring [this thread][17] at the Bethesda.net SSE forums,
for all supported games - or alternatively [this thread][28], at AFK mods.
Please be sure to ask there first before reporting an issue here. If asking for
help please provide the info detailed in our [Reporting a bug][18] wiki page.
In particular it is _essential_ you produce a [bashbugdump.log][19].

#### Latest betas

In the [second post][20] of the Oblivion thread there are links to latest
python and standalone (exe) builds. Be sure to check those out for bleeding
edge bugfixes and enhancements. Feedback appreciated!

### Contributing

To contribute to the code, fork the repo and set your fork up as
detailed in [\[git\] Syncing a Fork with the main repository][21].
A good starting point is the [currently worked on issues][22]
 (see also [issue 200][23] for some refactoring tasks we need help with).
The recommended way to code for Bash is Pycharm ([set up instructions][24]).
Please also read at least:

* **[\[github\] Branching Model & Using The Repository][25]**
* **[\[github\] Branching and merging to dev using rebase][26]**
* **[\[dev\] Coding Style][27]**

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
  [2]: http://www.nexusmods.com/oblivion/mods/22368
  [3]: https://www.nexusmods.com/fallout3/mods/22934
  [4]: https://www.nexusmods.com/newvegas/mods/64580
  [5]: http://www.nexusmods.com/skyrim/mods/1840
  [6]: http://www.nexusmods.com/fallout4/mods/20032
  [7]: http://www.nexusmods.com/skyrimspecialedition/mods/6837
  [8]: https://github.com/wrye-bash/wrye-bash/releases
  [9]: http://wrye-bash.github.io/
  [10]: http://wrye-bash.github.io/docs/Wrye%20Bash%20General%20Readme.html#install
  [11]: http://wrye-bash.github.io/docs/Wrye%20Bash%20Advanced%20Readme.html#install
  [12]: https://github.com/wrye-bash/wrye-bash/archive/dev.zip
  [13]: http://sourceforge.net/projects/wxpython/files/wxPython/2.8.12.1/wxPython2.8-win32-unicode-2.8.12.1-py27.exe
  [14]: https://github.com/wrye-bash/wrye-bash/blob/0a47238de9e7f46f55fe755f2744e2cea521f514/Mopy/bash/balt.py#L678
  [15]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Running-Wrye-Bash-on-WINE-%28Arch-Linux%29
  [16]: https://github.com/wrye-bash/wrye-bash/issues/240
  [17]: https://bethesda.net/community/topic/38798/relz-wrye-bash-oblivion-skyrim-skyrim-se-fallout-4
  [18]: https://github.com/wrye-bash/wrye-bash/wiki/[github]-Reporting-a-bug
  [19]: https://github.com/wrye-bash/wrye-bash/wiki/[github]-Reporting-a-bug#the-bashbugdumplog
  [20]: https://bethesda.net/community/post/200780
  [21]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgit%5D-Syncing-a-Fork-with-the-main-repository
  [22]: https://github.com/wrye-bash/wrye-bash/issues?utf8=%E2%9C%93&q=sort%3Aupdated-desc%20is%3Aopen
  [23]: https://github.com/wrye-bash/wrye-bash/issues/200
  [24]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Set-up-Pycharm-for-wrye-bash
  [25]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-Model-&-Using-The-Repository
  [26]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-and-merging-to-dev-using-rebase
  [27]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Coding-Style
  [28]: https://afkmods.iguanadons.net/index.php?/topic/4966-wrye-bash-all-games
