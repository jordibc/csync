#!/usr/bin/env python3

"""
Syncs a file that may exist in different machines, with a server
that only contains an encrypted version of the file.
"""

import sys
import os
import time
import hashlib
import subprocess
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter as fmt


def main():
    args = get_args()

    if args.list:
        list_tracked(args.location)
    elif args.init:
        for fname in args.files:
            init(fname, args.location)
    elif args.delete_backups:
        for fname in args.files:
            delete_backups(fname)
    else:
        for fname in args.files:
            sync(fname, args.location)



def get_args():
    parser = ArgumentParser(description=__doc__, formatter_class=fmt)
    add = parser.add_argument  # shortcut
    add('files', metavar='FILE', nargs='*', help='file to sync')
    add('--location', default='bb:sync', help='central sync storage')
    add('--list', action='store_true', help='list tracked files')
    add('--init', action='store_true', help='create initial file sync')
    add('--delete-backups', action='store_true', help='delete (most) backups')
    args = parser.parse_args()

    if not args.files and not args.list:
        sys.exit(parser.format_usage().strip())

    return args


def list_tracked(location):
    "Print local and remotely tracked files"
    def get_output(cmd): return subprocess.getoutput(cmd).splitlines()
    def get_fname(x): return x.split('/', 1)[-1][:-len('.history')]

    log('Getting local files that appear to be tracked...')
    for path in get_output('ls *.history'):
        print(get_fname(path))

    log('Getting remotely tracked files in %s ...' % location)
    server, path = location.split(':', 1)
    for path in get_output('ssh -q %s ls %s/*.history' % (server, path)):
        print(get_fname(path))


def init(fname, location):
    "Create the .history file and do the first synchronization"
    if not os.path.exists(fname):
        sys.exit("File doesn't exist: %s" % fname)

    log(f'Creating "{hfile(fname)}" to track synchronizations...')
    if os.path.exists(hfile(fname)):
        sys.exit(f'"{hfile(fname)}" already exists!')
    update_history(fname)

    if remote_exists(fname, location):
        sync(fname, location)
    else:
        log("Newly tracked file doesn't exist remotely. Uploading.")
        upload(fname, location)


def sync(fname, location):
    "Synchronize file fname using location as a repository"
    if not os.path.exists(fname):
        sys.exit(f"File doesn't exist: {fname}")

    if os.stat(fname).st_size == 0:
        answer = input('Local version is empty! Sync anyway? [y/n] ')
        if not answer.lower().startswith('y'):
            sys.exit('Cancelling.')

    assert_tracking(fname, location)

    update_history(fname)

    history_local = get_history_local(fname)
    history_remote = get_history_remote(fname, location) or ['nan']

    if history_local == history_remote:
        log('Same version everywhere, not updating anything.')
        delete_temp_files(fname, location)
    elif includes(history_local, history_remote):
        log('Local version is newer. Uploading.')
        upload(fname, location)
        delete_temp_files(fname, location)
    elif includes(history_remote, history_local):
        log('Remote version is newer. Downloading.')
        download(fname, location)
        delete_temp_files(fname, location)
    else:
        log('Versions have diverged. You will need to check manually.')
        download_with_different_name(fname, location)


def delete_backups(fname, n_keep_old=1, n_keep_new=2):
    print('Deleting backups '
          f'(except the first {n_keep_old} and the last {n_keep_new})...')
    dname = os.path.dirname(fname) or '.'
    backups = [x for x in os.listdir(dname) if x.startswith(fname + '.backup_')]
    backups_to_delete = sorted(backups)[n_keep_old:-n_keep_new]

    if not backups_to_delete:
        log('No backups to delete.')
    else:
        for bfile in backups_to_delete:
            run(f'rm "{bfile}"')


def includes(a, b):
    "Return True only if list a begins with all the elements of list b"
    return len(a) >= len(b) and all(a[i] == b[i] for i in range(len(b)))


def hfile(fname):
    "Return name of history file corresponding to file fname"
    return fname + '.history'


def cfile(fname):
    "Return name of encrypted file corresponding to file fname"
    return fname + '.gpg'


def tfile(fname, location):
    "Return name of temp file corresponding to file fname at a given location"
    # 'server:data/sync', 'notes.txt' -> 'tmp_server_data_sync_notes.txt'
    tmp = 'tmp_%s_%s' % (location, fname)
    for c in [':', ' ', '/']:
        tmp = tmp.replace(c, '_')
    return tmp


