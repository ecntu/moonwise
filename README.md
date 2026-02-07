# moonwise
How do you get book highlights out of [MoonReader](https://www.moondownload.com/) without [Readwise](https://readwise.io/)?

It turns out you can use MoonReader's real-time Readwise [sync feature](https://docs.readwise.io/readwise/docs/importing-highlights/moon-reader) with any url, so you can just point it to an endpoint you control. See @ynhhoJ's helpful [setup guide](https://github.com/ynhhoJ/moon-reader-highlights/blob/master/READER_SETUP.md).

If you want to get old highlights out of a MoonReader backups this is how I'm doing so.

Get the backup file ending in `.mrstd` or `.mrpro` and unzip it. The unzipped `com.flyersoft.moonreader` folder contains a bunch of numbered `.tag` files (`1.tag`, `2.tag`, ...) whose human-readable file names are in the corresponding line of `_names.list`. The file with the main sqlite3 database is `mrbooks.db`. So, we can open with:

```{bash}
sqlite3 $(awk '/mrbooks.db$/ {print FNR".tag"}' _names.list)
```

You'll notice the db has several tables and that your highlights are in `notes`. `import.py` has an example script.


The rest of this repo is a simple "vibe coded" flask site for managing my own highlights. Live (with limited functionality if not logged in) [here](https://old-highlights.ecntu.com/).

## Setup

1. Create and `.env` file with variables:
```{bash}
PASSWORD=
SESSION_SECRET=
MOON_READER_TOKEN=
N_REVIEW_PASSAGES=
N_FAVORITES_IN_REVIEW=
```

2. Run `uv run --env-file .env main.py`
3. Optionally, setup cron job to run `review.py`. For example:

```{text}
0 13 * * * cd ~/moonwise && uv run review.py && sh notify.sh
```


If you ever drop the `highlights_fts` table, re-populate it with:

  ```sql
  INSERT INTO highlights_fts(rowid, highlight_text, note)
  SELECT id, highlight_text, note FROM highlights;
  ```
