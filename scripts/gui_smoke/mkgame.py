"""Create a tiny fake Oblivion install and home: a master, a few plugins, an ini, a BAIN project, a screenshot."""
import os, struct, sys, time
root = os.path.abspath(sys.argv[1]) # mkgame.py <folder to make the fake game in>
def sub(sig, data): return sig + struct.pack('<H', len(data)) + data
def plugin(path, masters=(), esm=False, author=b'Tester', desc=b'A test plugin & stuff'):
    data = sub(b'HEDR', struct.pack('<fiI', 1.0, 0, 0x800)) + sub(b'CNAM', author + b'\0') + sub(b'SNAM', desc + b'\0')
    for m in masters:
        data += sub(b'MAST', m.encode() + b'\0') + sub(b'DATA', struct.pack('<Q', 0))
    with open(path, 'wb') as out:
        out.write(b'TES4' + struct.pack('<IIII', len(data), 1 if esm else 0, 0, 0) + data)
d = root + '/Oblivion/Data'
os.makedirs(d, exist_ok=True)
for exe in ('Oblivion.exe', 'OblivionLauncher.exe'): # what game detection looks for
    open(f'{root}/Oblivion/{exe}', 'wb').close()
plugin(d + '/Oblivion.esm', esm=True, author=b'Bethesda', desc=b'')
t0 = time.time() - 86400 * 400
os.utime(d + '/Oblivion.esm', (t0, t0))
names = ['Alpha Mod.esp', 'Beta & Gamma.esp', 'Delta Patch.esp', 'Epsilon.esp', 'Zeta Overhaul.esp', 'Eta.esp', 'Theta Fixes.esp', 'Iota.esp']
for i, n in enumerate(names):
    masters = ['Oblivion.esm'] + (['Alpha Mod.esp'] if 'Patch' in n else []) + (['Missing Master.esm'] if n == 'Iota.esp' else [])
    plugin(f'{d}/{n}', masters, desc=('Description of %s. ' % n).encode() * (3 if i % 2 else 1))
    os.utime(f'{d}/{n}', (t0 + 3600 * (i + 1), t0 + 3600 * (i + 1)))
mg = root + '/home/Documents/My Games/Oblivion'
os.makedirs(mg + '/Saves', exist_ok=True)
with open(mg + '/Oblivion.ini', 'w') as out:
    out.write('[General]\nsLanguage=ENGLISH\nbBorderRegionsEnabled=1\n[Display]\niSize W=1280\niSize H=720\n[Archive]\nsArchiveList=Oblivion - Meshes.bsa\n')
os.makedirs(root + '/home/AppData/Local/Oblivion', exist_ok=True)
with open(root + '/home/AppData/Local/Oblivion/plugins.txt', 'w') as out:
    out.write('\n'.join(['Oblivion.esm'] + names[:5]) + '\n')
pk = root + '/Oblivion Mods/Bash Installers'
for pkg in ('Tools & Fixes', 'Second Package'):
    os.makedirs(f'{pk}/{pkg}/Docs', exist_ok=True)
    plugin(f'{pk}/{pkg}/{pkg.split()[0]} Plugin.esp', ['Oblivion.esm'])
    open(f'{pk}/{pkg}/Docs/readme.txt', 'w').write('readme of ' + pkg)
print('fake game ready:', sorted(os.listdir(d)))