def remote_exists(fname, location):
    "Return True if the files corresponding to fname exist in the remote location"
    server, path = location.split(':', 1)
    fnames = ' '.join('"%s/%s"' % (path, x) for x in [cfile(fname), hfile(fname)])
    print(f'Checking if remote files exist at {server}: {fnames}')
    return os.system(f"ssh {server} 'ls {fnames}' > /dev/null 2>&1") == 0


def assert_tracking(fname, location):
    "Assert that fname is correctly being tracked and exit if not"
    print(f'Checking that "{fname}" is correctly being tracked...')
    try:
        for f in [fname, hfile(fname)]:
            assert os.path.exists(f), f"File doesn't exist: {f}"
        assert remote_exists(fname, location), \
            f'Missing corresponding files at {location}'
    except AssertionError as e:
        sys.exit('%s. Maybe run with --init first?' % e)
    # We could also check the consistency of the remote history by
    # computing the hash of the remote file (after copying it locally
    # and unencrypting) and comparing it to the last entry in the
    # remote history (ssh $server tail -n 1 $fname.history).


def update_history(fname):
    "Add current checksum of fname to its history file if not there yet"
    csum = checksum(fname)
    history = get_history_local(fname) if os.path.exists(hfile(fname)) else []
    if not history or csum != history[-1]:
        print(f'Updating "{hfile(fname)}" ...')
        new_entry = f'{csum}  {time.asctime()} at {os.uname()[1]}\n'
        open(hfile(fname), 'at').write(new_entry)


def checksum(fname):
    return hashlib.sha256(open(fname, 'rb').read()).hexdigest()[:40]


def get_history_local(fname):
    return [line.split()[0] for line in open(hfile(fname))]


def get_history_remote(fname, location):
    print(f'Getting remote history file ("{hfile(fname)}") ...')
    path_remote = f'{location}/{fname}'.replace(' ', '\\ ')
    path_tmp = tfile(fname, location)
    run(f'scp -q "{hfile(path_remote)}" {hfile(path_tmp)}')
    return get_history_local(path_tmp)


def download(fname, location):
    print(f'Downloading (after creating a backup) "{fname}" ...')
    backup(fname)
    path = f'{location}/{fname}'.replace(' ', '\\ ')
    run(f'scp -q "{cfile(path)}" "{hfile(path)}" .')
    decrypt(fname)


def download_with_different_name(fname, location):
    name_new = tfile(fname, location)
    print(f'Downloading "{fname}" with name "{name_new}" ...')
    for fn in [cfile, hfile]:
        fname_escaped = fname.replace(' ', '\\ ')
        run(f'scp -q "{location}/{fn(fname_escaped)}" {fn(name_new)}')
    decrypt(name_new)
    print(f'Check the differences in files "{name_new}" "{fname}"')
    print((f'Tip: merge them into "{name_new}", rename it to "{fname}", replace '
           f'"{hfile(fname)}" by "{hfile(name_new)}" and run csync again.'))


def backup(fname):
    t = time.strftime('%Y-%m-%d_%H%M')
    run(f'cp "{fname}" "{fname}.backup_{t}"')


def upload(fname, location):
    print(f'Uploading "{fname}" ...')
    encrypt(fname)
    run(f'scp -q "{cfile(fname)}" "{hfile(fname)}" "{location}"')


def encrypt(fname):
    xtra_args = passfile_args()
    run('gpg %s-o - -c "%s" > "%s"' % (xtra_args, fname, cfile(fname)))


def decrypt(fname):
    xtra_args = passfile_args()
    run('gpg %s-o - -d "%s" > "%s"' % (xtra_args, cfile(fname), fname))


def passfile_args():
    "Return arguments for gpg to use the password stored in the config file"
    passfile = os.environ['HOME'] + '/.config/csync/pass'
    return ('' if not os.path.exists(passfile) else
            '--batch --pinentry-mode loopback '
            '--passphrase-file "%s" \\\n    ' % passfile)


def delete_temp_files(fname, location):
    print('Deleting temporary files...')
    path_tmp = tfile(fname, location)
    for tmp in [hfile(path_tmp), cfile(fname)]:
        if os.path.exists(tmp):
            run(f'rm "{tmp}"')


def run(cmd):
    print(blue(cmd))
    ret = os.system(cmd)
    if ret != 0:
        sys.exit(f'Command failed (exit code: {ret})')


def log(txt):
    print(magenta(txt))


def ansi(n):
    "Return function that escapes text with ANSI color n"
    return lambda txt: '\x1b[%dm%s\x1b[0m' % (n, txt)

black, red, green, yellow, blue, magenta, cyan, white = map(ansi, range(30, 38))



if __name__ == '__main__':
    main()
