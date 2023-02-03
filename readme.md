# csync

**C**rypto-**sync**hronize files.

Syncs a file that may exist in different machines, using a remote
location as a repository (which will only contain an encrypted version
of the file).


# What does it try to solve?

I want to have a file *synchronized between my different computers*
(for example a text file with personal information).

A simple solution could be to have that file in one of those cloud
servers out there, but I don't trust them ([do
you?](https://en.wikipedia.org/wiki/Edward_Snowden#Revelations)).

I have a remote server I can log in with ssh. I could put a [git
server](https://git-scm.com/book/fa/v2/Git-on-the-Server-Setting-Up-the-Server)
there, or maybe set up [nextcloud](https://nextcloud.com/), and
then I could do the synchronization easily. But I don't want to bother
(too much work, I'm lazy!), I don't want to rely on complex software,
and most importantly I don't want to trust any remote computer -- only
my own computers and some simpler tools like [gpg](https://gnupg.org/).

So I wrote this utility. It first encrypts the file you want to
synchronize, and then uploads it to a remote location. Or downloads
the remote file and unencrypts it on your local machine. Depends on
which one is the last version. (Or if the versions have diverged, it
downloads and unencrypts the remote one with a different name so you
solve the differences.)


# How does it work?

In order to know which version is more recent, and also if there have
been divergences between files in different computers, it stores a
file with a list of hashes of the unencrypted file, both locally and
remotely (in addition to the *unencrypted file locally* and the
*encrypted file remotely*).

If the file you are synchronizing is called `notes.txt`, the file with
the list of hashes will be called `notes.txt.history`, and it will
look like:

```
68846e...78aa6b  Fri Sep  4 13:22:10 2023 at computer1
39752b...432e33  Sat Sep 19 18:33:57 2023 at computer2
fb045e...4dea9e  Sun Oct  4 21:18:21 2023 at computer1
5d34b7...c11a36  Mon Nov  2 11:33:27 2023 at computer3
d2fa12...dcbf81  Sat Nov  7 00:26:01 2023 at computer3
```

Each line starts with the (first 40 characters of the) SHA-256 hash of
the file at the time that csync was run. The second part is just a
timestamp and the name of the computer where it was done, and it is
only there for visual inspection, but not used in any way by csync.

When synchronizing, it first updates this local *history file* if
there are any changes since the last time, then downloads the remote
history file and compares them. If the full history of changes is
contained in the local file, then the local one is the more recent and
it encrypts it and uploads it (plus the updated history file). If the
remote changes contain the local ones, it downloads the encrypted
remote file and unencrypts it (making a backup of the local file
first, just in case). And if the histories have diverged, it downloads
and unencrypts the remote one and tells you to manually merge them.


# Example

```
$ csync --location remoteserver:sync notes.txt
Checking that notes.txt is correctly being tracked...
Checking if remote files exist at remoteserver: "sync/notes.txt.gpg" "sync/notes.txt.history"
Getting remote history file (notes.txt.history) ...
scp -q remoteserver:sync/notes.txt.history tmp_remoteserver_sync_notes.txt.history
Same version everywhere, not updating anything.
Deleting temporary files.
rm tmp_remoteserver_sync_notes.txt.history
```


# Usage

```
usage: csync [-h] [--location LOCATION] [--list] [--download] [--init] [--delete-backups] [FILE ...]

Syncs a file that may exist in different machines, with a server that only
contains an encrypted version of the file.

positional arguments:
  FILE                 file to sync

options:
  -h, --help           show this help message and exit
  --location LOCATION  central sync storage
  --list               list tracked files
  --download           force download of remote file
  --init               create initial file sync
  --delete-backups     delete (most) backups
```


# Similar projects

A much more advanced synchronization tool is
[Syncthing](https://syncthing.net/). It has many advantages over
csync.

The main advantage of csync is that it doesn't require the computers
to be connected simultaneously for it to synchronize data. It also has
a simpler setup (if you have an online server that you can use to
store the encrypted files).
