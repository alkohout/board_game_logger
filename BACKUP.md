# Backups

The code is on GitHub. This is about the data, which is all in Neon — including
the rulebook PDFs (`rulebooks.pdf_data`, ~88 MB) and the board photos
(`game_photos.image`), so a database dump is a complete backup.

Nothing on the Oracle server backs anything up; it has no `pg_dump` installed.
Backups run **from cron on the WSL machine**.

## The nightly job

    15 0 * * * PG_BACKUP_ENV=~/.config/pg_backup/neon.env ~/.local/bin/pg_backup.sh
               >> ~/.local/share/pg_backup_neon.log 2>&1

- Writes to `.../iCloudDrive/Documents/projects/SQL_backup_neon/<timestamp>/`
- `pg_dump -Fc` per database plus `globals.sql`, `SHA256SUMS`, `MANIFEST.txt`
- Keeps 14 days, ~56 MB a run
- Staged in a temp dir and moved on success, so a half-written dump is never
  published; a finished run is marked by `.done`

**There is a second, unrelated job at 00:00** that runs the same script with no
`PG_BACKUP_ENV`. That one dumps the *local* WSL Postgres, whose `boardgames`
database is a stale dev copy. It is not a backup of this site.

## Restoring

    createdb bgl_restore && pg_restore -d bgl_restore --no-owner --no-privileges neondb.dump

## Checking it, properly

Exit status is not enough. In September 2026 the live config still pointed at
the us-east-1 project abandoned in the August region move; that project is
still running, so the job succeeded while dumping month-old frozen data.

So verify by **restoring and counting**:

    psql -d bgl_restore -tAc "select count(*) from games"     # match the live count
    psql -d bgl_restore -tAc "select max(date_played) from games"   # should be recent

## After moving region or rotating the password

`migrations/region_move.sh` changes the connection string. `~/.config/pg_backup/neon.env`
holds its own copy of `PGHOST` and `PGPASSWORD` and will not follow — update it
in the same sitting, then restore-and-count as above.

Use the **direct** endpoint, not `-pooler`: `pg_dump` needs session features the
pooler does not carry.

## Known gaps

- Backups only happen when this PC is on and WSL is up at 00:15. A missed night
  is silent.
- One destination (iCloud). No second copy elsewhere.
- Neon's own point-in-time restore window depends on the plan and has not been
  checked.
