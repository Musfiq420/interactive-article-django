from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def configure_sqlite_pragmas(sender, connection, **kwargs):
    if connection.vendor != "sqlite":
        return

    with connection.cursor() as cursor:
        # Use in-memory journaling because file-backed SQLite journals are
        # failing in this workspace with disk I/O errors.
        cursor.execute("PRAGMA journal_mode=MEMORY;")
        cursor.execute("PRAGMA temp_store=MEMORY;")
