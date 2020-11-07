# csync

Syncs a file that may exist in different machines, with a server that
only contains an encrypted version of the file.


# Example

```
$ csync notes.html
Checking that notes.html is correctly being tracked...
Checking if remote files exist at bb: "sync/notes.html.gpg" "sync/notes.html.history"
Getting remote history file (notes.html.history) ...
scp -q bb:sync/notes.html.history tmp_bb_sync_notes.html.history
Same version everywhere, not updating anything.
Deleting temporary files.
rm tmp_bb_sync_notes.html.history
```


# Usage

```
usage: csync [-h] [--location LOCATION] [--list] [--start] [FILE [FILE ...]]

Syncs a file that may exist in different machines, with a server that only contains an encrypted version of the file.

positional arguments:
  FILE                 file to sync (default: None)

optional arguments:
  -h, --help           show this help message and exit
  --location LOCATION  central sync storage (default: bb:sync)
  --list               list tracked files (default: False)
  --start              create initial file sync (default: False)
```
