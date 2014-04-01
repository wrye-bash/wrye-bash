Wrye Bash
=========
###About

Wrye Bash is a mod management utility for Oblivion and Skyrim with a rich set
 of features. This is a fork of the Wrye Bash related code from
 [the SVN repository](http://sourceforge.net/p/oblivionworks/code/HEAD/tree/).
 We are in the process of finalizing the move and then we aim to refactor the
 code to eventually support more games, offering the same feature set for all of
 them. Please read the _Contributing_ section below if interested in
 contributing.

Docs are included in the download but we are setting them up also online
 [here][2].

###Installation

To run Wrye Bash from the latest `dev` code (download from [here]
(https://github.com/wrye-bash/wrye-bash/archive/dev.zip)) you need:

* A game to manage (currently Oblivion or Skyrim)
* Python 2.7 (latest 2.7 is recommended): http://www.python.org/
* wxPython 2.8.12.1 Unicode (do **not** get a newer version): [wxPython]
(http://sourceforge.net/projects/wxpython/files/wxPython/2.8.12.1/wxPython2.8-win32-unicode-2.8.12.1-py27.exe
 "wxPython 2.8.12.1")
* pywin32 build 218 or newer for your Python:
 https://sourceforge.net/projects/pywin32/files/pywin32/
* comtypes 0.6.2 or later for your Python:
 https://sourceforge.net/projects/comtypes/files/comtypes/

Refer to the readmes for [detailed instructions][1]. In short:

1. Install one of the supported games. Oblivion, Skyrim.
2. Install Python and plugins above.
3. Extract the downloaded Wrye Bash archive into your game folder.
4. Run Wrye Bash by double-clicking "Wrye Bash Launcher.pyw" in the new Mopy
 folder.

###Contributing

Please read at least:

<ul>
    <li> <strong><a
	href="/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-Model-&amp;-Using-The-Repository">
	[github] Branching Model &amp; Using The Repository</a></strong>
    </li>
    <li>
      <strong><a
	  href="/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-and-merging-to-dev-using-rebase">
	  [github] Branching and merging to dev using rebase</a></strong>
    </li>
    <li>
      <strong><a
	  href="/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Coding-Style">
	  [dev] Coding Style</a></strong>
    </li>
  </ul>

The `dev` branch forks at the [SVN 3177 trunk revision]
(http://sourceforge.net/p/oblivionworks/code/3177/tree/).

Some branches have experimental work going on geared towards [Python 3.3+]
(http://www.python.org/).
 So in addition to the software cited above you may need [wxPython Classic 3.0]
 (http://wxpython.kosoftworks.com/preview/20140104/
 "Preview Build fixes compiled issues on MSWindows until main wxPython page
 gets updated") and [wxPython Project Phoenix(Python3+)]
 (http://wxpython.org/Phoenix/snapshot-builds/
 "if developing for the phoenix refactoring")

####Main Branches

- [`dev`](https://github.com/wrye-bash/wrye-bash/tree/dev): the main development
 branch - approved commits end up here. _Do not directly push to this branch_ -
 push to your branches and contact someone from the owners team in the relevant
 issue.
- [`master`](https://github.com/wrye-bash/wrye-bash/tree/master): the production
 branch, contains stable releases. Use it _only_ as reference.


[1]: http://wrye-bash.github.io/docs/Wrye%20Bash%20General%20Readme.html#install
[2]: https://github.com/wrye-bash/wrye-bash.github.io
