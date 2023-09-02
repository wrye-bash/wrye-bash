<img align="left" src="Mopy/bash/images/bash.svg" width="120" alt="">

Wrye Bash
=========

[![Wrye Bash CI](https://github.com/wrye-bash/wrye-bash/workflows/Wrye%20Bash%20CI/badge.svg)](https://github.com/wrye-bash/wrye-bash/actions?query=workflow%3A%22Wrye+Bash+CI%22)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE.md)

### About

Wrye Bash is a mod management utility for games based on Bethesda's Creation
Engine, with a rich set of features. This is a fork of the Wrye Bash related
code from the [SVN 3177 trunk revision][1].
We are in the process of refactoring the code to eventually support more games,
offering the same feature set for all of them.
Please see our [Contributing.md][24] if interested in contributing.

#### Supported Games

Here is a list of supported games with the minimal patch version that Bash was
tested on (previous versions or latest versions may or may not work):

* Enderal (patch 1.6.4.0)
* Enderal: Special Edition (patch 2.0.12.4)
* Fallout 3 (patch 1.7.0.3)
* Fallout 4 (patch 1.10.163.0)
* Fallout 4 VR (patch 1.2.72.0)
* Fallout New Vegas (patch 1.4.0.525)
* Morrowind (very early support, patch 1.6.1820.0)
* Nehrim (patch 2.0.2.4)
* Oblivion (patch 1.2.0.416)
* Skyrim (patch 1.9.36.0)
* Skyrim Special Edition (patch 1.6.640.0)
* Skyrim VR (patch 1.4.15.0)
* Starfield (patch 1.7.23.0)

### Download

* [GitHub][3]
* [NexusMods][2]

Docs are included in the download, but we are also setting them up online
 [here][4].

### Installation

* Short version: just use the installer, and install everything to their
 default locations.
* Long version: see the [General Readme][5] for information, and the
 [Advanced Readme][6] for even more details.

To run Wrye Bash from the latest `dev` code (download from [here][7])
you need:

* A game to manage from the supported games.
* [Python 3.11 64-bit][16] (latest 3.11 is recommended)

**NB**: the 64-bit version is **required**. 32-bit operating systems are no
longer supported.

Once you have those, install the required packages by running:

```bash
py -3 -m pip install -r requirements.txt
```

*Note: you will have to use a more specific version for `py -3` if you have multiple versions of Python 3 installed.*

Refer to the readmes linked above for detailed instructions. In short:

1. Install one of the supported games (Oblivion, Skyrim, Fallout).
1. Install Python and plugins above.
1. Extract the downloaded Wrye Bash archive into your game folder.
1. Run Wrye Bash by double-clicking "Wrye Bash Launcher.pyw" in the new Mopy
   folder.

#### WINE

Since 306, Wrye Bash runs on WINE - with some hiccups. Please see our
[wiki article][8] for a detailed guide.

Relevant issue: [#240][9]

### Questions ? Feedback ?

We are currently monitoring [this thread][10] at the AFK Mods forum and
[the Wrye Bash Discord][11].
Please be sure to ask there first before reporting an issue here. If asking for
help please provide the info detailed in our [Reporting a bug][12] wiki page.
In particular, it is _essential_ you produce a [bashbugdump.log][13].

#### Latest betas

In the [second post][14] of the AFK Mods thread, as well as in the
`#wip-builds` channel on [Discord][11], there are links to the latest python
and standalone (exe) builds. Be sure to check those out for bleeding edge
bugfixes and enhancements. Feedback appreciated!

### Contributing

Please see our [dedicated Contributing.md][15] document for information on how
to contribute.

#### Main Branches

- [`dev`][17]: The main development branch - approved commits end up here.
 *Do not directly push to this branch* - push to your branches and contact
 a maintainer in the relevant issue.
- [`master`][18]: The production branch, contains stable releases. Use it
  *only* as reference.
- [`nightly`][19]: Bleeding edge branch. Commits land here for testing.


  [1]: http://sourceforge.net/p/oblivionworks/code/3177/tree/
  [2]: https://www.nexusmods.com/site/mods/591
  [3]: https://github.com/wrye-bash/wrye-bash/releases
  [4]: http://wrye-bash.github.io/
  [5]: http://wrye-bash.github.io/docs/Wrye%20Bash%20General%20Readme.html#install
  [6]: http://wrye-bash.github.io/docs/Wrye%20Bash%20Advanced%20Readme.html#install
  [7]: https://github.com/wrye-bash/wrye-bash/archive/dev.zip
  [8]: https://github.com/wrye-bash/wrye-bash/wiki/%5Bguide%5D-Running-Wrye-Bash-on-WINE-%28Arch-Linux%29
  [9]: https://github.com/wrye-bash/wrye-bash/issues/240
  [10]: https://afkmods.com/index.php?/topic/4966-wrye-bash-all-games
  [11]: https://discord.gg/NwWvAFR
  [12]: https://github.com/wrye-bash/wrye-bash/wiki/[github]-Reporting-a-bug
  [13]: https://github.com/wrye-bash/wrye-bash/wiki/[github]-Reporting-a-bug#the-bashbugdumplog
  [14]: https://afkmods.com/index.php?/topic/4966-wrye-bash-all-games/&do=findComment&comment=166863
  [15]: https://github.com/wrye-bash/wrye-bash/blob/dev/Contributing.md
  [16]: http://www.python.org
  [17]: https://github.com/wrye-bash/wrye-bash/tree/dev
  [18]: https://github.com/wrye-bash/wrye-bash/tree/master
  [19]: https://github.com/wrye-bash/wrye-bash/tree/nightly
