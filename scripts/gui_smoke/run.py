"""Run the GUI scenarios and unit tests on Wrye Bash trees, compare them.

run.py --tree NAME=MOPY [--tree NAME=MOPY ...] [--out DIR] [TEST ...]

A TEST is a sc_*.py scenario of this folder - run in the whole app through
wbdrive.py - or a zz_*.py unit test, run on its own through harness.py. All
of them by default. Each run starts from a freshly made fake game. The first
tree is the baseline: the report shows where the others differ from it."""
import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_NOISE = re.compile(r'Debug: |Gtk-(CRITICAL|WARNING)|send2trash missing|'
                    r'^\s*$|Adding duplicate|accel string ignored')

def _normalize(line):
    line = re.sub(r'0x[0-9a-fA-F]+', '0x?', line)
    line = re.sub(r'\b\d\d:\d\d:\d\d(\.\d+)?\b', '<time>', line)
    return line.rstrip()

def _kill(proc):
    if sys.platform == 'win32':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                       capture_output=True)
    else:
        os.killpg(proc.pid, signal.SIGKILL)

def run_one(test, tree, mopy, out, timeout):
    stem = test[:-3]
    run_dir = os.path.join(out, tree, stem)
    shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir)
    fake = os.path.join(out, 'fake')
    shutil.rmtree(fake, ignore_errors=True)
    subprocess.run([sys.executable, os.path.join(HERE, 'mkgame.py'), fake],
                   check=True, capture_output=True)
    env = {**os.environ, 'WB_MOPY': os.path.abspath(mopy), 'WB_FAKE': fake,
           'PYTHONIOENCODING': 'utf-8'}
    if sys.platform != 'win32':
        env['HOME'] = os.path.join(fake, 'home')
    cmd = [sys.executable, os.path.join(HERE, test)]
    if test.startswith('sc_'):
        cmd = [sys.executable, os.path.join(HERE, 'wbdrive.py'),
               os.path.join(HERE, test), run_dir]
    if sys.platform != 'win32' and not os.environ.get('DISPLAY'):
        cmd = ['xvfb-run', '-a', '-s', '-screen 0 1400x900x24', *cmd]
    log_path = os.path.join(run_dir, 'output.log')
    start = time.time()
    with open(log_path, 'w', encoding='utf-8') as log_out:
        proc = subprocess.Popen(cmd, env=env, stdout=log_out,
            stderr=subprocess.STDOUT, cwd=HERE,
            start_new_session=sys.platform != 'win32')
        try:
            rc = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill(proc)
            proc.wait()
            rc = 'TIMEOUT'
    with open(log_path, encoding='utf-8', errors='replace') as ins:
        output = ins.read().splitlines()
    if test.startswith('sc_'):
        lines = [l.split('[drive] ', 1)[1] for l in output if '[drive] ' in l]
    else:
        lines = [l for l in output if not _NOISE.search(l)]
    tracebacks = [i for i, l in enumerate(output) if l.startswith('Traceback')]
    if test.startswith('sc_') and tracebacks:
        lines += output[tracebacks[-1]:][-6:] # how the last one ended
    if rc == 'TIMEOUT':
        lines += ['(timed out - output ended with:)', *output[-4:]]
    return rc, [_normalize(l) for l in lines], time.time() - start

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--tree', action='append', required=True,
                    help='NAME=MOPY - the first one is the baseline')
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    ap.add_argument('--timeout', type=int, default=150)
    ap.add_argument('tests', nargs='*')
    args = ap.parse_args()
    trees = [t.split('=', 1) for t in args.tree]
    tests = args.tests or sorted(f for f in os.listdir(HERE)
                                 if re.fullmatch(r'(sc|zz)_\w+\.py', f))
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    report = []
    def emit(*a):
        line = ' '.join(map(str, a))
        print(line, flush=True)
        report.append(line)
    summary = []
    for test in tests:
        res = {}
        for tree, mopy in trees:
            res[tree] = run_one(test, tree, mopy, out, args.timeout)
        emit(f'\n{"=" * 30} {test}')
        base_tree = trees[0][0]
        for tree, _mopy in trees:
            rc, lines, secs = res[tree]
            emit(f'--- {tree}: exit {rc} in {secs:.0f}s')
            if tree == base_tree:
                for l in lines: emit('   ', l)
            else:
                base = res[base_tree][1]
                if lines == base:
                    emit('    same output as', base_tree)
                else:
                    import difflib
                    for l in difflib.unified_diff(base, lines, base_tree,
                                                  tree, n=1, lineterm=''):
                        emit('   ', l)
        rcs = {t: r[0] for t, r in res.items()}
        same = all(r[1] == res[base_tree][1] for r in res.values())
        summary.append(f'{test:28} exit {rcs} | '
                       f'{"same output" if same else "OUTPUT DIFFERS"}')
    emit(f'\n{"=" * 30} summary')
    for l in summary: emit(l)
    with open(os.path.join(out, 'report.txt'), 'w', encoding='utf-8') as o:
        o.write('\n'.join(report) + '\n')

if __name__ == '__main__':
    main()
