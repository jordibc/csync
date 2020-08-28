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
    else:
        for fname in args.files:
            sync(fname, args.location, args.start)


def list_tracked(location):
    "Print local and remotely tracked files"
    get_output = lambda cmd: subprocess.getoutput(cmd).splitlines()
    get_fname = lambda x: x.split('/', 1)[-1][:-len('.history')]

    log('Getting local files that appear to be tracked...')
    for path in get_output('ls *.history'):
        print(get_fname(path))

    log('Getting remotely tracked files in %s ...' % location)
    server, path = location.split(':', 1)
    for path in get_output('ssh -q %s ls %s/*.history' % (server, path)):
        print(get_fname(path))


def sync(fname, location, start=False):
    "Synchronize file fname using location as a repository"
    # If start==True, it will create the .history file first.

    if not os.path.exists(fname):
        sys.exit("File doesn't exist: %s" % fname)

    if os.stat(fname).st_size == 0:
        answer = input('Local version is empty! Sync anyway? [y/n] ')
        if not answer.lower().startswith('y'):
            sys.exit('Cancelling.')

    if start:
        log('Creating %s to track synchronizations...' % hfile(fname))
        if os.path.exists(hfile(fname)):
            sys.exit('%s already exists!' % hfile(fname))
        update_history(fname)

        if not remote_exists(location, cfile(fname), hfile(fname)):
            log("Newly tracked file doesn't exist remotely. Uploading.")
            upload(location, fname)
            sys.exit()

    assert_tracking(location, fname)

    update_history(fname)

    history_local = get_history_local(fname)
    history_remote = get_history_remote(location, fname) or ['nan']

    if history_local == history_remote:
        log('Same version everywhere, not updating anything.')
        delete_temp_files(location, fname)
    elif includes(history_local, history_remote):
        log('Local version is newer. Uploading.')
        upload(location, fname)
        delete_temp_files(location, fname)
    elif includes(history_remote, history_local):
        log('Remote version is newer. Downloading.')
        download(location, fname)
        delete_temp_files(location, fname)
    else:
        log('Versions have diverged. You will need to check manually.')
        download_with_different_name(location, fname)


def includes(a, b):
    "Return True if a includes all the elements of b"
    return len(a) >= len(b) and all(a[i] == b[i] for i in range(len(b)))


def get_args():
    parser = ArgumentParser(description=__doc__, formatter_class=fmt)
    add = parser.add_argument  # shortcut
    add('files', metavar='FILE', nargs='*', help='file to sync')
    add('--location', default='bb:sync', help='central sync storage')
    add('--list', action='store_true', help='list tracked files')
    add('--start', action='store_true', help='create initial file sync')
    args = parser.parse_args()

    if not args.files and not args.list:
        sys.exit(parser.format_usage().strip())

    return args


def hfile(fname):
    "Return name of history file corresponding to file fname"
    return fname + '.history'


def cfile(fname):
    "Return name of encrypted file corresponding to file fname"
    return fname + '.gpg'


def tfile(location, fname):
    tmp = 'tmp_%s_%s' % (location, fname)
    for c in [':', ' ', '/']:
        tmp = tmp.replace(c, '_')
    return tmp


def remote_exists(location, *args):
    "Return True if the given files exist in the remote location"
    server, path = location.split(':', 1)
    fnames = ' '.join('"%s/%s"' % (path, x) for x in args)
    print('Checking if remote files exist at %s: %s' % (server, fnames))
    return os.system('ssh %s ls %s > /dev/null 2>&1' % (server, fnames)) == 0


def assert_tracking(location, fname):
    "Assert that fname is correctly being tracked and exit if not"
    print('Checking that %s is correctly being tracked...' % fname)
    try:
        for f in [fname, hfile(fname)]:
            assert os.path.exists(f), "File doesn't exist: %s" % f
        assert remote_exists(location, cfile(fname), hfile(fname)), \
            'Must exist in %s : %s %s' % (location, cfile(fname), hfile(fname))
    except AssertionError as e:
        sys.exit(e)
    # We could also check the consistency of the remote history by
    # computing the hash of the remote file (after copying it locally
    # and unencrypting) and comparing it to the last entry in the
    # remote history (ssh $server tail -n 1 $fname.history).


def update_history(fname):
    "Add current checksum of fname to its history file if not there yet"
    csum = checksum(fname)
    history = get_history_local(fname) if os.path.exists(hfile(fname)) else []
    if not history or csum != history[-1]:
        print('Updating %s ...' % hfile(fname))
        new_entry = '%s  %s at %s\n' % (csum, time.asctime(), os.uname()[1])
        open(hfile(fname), 'at').write(new_entry)


def checksum(fname):
    return hashlib.blake2b(open(fname, 'rb').read()).hexdigest()


def get_history_local(fname):
    return [line.split()[0] for line in open(hfile(fname))]


def get_history_remote(location, fname):
    print('Getting remote history file (%s) ...' % hfile(fname))
    path_remote = '%s/%s' % (location, fname)
    path_tmp = tfile(location, fname)
    run('scp -q %s %s' % (hfile(path_remote), hfile(path_tmp)))
    return get_history_local(path_tmp)


def download(location, fname):
    print('Downloading (after creating a backup) %s ...' % fname)
    backup(fname)
    path = '%s/%s' % (location, fname)
    run('scp -q %s %s .' % (cfile(path), hfile(path)))
    decrypt(fname)


def download_with_different_name(location, fname):
    name_new = tfile(location, fname)
    print('Downloading %s with name %s ...' % (fname, name_new))
    run('scp -q %s/%s %s' % (location, cfile(fname), cfile(name_new)))
    run('scp -q %s/%s %s' % (location, hfile(fname), hfile(name_new)))
    decrypt(name_new)
    print('Check the differences in files %s %s' % (name_new, fname))
    print(('You probably want to merge them into %s, rename it to %s, replace '
           '%s by %s and run csync again.') % (name_new, fname,
                                               hfile(fname), hfile(name_new)))


def backup(fname):
    t = time.strftime('%Y-%m-%d_%H%M')
    run('cp %s %s.backup_%s' % (fname, fname, t))


def upload(location, fname):
    print('Uploading %s ...' % fname)
    encrypt(fname)
    run('scp -q %s %s %s' % (cfile(fname), hfile(fname), location))


def encrypt(fname):
    xtra_args = passfile_args()
    run('gpg %s-o - -c %s > %s' % (xtra_args, fname, cfile(fname)))


def decrypt(fname):
    xtra_args = passfile_args()
    run('gpg %s-o - -d %s > %s' % (xtra_args, cfile(fname), fname))


def passfile_args():
    passfile = os.environ['HOME'] + '/.config/csync/pass'
    return ('' if not os.path.exists(passfile) else
            '--batch --pinentry-mode loopback '
            '--passphrase-file "%s" \\\n    ' % passfile)


def delete_temp_files(location, fname):
    print('Deleting temporary files.')
    path_tmp = tfile(location, fname)
    for tmp in [hfile(path_tmp), cfile(fname)]:
        if os.path.exists(tmp):
            run('rm %s' % tmp)


def run(cmd):
    print(blue(cmd))
    ret = os.system(cmd)
    if ret != 0:
        sys.exit('Command failed (exit code: %d)' % ret)


def log(txt):
    print(magenta(txt))


def ansi(n):
    "Return function that escapes text with ANSI color n"
    return lambda txt: '\x1b[%dm%s\x1b[0m' % (n, txt)

black, red, green, yellow, blue, magenta, cyan, white = map(ansi, range(30, 38))



if __name__ == '__main__':
    main()
