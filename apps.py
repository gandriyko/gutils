from __future__ import unicode_literals
from django.apps import AppConfig


class GutilsConfig(AppConfig):
    name = 'gutils'
    verbose_name = 'GUtils'

    def ready(self):
        import gutils.signals
