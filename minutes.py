import requests
import argparse
import re
import sys
import subprocess
import os
import shlex
from datetime import datetime


parser = argparse.ArgumentParser(
    description="Given a HackMD meeting notes URL, make a PR to the archive"
)
parser.add_argument('url', help='HackMD document URL')
parser.add_argument('repo', help='Target repository: org/reponame')
parser.add_argument('path', help='Path in the repository to commit file to')
args = parser.parse_args()

url = args.url
repo = args.repo
path = args.path


ANSI_BOLD = "\033[1m"
ANSI_CLEAR = "\033[0;0m"
ANSI_YELLOW = "\033[1;33m"


def run(*args, **kwargs):
    fail = kwargs.pop('fail', True)
    cmd = shlex.join(args[0])
    print(f"{ANSI_BOLD}$ {cmd}{ANSI_CLEAR}")
    p = subprocess.run(*args, **kwargs)
    if fail and p.returncode != 0:
        print(f'\nFATAL: command exited with error code {p.returncode}')
        sys.exit(p.returncode)
    return p


def bprint(msg):
    print(f"{ANSI_BOLD}{ANSI_YELLOW}{msg}{ANSI_CLEAR}")


hackmd_id_match = re.match('https://hackmd.io/([a-zA-Z0-9-]+)/?$', url)
if hackmd_id_match is None:
    print(f'Invalid HackMD URL: {url}')
    sys.exit(-1)

if not repo.count('/') == 1:
    print(f'Invalid repo: {repo}; should be org/reponame')
    sys.exit(-1)


hackmd_id, = hackmd_id_match.groups(1)

download_url = f'https://hackmd.io/{hackmd_id}/download'
r = requests.get(download_url)
meeting_notes = r.content

date = datetime.today().strftime('%Y-%m-%d')

cwd = '__minutes_cache'
os.makedirs(cwd, exist_ok=True)
os.chdir(cwd)

reponame = repo.split('/')[1]

if not os.path.exists(reponame):
    bprint(f'Cloning {repo}')
    run([
        'gh', 'repo', 'clone', repo
    ])

os.chdir(reponame)

bprint('Fetching latest commits')
run([
    'git', 'checkout', 'main'
])
run([
    'git', 'pull', 'origin', 'main'
])

branch = f'minutes_{date}'
bprint(f'Creating `{branch}` branch')

p = run([
    'git', 'show-branch', branch
], fail=False)
if p.returncode == 0:
    print('Branch already exists: overwriting')
    run([
        'git', 'branch', '-D', branch
    ])

run([
    'git', 'checkout', '-b', branch
])

if path.startswith('/'):
    path = path.lstrip('/')

fn = os.path.relpath(os.path.join(path, f'{date}.md'))
with open(fn, 'wb') as f:
    f.write(meeting_notes)

run([
    'git', 'add', fn
])

run([
    'git', 'commit', '-m', f'Add {date} meeting notes'
])

p = run([
    'gh', 'pr', 'create',
    '--fill',
    '--repo', repo
])
