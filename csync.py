#!/usr/bin/env python3

"""
Syncs a file that may exist in different machines, with a server
that only contains an encrypted version of the file.
"""

import sys
import os
import time
import hashlib

SERVER = 'bb'


# TODO: Truncate history if repeated sha1.


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: %s <filename>' % sys.argv[0])

    fname = sys.argv[1]

    assert_tracking(fname)

    update_history(fname)

    history_local = get_history(fname)
    history_server = get_history_server(fname) or ['dummy']

    local, server = history_local[-1], history_server[-1]

    if local == server:
        pass  # do nothing
    elif server in history_local:
        upload(fname)
    elif local in history_server:
        download(fname)
    else:
        download_with_different_name(fname)


def assert_tracking(fname):
    try:
        for f in [fname, fname + '.history']:
            assert os.path.exists(f), "File doesn't exist: %s" % f
        run('ssh %s ls sync/%s.gpg sync/%s.history' % (SERVER, fname, fname))
    except AssertionError as e:
        sys.exit(e)
    # We could also check the consistency of the remote history by
    # computing the hash of the remote file (after copying it locally
    # and unencrypting) and comparing it to the first entry in the
    # remote history (ssh $server head -n 1 $fname.history).


def update_history(fname):
    csum = checksum(fname)
    history = get_history(fname)
    if not history or csum != history[-1]:
        new_entry = '%s\t%s\n' % (csum, time.asctime())
        open(fname + '.history', 'at').write(new_entry)


def checksum(fname):
    return hashlib.sha1(open(fname).read().encode('utf8')).hexdigest()


def get_history(fname):
    return [line.split()[0] for line in open(fname + '.history')]


def get_history_server(fname):
    path_remote = '%s:sync/%s' % (SERVER, fname)
    path_tmp = 'tmp_%s_%s' % (SERVER, fname)
    run('scp %s.history %s.history' % (path_remote, path_tmp))
    return get_history(path_tmp)


def download(fname):
    backup(fname)
    path = '%s:sync/%s' % (SERVER, fname)
    run('scp %s.gpg %s.history .' % (path, path))
    decrypt(fname)


def download_with_different_name(fname):
    name_new = 'tmp_%s_%s' % (SERVER, fname)
    run('scp %s:sync/%s.gpg %s.gpg' % (SERVER, fname, name_new))
    run('scp %s:sync/%s.history %s.history' % (SERVER, fname, name_new))
    decrypt(name_new)
    print('Check the differences in files %s %s' % (name_new, fname))


def backup(fname):
    t = time.strftime('%Y-%m-%d_%H%M')
    run('cp %s %s.backup_%s' % (fname, fname, t))


def upload(fname):
    encrypt(fname)
    run('scp %s.gpg %s.history %s:sync' % (fname, fname, SERVER))


def encrypt(fname):
    run('gpg -o %s.gpg -c %s' % (fname, fname))


def decrypt(fname):
    run('gpg -o %s -d %s.gpg' % (fname, fname))


def run(cmd):
    print('> ' + cmd)
    ret = os.system(cmd)
    if ret != 0:
        sys.exit('Command failed (exit code: %d)' % ret)



if __name__ == '__main__':
    main()
