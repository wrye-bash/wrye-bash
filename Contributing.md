# Contributing to Wrye Bash

:+1::tada: First off, thanks for taking the time to contribute! :tada::+1:

Wrye Bash is a mod management utility with a rich set of features. The following
is a set of guidelines for contributing to Wrye Bash and its packages.
You can contribute either by providing a good bug report, contributing code or
making a donation.
For basic info on installation and set up see our
[main readme](https://github.com/wrye-bash/wrye-bash) and links there.
In particular:

- [Installation](https://github.com/wrye-bash/wrye-bash#installation)
- [Questions & Feedback](https://github.com/wrye-bash/wrye-bash#questions--feedback-)
- [Latest betas](https://github.com/wrye-bash/wrye-bash#latest-betas)

## Reporting Bugs

**IMPORTANT**: Before posting an issue, be sure to ask at the official thread (linked
under [Questions & Feedback](https://github.com/wrye-bash/wrye-bash#questions--feedback-)
); maybe the bug is already fixed in some development version
or you are doing something wrong. Post an issue on github **ONLY** after doing so
and then making sure the bug is not already on the bug tracker by [searching on
the key elements of your problem](https://help.github.com/articles/searching-issues/)

### Asking for help / Posting issues

When asking for help (initially at the official forums thread linked to above)
please provide all of the following info:

* **Bug description** - be sure to include:
 - what you did (_step-by-step_),
 - what you expected, and
 - what happened.

* Any and every **error message** you encounter: please produce the
**BashBugDump.log** (see the section [below](#the-bashbugdumplog)). Failing to do so
will hinder debugging - post at least the contents of any `stdout/stderr` window
that pops up with errors (python tracebacks).

* Are you using a **bash.ini** ? If so, include its contents (in spoiler tags, please!).

* Is the problem related to the **Bashed Patch** ? If so include the following:
  * Your Load Order (in spoiler tags). Right click on a column header in the Mods tab > 'List Mods...'.
  * Your Bashed Tags (in spoiler tags). Right click on a column header in the Mods tab > 'List Bash Tags...'.
  * Your Bashed Patch config (in spoiler tags). Right click on the Bashed patch in the Mods tab > 'List Patch Config...'.

 To increase your chances your BP bug is fixed (to a number greater than 0) be
 sure to supply the **minimal load order and patch options that reproduce your
 bug.** That is, deselect all batch patch options and deactivate all the mods
 then try to pin down which options and which mods trigger the bug.

The rest of the info we need is also contained in **`bashbugdump.log`**. In
particular we need to know:

* **Your operating system!** If on Windows Vista or later and the game is in
the default directory (ex: *C:\Program Files (x86)\Bethesda Softworks\Oblivion*),
please install it somewhere else (like *C:\Games\Oblivion*). This can cause
lots of problems, due to UAC (User Account Control).

* **Wrye Bash version!** _Also_ specify if you are using Python Wrye Bash, or
Standalone Wrye Bash exe ( WBSA ). If you're using a development version, be
sure to include the *commit SHA*.

#### **The BashBugDump.log**

The `BashBugDump.log` is just a text file (loads into Windows Notepad), and the
contents can be pasted into forum posts (please use "spoiler tags"). It
contains precious information on your python install,
encodings etc - _you must add this to your report._ To generate it:

###### Python version

Launch `Wrye Bash Debug.bat` (recommended)  or fire up a command prompt, navigate to Mopy and issue:

    C:\path\to\Mopy>c:\path\to\Python27\python.exe "Wrye Bash Launcher.pyw" -d

NB: `C:\path\to\Mopy>"Wrye Bash Launcher.pyw" -d` alone won't work. You need to
include the full path to the python executable.

###### Standalone version

Fire up a command prompt, which will look similar to this:

    C:\Users\Username>

Ensure you know the full path to your Wrye Bash installation, and type
(changing `C:\path\to\mopy` accordingly):

    chdir /D "C:\path\to\Mopy"

Your command prompt should now read the equivalent of ..

    C:\path\to\Mopy>

Now type:

    "Wrye Bash.exe" -d

Wrye Bash should now launch, and doing it this way the output of errors will be
redirected to `Mopy/bashbugdump.log` and no more stdout/stderr windows will pop up.

Apart from the `bashbugdump.log` Bash may create a couple other log files in
the Mopy directory - see [here](https://github.com/wrye-bash/wrye-bash/wiki/[github]-Reporting-a-bug#bash-log-files)
for details.

## Contributing Code

I'm really glad you're reading this, because we need volunteer developers to
help this project come to fruition. Some outstanding issues we need help with
are:

1. Update patchers so Wrye Bash can process Skyrim's and Fallout4 files as it does for Oblivion
1. Add tests for patchers package - we are setting up a test repo here: https://github.com/wrye-bash/test_bash
1. Add tests for other sensitive areas (load order, refresh, BAIN etc)
1. Move on to newer python/wx python versions, initially wx classic 3.02
1. Update cosave code to work with script extenders other than OBSE
1. Update save files editing code for games other than Oblivion
1. Update CBash for games other than Oblivion. CBash repo: https://github.com/wrye-bash/CBash

Another good starting point is the
[currently worked on issues](https://github.com/wrye-bash/wrye-bash/issues?utf8=%E2%9C%93&q=sort%3Aupdated-desc%20is%3Aopen)
(see also [issue 200](https://github.com/wrye-bash/wrye-bash/issues/200) for
some refactoring tasks we need help with).

#### Set up

To contribute to the code, fork the repo and set your fork up as detailed in
[[git] Syncing a Fork with the main repository](https://github.com/wrye-bash/wrye-bash/wiki/%5Bgit%5D-Syncing-a-Fork-with-the-main-repository).
The recommended way to code for Bash is Pycharm
([set up instructions](https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Set-up-Pycharm-for-wrye-bash)).
Our wiki contains dev, git and github labelled articles to get you started with
setting up the repository and git basics. Please read at least:

* [[github] Branching Model & Using The Repository](https://github.com/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-Model-&-Using-The-Repository)
* [[github] Branching and merging to dev using rebase](https://github.com/wrye-bash/wrye-bash/wiki/%5Bgithub%5D-Branching-and-merging-to-dev-using-rebase)
* [[dev] Coding Style](https://github.com/wrye-bash/wrye-bash/wiki/%5Bdev%5D-Coding-Style)
* [[git] Commit guidelines](https://github.com/wrye-bash/wrye-bash/wiki/%5Bgit%5D-Commit-guidelines)

When ready: do not issue a pull request - contact instead a member of the team
in the relevant issue or mentioning him/her on your commit and let them review.
Then those branches can be pulled from your fork and integrated with upstream.
Once this is done a couple times you get *write* privileges.

#### Main Branches

* [dev](https://github.com/wrye-bash/wrye-bash/tree/dev): the main development
branch - approved commits end up here. Do not directly push to this branch -
push to your branches and contact someone from the owners team in the relevant
issue.
* [master](https://github.com/wrye-bash/wrye-bash/tree/master): the production
branch, contains stable releases. Use it only as reference.
* [utumno-wip](https://github.com/wrye-bash/wrye-bash/tree/utumno-wip):
bleeding edge dev branch. Do have a look if interested in contributing or
testing very latest features/fixes.

#### Governance Model

The Governance Model for Wrye-Bash is similar to that laid out for
[Git for Windows](https://git-for-windows.github.io/governance-model.html).
See that article for details.

## Donating

Last but not least you can make a difference to Wrye Bash by offering a small donation.
Your donation will motivate the expert software developers behind this project to keep
working on the complex and time consuming job of keeping Wrye Bash alive. You can
donate via paypal on the
[nexus sites](http://www.nexusmods.com/skyrimspecialedition/users/donate/?mode=straight&id=482689)
