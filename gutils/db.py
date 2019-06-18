from django.conf import settings
from django.db import connections


def server_side_cursor(using='default'):
    connection = connections[using]
    vendor = connection.vendor
    if vendor == 'postgresql':
        cursor = connection.connection.cursor()
        cursor.tzinfo_factory = None
        return cursor
    elif vendor == 'mysql':
        from MySQLdb.cursors import SSCursor
        from MySQLdb import connect
        DB = settings.DATABASES[using]
        db = connect(host=DB['HOST'], user=DB['USER'],
                     passwd=DB['PASSWORD'], db=DB['NAME'],
                     use_unicode=True, charset='utf8',
                     cursorclass=SSCursor)
        return db.cursor()
    else:
        return connection.cursor()
