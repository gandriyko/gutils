import copy
from gutils.columns import Column


class Table:

    def __init__(self, view):
        self.columns = dict()
        self.view = view

    def get_columns(self):
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            value = getattr(self, attr)
            if isinstance(value, Column):
                self.columns[attr] = value
        return self.columns

