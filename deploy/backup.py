#!/usr/bin/env python3
"""Daily backup of the FinSuite database (accounts, saved data, alerts).

Uses SQLite's online backup, so it is safe while the app is running. Keeps the
newest KEEP copies, compressed. Standard library only; run by cron as root:
    python3 /opt/finsuite/deploy/backup.py
Restore:  gunzip -c /var/backups/finsuite/finsuite-DATE.db.gz > /var/lib/finsuite/finsuite.db
          chown www-data:www-data /var/lib/finsuite/finsuite.db && systemctl restart finsuite
"""
import gzip
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

DB = Path(os.environ.get("FINSUITE_DB", "/var/lib/finsuite/finsuite.db"))
DEST = Path(os.environ.get("FINSUITE_BACKUP_DIR", "/var/backups/finsuite"))
KEEP = int(os.environ.get("FINSUITE_BACKUP_KEEP", 14))


def main() -> int:
    if not DB.is_file():
        print(f"no database at {DB}, nothing to back up")
        return 0
    DEST.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "copy.db"
        src, dst = sqlite3.connect(DB), sqlite3.connect(copy)
        with dst:
            src.backup(dst)
        src.close(); dst.close()
        check = sqlite3.connect(copy)
        ok = check.execute("PRAGMA integrity_check").fetchone()[0]
        check.close()
        if ok != "ok":
            print(f"backup failed integrity check: {ok}", file=sys.stderr)
            return 1
        target = DEST / f"finsuite-{stamp}.db.gz"
        with open(copy, "rb") as f_in, gzip.open(target, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.chmod(target, 0o600)
    for old in sorted(DEST.glob("finsuite-*.db.gz"))[:-KEEP]:
        old.unlink()
    print(f"backed up to {target} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
