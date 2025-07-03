This directory is intended to be used as a mountpoint for sshfs.

You can change it to any other location (with the `--location`
argument), but this is the default for csync.

From its parent directory, you can run:

```sh
sshfs [user@]host:[dir] sync -o reconnect,idmap=user
```

When you are done for the day (or whatever), you can just unmount it:

```sh
umount sync
```
