This directory is intended to be used as a mountpoint for sshfs.

You can use instead any other location (with the `--location`
argument), but this is the default for csync.

For example, if the remote location is `remote:sync`, from this
directory's parent directory you can run:

```sh
$ sshfs remote:sync default_mountpoint -o reconnect,idmap=user
```

When you are done for the day (or whatever), you can just unmount it:

```sh
umount default_mountpoint
```
