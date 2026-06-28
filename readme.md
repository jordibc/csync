# csync

**C**rypto-**sync**hronize files.

Syncs a file that may exist in different machines, using a remote
location as a repository (which will only contain an encrypted version
of the file).


## 💡 Example

```sh
$ sshfs remoteserver:sync /data/sync -o reconnect,idmap=user
$ csync notes.txt
Checking that "notes.txt" is correctly being tracked...
Checking if remote files exist at /data/sync: ['notes.txt.gpg', 'notes.txt.history']
Same version everywhere, not updating anything.
Deleting temporary files...
```


## 📥 Installation

You can run the `src/csync.py` file directly, or install the executable
`csync` with:

```sh
$ pip install -e .
```


## ❓ What does it try to solve?

I want to have a file *synchronized between my different computers*
(for example a text file with personal information).

A simple solution could be to have that file in one of those cloud
servers out there, but I don't trust them ([do
you?](https://en.wikipedia.org/wiki/Edward_Snowden#Revelations)).

I have a remote server I can log in with ssh. I could put a [git
server](https://git-scm.com/book/en/v2/Git-on-the-Server-Setting-Up-the-Server)
there, or maybe set up [nextcloud](https://nextcloud.com/), and
then I could do the synchronization easily. But I don't want to bother
(too much work, I'm lazy!), I don't want to rely on complex software,
and most importantly I don't want to trust any remote computer -- only
my own computers and some simpler tools like [gpg](https://gnupg.org/).

So I wrote this utility. It first encrypts the file you want to
synchronize, and then uploads it to a remote location. Or downloads
the remote file and decrypts it on your local machine. Depends on
which one is the last version. (Or if the versions have diverged, it
downloads and decrypts the remote one with a different name so you
solve the differences.)


## 🤔 How does it work?

In order to know which version is more recent, and also if there have
been divergences between files in different computers, it stores a
file with a list of hashes of the unencrypted file, both locally and
remotely (in addition to the *unencrypted file locally* and the
*encrypted file remotely*).

If the file you are synchronizing is called `notes.txt`, the file with
the list of hashes will be called `notes.txt.history`, and it will
look like:

```
68846e...78aa6b  2901397 B  2026-06-25 22:18Z  computer1
39752b...432e33  2903431 B  2026-06-29 19:44Z  computer2
fb045e...4dea9e  3194455 B  2026-07-03 12:36Z  computer1
5d34b7...c11a36  3196332 B  2026-07-06 21:39Z  computer3
d2fa12...dcbf81  3243595 B  2026-07-24 15:23Z  computer3
```

Each line starts with the (first 40 characters of the) SHA-256 hash of
the file at the time that csync was run. Then there is the size of the
file in bytes, the time of last modification, and the name of the
computer where it was done, all those only there for visual
inspection, but not used in any way by csync.

When synchronizing, it first updates this local *history file* if
there are any changes since the last time, then downloads the remote
history file and compares them. If the full history of changes is
contained in the local file, then the local one is the more recent and
it encrypts it and uploads it (plus the updated history file). If the
remote changes contain the local ones, it downloads the encrypted
remote file and decrypts it (making a backup of the local file first,
just in case). And if the histories have diverged, it downloads and
decrypts the remote one and tells you to manually merge them.


## 🛜 Remote connection

`csync` works with or without the remote directory mounted with
[sshfs](https://github.com/libfuse/sshfs).

If not mounted, it will use `ssh` and `scp` to explore and copy files
around. If mounted, it will access the mounted directory and will be
much faster.

We can select which method to use in the configuration file, normally
at `$HOME/.config/csync/csync.cfg`.

For example, if the remote location is `remote:sync`, we could have
`csync.cfg` look like:

```cfg
method = scp
location = remote:sync
passphrase = ...
```

But if we mount it with sshfs in the script's directory
`default_mountpoint`:

```sh
$ sshfs remote:sync default_mountpoint -o reconnect,idmap=user
```

Then `csync.cfg` would look like:

```cfg
method = sshfs
location = /path_to_csync/default_mountpoint
passphrase = ...
```

And when we do:

```sh
$ csync notes.txt
```

that operation will be faster than when using scp, as will all the
future operations with csync.


### gocryptfs

Another possibility is to have the remote directory, mounted with
nextcloud or sshfs, encrypted with `gocryptfs` and mounted somewhere
locally (as in `/data/crypt/csync` for example).

In that case, we don't need to use gpg and can specify `gocryptfs` as
method and `/data/crypt/csync` as location.


## 📖 Usage

```
usage: csync [-h] [-c CONFIG] [--list] [--download] [--init] [--delete-backups]
             [FILE ...]

Syncs a file that may exist in different machines, with a server that only
contains an encrypted version of the file.

positional arguments:
  FILE                 file to sync

options:
  -h, --help           show this help message and exit
  -c, --config CONFIG  configuration file
  --list               list tracked files
  --download           force download of remote file
  --init               create initial file sync
  --delete-backups     delete (most) backups
```


## ☮️ Similar projects

A much more advanced synchronization tool is
[Syncthing](https://syncthing.net/). It has many advantages over
csync.

The main advantage of csync is that it doesn't require the computers
to be connected simultaneously for it to synchronize data. It also has
a simpler setup (if you have an online server that you can use to
store the encrypted files).

Another project that lets synchronize files, and share them and more,
is [Seafile](https://www.seafile.com/).


## 🤖 AI use

Nope, there was no use of AI at all to write this software. The emojis
that appear in the text come from me because I used to like them, even
though nowadays it makes it look as if they were generated by an LLM.
Just humans here, thank you.


## ⚖️ License

This program is licensed under the GPL v3. See the [project
license](license.md) for further details.
