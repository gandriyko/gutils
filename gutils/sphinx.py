# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.conf import settings
from django.utils.encoding import force_text
import MySQLdb
from MySQLdb import cursors
import six
import re


def safe_value(value):
    if isinstance(value, six.string_types):
        v = force_text(value)
        v = re.sub(r'[^\d\w ]', ' ', v, flags=re.U)
        v = re.sub(r' +', ' ', v)
        return v.strip()
    return value


class SphinxConnector():

    def __init__(self, **kwargs):
        connection_options = {
            'host': getattr(settings, 'GUTILS_SPHINXQL_HOST', '127.0.0.1'),
            'port': getattr(settings, 'GUTILS_SPHINXQL_PORT', 9306),
        }
        connection_options.update(**kwargs)
        self.connection = MySQLdb.connect(
            cursorclass=cursors.DictCursor,
            use_unicode=True,
            charset='utf8',
            **connection_options
        )

    def __del__(self):
        self.close()

    def close(self):
        del self.connection



    def execute(self, query, params, **kwargs):
        safe = kwargs.get('safe', False)
        if safe:
            params = [safe_value(a) for a in params]
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            raise e
        finally:
            cursor.close()
