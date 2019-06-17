# -*- coding: utf-8 -*-

from django.db import models
from django.shortcuts import _get_queryset
from django.utils.translation import ugettext as _
import gc


class ExtraManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self._select_related = kwargs.pop('select_related', None)
        self._prefetch_related = kwargs.pop('prefetch_related', None)

        super(ExtraManager, self).__init__(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        qs = super(ExtraManager, self).get_queryset(*args, **kwargs)
        if self._select_related:
            qs = qs.select_related(*self._select_related)
        if self._prefetch_related:
            qs = qs.prefetch_related(*self._prefetch_related)
        return qs


def get_object_or_None(klass, *args, **kwargs):
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None


def queryset_iterator(queryset, chunksize=10000, select_related=None, prefetch_related=None, sort=None):
    if not sort:
        sort = ['id']
    first = queryset.order_by(*sort).first()
    if not first:
        return
    pk = first.pk - 1
    last = queryset.order_by(*sort).last()
    if not last:
        return
    last_pk = last.pk
    queryset = queryset.order_by(*sort)
    if select_related:
        queryset = queryset.select_related(*select_related)
    if prefetch_related:
        queryset = queryset.prefetch_related(*prefetch_related)
    while pk < last_pk:
        for row in queryset.filter(pk__gt=pk)[:chunksize]:
            pk = row.pk
            yield row
        gc.collect()


def queryset_part_iterator(queryset, pk='pk', chunksize=50000):
    queryset = queryset.order_by(pk)
    chunk = list(queryset[:chunksize])
    while chunk:
        yield chunk
        last_pk = getattr(chunk[-1], pk)
        chunk = list(queryset.filter(**{pk + '__gt': last_pk})[:chunksize])


def values_iterator(queryset, chunksize=50000, fields=['pk'], key='pk'):
    pk = 0
    if key not in fields:
        fields.insert(0, key)
    try:
        last_pk = getattr(queryset.order_by('-%s' % key)[0], key)
    except IndexError:
        return
    queryset = queryset.order_by(key)
    while pk < last_pk:
        for row in queryset.filter(**{'%s__gt' % key: pk}).values(*fields)[:chunksize]:  # .iterator():
            pk = row[key]
            yield row
    gc.collect()


def values_part_iterator(queryset, chunksize=50000, fields=['pk'], pk='pk'):
    queryset = queryset.order_by(pk)
    chunk = list(queryset.values(*fields)[:chunksize])
    while chunk:
        yield chunk
        last_pk = chunk[-1][pk]
        chunk = list(queryset.filter(**{pk + '__gt': last_pk}).values(*fields)[:chunksize])


def dict_join(items, new_name, join_field, qs, pk='pk'):
    if not qs:
        return items
    info = dict((getattr(i, pk), i) for i in qs)
    for item in items:
        id = item[join_field]
        item[new_name] = info.get(id)
    return items


def get_realated_items(item):
    related_items = [f for f in item._meta.get_fields() if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete]
    items = []
    for ri in related_items:
        items.append(dict(name=ri.related_model._meta.verbose_name_plural[:],
                          qty=ri.related_model._default_manager.all().filter(**{ri.field.name: item}).count()))
    return items


def cache_tree_children(queryset):
    """
    Takes a list/queryset of model objects in MPTT left (depth-first) order,
    and caches the children on each node so that no further queries are needed.
    This makes it possible to have a recursively included template without worrying
    about database queries.

    Returns a list of top-level nodes.
    """

    current_path = []
    top_nodes = []

    if hasattr(queryset, 'order_by'):
        mptt_opts = queryset.model._mptt_meta
        tree_id_attr = mptt_opts.tree_id_attr
        left_attr = mptt_opts.left_attr
        queryset = queryset.order_by(tree_id_attr, left_attr)

    if queryset:
        root_level = None
        for obj in queryset:
            node_level = obj.get_level()
            if root_level is None:
                root_level = node_level
            if node_level < root_level:
                raise ValueError(_("cache_tree_children was passed nodes in the wrong order!"))

            obj._cached_children = []

            while len(current_path) > node_level - root_level:
                current_path.pop(-1)

            if node_level == root_level:
                top_nodes.append(obj)
            else:
                current_path[-1]._cached_children.append(obj)
            current_path.append(obj)
    return top_nodes
