"""Drop this script in Mopy and double click it to get lines and files count"""

import os
import pkgutil

# noinspection PyDefaultArgument
import re

def _findAllBashModules(files=[], bashPath=None, cwd=None,
                        exts=('.py', '.pyw'), exclude=(u'chardet',),
                        _firstRun=False):
    """Return a list of all Bash files as relative paths to the Mopy
    directory.

    :param files: files list cache - populated in first run. In the form: [
    u'Wrye Bash Launcher.pyw', u'bash\\balt.py', ..., u'bash\\__init__.py',
    u'bash\\basher\\app_buttons.py', ...]
    :param bashPath: the relative path from Mopy
    :param cwd: initially C:\...\Mopy - but not at the time def is executed !
    :param exts: extensions to keep in listdir()
    :param exclude: tuple of excluded packages
    :param _firstRun: internal use
    """
    if not _firstRun and files:
        return files # cache, not likely to change during execution
    cwd = cwd or os.getcwdu()
    files.extend([os.path.join((bashPath or u''), m) for m in
                  os.listdir(cwd) if m.lower().endswith(exts)])
    # find subpackages -- p=(module_loader, name, ispkg)
    for p in pkgutil.iter_modules([cwd]):
        if not p[2] or p[1] in exclude: continue
        _findAllBashModules(
            files, bashPath.join(p[1]) if bashPath else u'bash',
            cwd=os.path.join(cwd, p[1]), _firstRun=True)
    return files

_re_str = re.compile(u'' r"Mel(Opt|Truncated)?Struct(\(b'[^']+',) ?u?'([^']+)'")
# noinspection PyDefaultArgument
class _Lines(object):

    def __init__(self):
        self.non_blank_count = 0
        self._files = 0

    excl = {u'bosh', u'basher', u'gui', u'env', u'tests', u'getlineslength.py',
            u'balt.py', u'barb.py', u'barg.py', u'bash.py', u'bass.py',
            u'belt.py', u'bolt.py', u'bush.py', u'exception.py', u'fomod.py',
            u'ini_files.py', u'initialization.py', u'load_order.py',
            u'localize.py', u'mod_files.py', u'parsers.py', u'ScriptParser.py',
            u'utumno.py', u'archives.py', u'_games_lo.py', u'__init__.py',
    }
    def printLineLength(self, cwd=None, exts=('.py', '.pyw'), exclude=excl,
                        _firstRun=False, _print=True, _re_str=_re_str):
        if not cwd:
            cwd = os.getcwdu()
            print cwd
        modules = [os.path.join(cwd, m) for m in os.listdir(cwd) if
                   m.lower().endswith(exts) and not m.lower() in exclude]
        non_blank_count = 0
        i = -1
        def _repl(match):
            digit = u''
            ret = []
            for c in match.group(3):
                if c == '=': continue
                if str.isdigit(c):
                    digit += '%s' % c
                elif digit:
                    ret.append(digit + c)
                    digit = u''
                else:
                    ret.append(u'%s' % c)
            return u"Mel%sStruct%s %s" % (
                match.group(1) or u'', match.group(2), ret)
        for i, module_path in enumerate(modules):
            print module_path
            with open(module_path) as module:
                lines = module.readlines()
            for j, line in enumerate(lines):
                lines[j] = _re_str.sub(_repl, line)
            with open(module_path, u'w') as module:
                module.writelines(lines)

        self.non_blank_count += non_blank_count
        if i >= 0: self._files += i + 1
        # iterate subpackages -- p=(module_loader, name, ispkg)
        for p in pkgutil.iter_modules([cwd]):
            if not p[2] or p[1] in exclude: continue
            self.printLineLength(cwd=os.path.join(cwd, p[1]),
                                  _firstRun=True, _print=False)

try:
    _Lines().printLineLength() # cwd must be Mopy otherwise this blows
except Exception as e:
    print e

_ = raw_input('Done>')
