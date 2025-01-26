# moonwise

How do you get book highlights out of [MoonReader](https://www.moondownload.com/) without [Readwise](https://readwise.io/)?

If you need real-time syncing, it appears that the only way is by [linking your Readwise](https://docs.readwise.io/readwise/docs/importing-highlights/moon-reader). However, if you are ok with getting them from your (daily, monthly, etc) auto-backups, this is how I'm doing so.

Get the backup file ending in `.mrstd` or `.mrpro` and unzip it. The unzipped `com.flyersoft.moonreader` folder contains a bunch of numbered `.tag` files (`1.tag`, `2.tag`, ...) whose human-readable file names are in the corresponding line of `_names.list`. The file with the main sqlite3 database is `mrbooks.db`. So, we can open with:

```{bash}
sqlite3 $(awk '/mrbooks.db$/ {print FNR".tag"}' _names.list)
```

You'll notice the db has several tables and highlights are in `notes`.

Someday I might code up a pretty UI, but for now (`main.py`) I'm just dumping the highlights into a note in Obsidian. With the [spaced repetition plugin](https://www.stephenmwangi.com/obsidian-spaced-repetition/) and [ntfy](https://ntfy.sh/) + [adv uri plugin](https://vinzent03.github.io/obsidian-advanced-uri/) for daily notifications gets most of the experience I want:


<img src="(https://github.com/user-attachments/assets/759f49c1-7314-40cf-bdbf-f1f3a7e1e625" height="400">