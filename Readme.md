Wrye Bash
=========

### About

Wrye Bash is a mod management utility for games based on Bethesda's Creation
Engine, with a rich set of features.
This is a fork of the Wrye Bash related code from the
[SVN 3177 trunk revision][1].
We are in the process of refactoring the code to eventually support more games,
offering the same feature set for all of them.
Please read the [Contributing](#contributing) section below if interested in
contributing.

#### Supported Games

Here is a list of supported games with the minimal patch version that Bash was
tested on (previous versions or latest versions may or may not work):

* Oblivion (patch 1.2.0.416)
* Fallout 3 (patch 1.7.0.3)
* Fallout New Vegas (patch 1.4.0.525)
* Skyrim (patch 1.9.36.0)
* Enderal (patch 1.5.7.0)
* Fallout 4 (patch 1.10.138.0)
* Fallout 4 VR (patch 1.2.72.0)
* Skyrim Special Edition (patch 1.5.80.0)
* Skyrim VR (patch 1.4.15.0)

### Download

* [Oblivion Nexus][2]
* [Fallout 3 Nexus][3]
* [Fallout New Vegas Nexus][4]
* [Skyrim Nexus][5]
* [Enderal Nexus][30]
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
* [Python 2.7 32-bit](http://www.python.org/) (latest 2.7 is recommended)

**NB**: the 32-bit version is required even if you are on a 64-bit
operating system.

Once you have those, install the required packages by running:

```python
path/to/python.exe -m pip install -r requirements.txt
```

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

We are currently monitoring [this thread][17] at the AFK Mods forum and
[the Wrye Bash Discord][18].
Please be sure to ask there first before reporting an issue here. If asking for
help please provide the info detailed in our [Reporting a bug][19] wiki page.
In particular it is _essential_ you produce a [bashbugdump.log][20].

#### Latest betas

In the [second post][21] of the AFK Mods thread, as well as in the
`#wip-builds` channel on [Discord][22], there are links to the latest python
and standalone (exe) builds. Be sure to check those out for bleeding edge
bugfixes and enhancements. Feedback appreciated!

### Contributing

To contribute to the code, fork the repo and set your fork up as
detailed in [\[git\] Syncing a Fork with the main repository][23].
A good starting point is the [currently worked on issues][24]
 (see also [issue 200][25] for some refactoring tasks we need help with).
The recommended way to code for Bash is Pycharm ([set up instructions][26]).
Please also read at least:

* **[\[github\] Branching Model & Using The Repository][27]**
* **[\[github\] Branching and merging to dev using rebase][28]**
* **[\[dev\] Coding Style][29]**

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
- [`nightly`](https://github.com/wrye-bash/wrye-bash/tree/nightly):
bleeding edge branch. Commits land here for testing.


  [1]: http://sourceforge.net/p/oblivionworks/code/3177/tree/
  [2]: https://www.nexusmods.com/oblivion/mods/22368
  [3]: https://www.nexusmods.com/fallout3/mods/22934
  [4]: https://www.nexusmods.com/newvegas/mods/64580
  [5]: https://www.nexusmods.com/skyrim/mods/1840
  [6]: https://www.nexusmods.com/fallout4/mods/20032
  [7]: https://www.nexusmods.com/skyrimspecialedition/mods/6837
  [8]: https://github.com/wrye-bash/wrye-bash/releases
  [9]: http://wrye-bash.github.io/
  [10]: http://wrye-bash.github.io/docs/Wrye%20Bash%20General%20Readme.html#install
  [11]: http://wrye-bash.github.io/docs/Wrye%20Bash%20Advanced%20Readme.html#install
  [12]: https://github.com/wrye-bash/wrye-bash/archive/dev.zip
  [14]: https://github.com/wrye-bash/wrye-bash/blob/0a47238de9e7f46f55fe755f2744e2cea521f514/Mopy/bash/balt.py#L678
  [15]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Running-Wrye-Bash-on-WINE-%28Arch-Linux%29
  [16]: https://github.com/wrye-bash/wrye-bash/issues/240
  [17]: https://afkmods.com/index.php?/topic/4966-wrye-bash-all-games
  [18]: https://discord.gg/NwWvAFR
  [19]: https://github.com/wrye-bash/wrye-bash/wiki/[github]-Reporting-a-bug
  [20]: https://github.com/wrye-bash/wrye-bash/wiki/[github]-Reporting-a-bug#the-bashbugdumplog
  [21]: https://afkmods.com/index.php?/topic/4966-wrye-bash-all-games/&do=findComment&comment=166863
  [22]: https://discord.gg/NwWvAFR
  [23]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgit%5D-Syncing-a-Fork-with-the-main-repository
  [24]: https://github.com/wrye-bash/wrye-bash/issues?utf8=%E2%9C%93&q=sort%3Aupdated-desc%20is%3Aopen
  [25]: https://github.com/wrye-bash/wrye-bash/issues/200
  [26]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Set-up-Pycharm-for-wrye-bash
  [27]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-Model-&-Using-The-Repository
  [28]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-and-merging-to-dev-using-rebase
  [29]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Coding-Style
  [30]: https://www.nexusmods.com/enderal/mods/97
