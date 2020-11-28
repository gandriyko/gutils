# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
import json
import pprint
import random
import re
import unicodedata

from collections import OrderedDict
from decimal import Decimal
from operator import attrgetter

from django.conf import settings
from django.db.models import FieldDoesNotExist, Model
from django.utils.http import urlquote
from django.utils import formats
from django.utils import six
from django.utils.encoding import DjangoUnicodeDecodeError
from django.utils.encoding import force_text
from django.utils.functional import lazy
from django.utils.translation import ugettext as _

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from gutils.strings import upper_first


default_app_config = 'gutils.apps.GutilsConfig'


class Struct:

    def __init__(self, **entries):
        self.__dict__.update(entries)

    def __getitem__(self, attr):
        return getattr(self, attr, None)

    def __setitem__(self, attr, value):
        self.__dict__[attr] = value
        return value

    def __str__(self):
        return pprint.pformat(self.__dict__)

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    @property
    def dict(self):
        return self.__dict__

    def items(self):
        return self.__dict__.items()

    def update(self, **kwargs):
        self.__dict__.update(kwargs)
        return self

    def update_not_empty(self, **kwargs):
        for k, v in kwargs.items():
            if v:
                self.__dict__[k] = v

    def copy(self):
        return Struct(**self.dict)


class DecimalEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)


def get_function(function_name):
    module_segments = function_name.split('.')
    module = __import__('.'.join(module_segments[:-1]))
    for segment in module_segments[1:]:
        module = getattr(module, segment)
    if not callable(module):
        raise AttributeError("'%s' is not a callable." % (function_name))
    return module


def get_attribute(obj, attr, default=None, call=True):
    try:
        value = attrgetter(attr)(obj)
        if hasattr(value, 'all'):
            return value
        if call and value and hasattr(value, '__call__'):
            return value()
        return value
    except AttributeError:
        return default


def get_name(model, field=None, upper=True, plural=False):
    if not model:
        return ''
    if field:
        try:
            field_class = model._meta.get_field(field)
        except FieldDoesNotExist:
            field_class = None
        if field_class and hasattr(field_class, 'verbose_name'):
            name = field_class.verbose_name
        else:
            name = field
    else:
        try:
            if plural:
                name = model._meta.verbose_name_plural
            else:
                name = model._meta.verbose_name
        except AttributeError:
            name = model._meta.model_name
    if upper:
        return upper_first(name)
    else:
        return name


get_name_lazy = lazy(get_name, six.text_type)


def to_int(value, default=0):
    try:
        return int(value)
    except ValueError:
        return default
    except TypeError:
        return default


def to_dict(obj, fields, fields_rules=None):
    result = {}
    _fields = list(fields)
    if 'id' not in fields:
        _fields.insert(0, 'id')
    model = type(obj)

    for field in _fields:
        _field = field[:]
        # _field = _field.replace('__', '.')
        if fields_rules and field in fields_rules:
            key = fields_rules[field]
            if key is None:
                continue
            # key = key.replace('__', '.')
        else:
            key = _field[:]

        if '__' in key:
            v = obj
            for f0 in key.split('__'):
                if v is not None:
                    v = getattr(v, f0, None)
        else:
            try:
                field_type = model._meta.get_field(key).__class__.__name__
            except Exception:
                field_type = None
            if field_type == 'ForeignKey':
                v = getattr(obj, f'{key}_id', None)
            else:
                v = getattr(obj, key, None)
        if callable(v):
            v = v()

        if isinstance(v, datetime.datetime):
            v = formats.date_format(v, 'DATETIME_FORMAT', use_l10n=True)
        elif isinstance(v, datetime.date):
            v = formats.date_format(v, 'DATE_FORMAT', use_l10n=True)
        elif isinstance(v, Model):
            v = getattr(v, 'pk', None)
        elif isinstance(v, Decimal):
            v = float(v)
        #if not isinstance(v, six.string_types) and not isinstance(v, (bool, int)):
        #    v = force_text(v)
        result[_field] = v
    return result


def int_list(value, separator=','):
    if not value:
        return []
    return list(set(to_int(i) for i in value.strip().split(separator) if to_int(i, None) is not None))


def get_choice_by_name(choices, item):
    if item:
        item = item.lower()
    for c in choices:
        if item in c:
            return c[0]
    return choices[0][0]


def intersect(*data):
    result = set()
    for d in data:
        if not result:
            result = set(d)
        else:
            result &= set(d)
    return result


def instance_as_dict(instance, verbose_name=True):
    result = OrderedDict()
    if not instance:
        return result
    for field in instance._meta.fields:
        # don;t log passwords
        if 'password' in field.name:
            continue
        key = field.verbose_name if verbose_name else field.name
        f = getattr(instance, 'get_%s_display' % field.name, None)
        if f:
            value = f()
        else:
            value = getattr(instance, field.name, '')
        if value is True:
            value = _('Yes')
        elif value is False:
            value = _('No')
        elif value is None:
            value = ''
        result[key] = value
    f = getattr(instance, 'get_details_dict', None)
    if f:
        if verbose_name:
            key = _('Details')
        else:
            key = 'details'
        result[key] = f()
    return result


def instance_as_json(instance, max_length=None, verbose_name=True):
    result = OrderedDict()
    for k, v in instance_as_dict(instance, verbose_name).items():
        k = force_text(k)
        v = force_text(v)
        if max_length:
            v = v[:max_length]
        result[k] = v
    return json.dumps(result, ensure_ascii=False)


def instance_as_string(instance, verbose_name=True):
    return "\n".join(['%s: %s' % (k, v) for k, v in instance_as_dict(instance, verbose_name).items()])


def parse_get(path):
    res = urlparse(path)
    path = res.query
    if not path:
        path = res.path
    return dict([p.split('=') for p in path.split('&')])


def random_digit_challenge(max_length=None):
    secure_random = random.SystemRandom()
    if max_length is None:
        max_length = getattr(settings, 'CAPTCHA_LENGTH', 4)
    chars, ret = '0123456789', ''
    for i in range(max_length):
        ret += secure_random.choice(chars)
    return ret.upper(), ret


def unique(items, key=None):
    if key is None:
        def key(x):
            return x
    found = set([])
    keep = []
    for item in items:
        k = key(item)
        if k not in found:
            found.add(k)
            keep.append(item)
    return keep


def get_index(value, alist, default=-1):
    try:
        return alist.index(value)
    except ValueError:
        return default


def base32encode(number):
    alphabet = '0123456789abcdefghijklmnopqrstuv'
    result = ''
    while number:
        number, i = divmod(number, 32)
        result = alphabet[i] + result
    return result or alphabet[0]


def base36encode(number):
    alphabet = '0123456789abcdefghijklmnopqrstuvwxyz'
    result = ''
    while number:
        number, i = divmod(number, 36)
        result = alphabet[i] + result
    return result or alphabet[0]


def allowed_country(request):
    country = request.META.get('GEOIP_COUNTRY_CODE')
    return country in settings.HIDDEN_COUNTRIES


def correct_encoding(request):
    for item in request.GET.values():
        if '\ufffd' in item:
            request.encoding = 'cp1251'
            break


def content_disposition(file_name):
    ascii_name = unicodedata.normalize('NFKD', file_name).encode('ascii', 'ignore').decode()
    header = 'attachment; filename="{}"'.format(ascii_name)
    if ascii_name != file_name:
        quoted_name = urlquote(file_name)
        header += '; filename*=UTF-8\'\'{}'.format(quoted_name)

    return header


def is_bot(request):
    try:
        ua = force_text(request.META.get('HTTP_USER_AGENT', '').lower())
    except DjangoUnicodeDecodeError:
        ua = None
    if not ua:
        return True
    ua = re.sub(r'[^\w\- \\/\.\,]', '', ua)
    ua = force_text(ua).lower()
    keywords = ("bot", "crawler", "spider", "80legs", "baidu", "yahoo! slurp", "ia_archiver",
                "mediapartners-google",
                "lwp-trivial", "nederland.zoek", "ahoy", "anthill", "appie", "arale", "araneo", "ariadne",
                "atn_worldwide", "atomz", "bjaaland", "ukonline", "calif", "combine", "cosmos", "cusco",
                "cyberspyder", "digger", "grabber", "downloadexpress", "ecollector", "ebiness", "esculapio",
                "esther", "felix ide", "hamahakki", "kit-fireball", "fouineur", "freecrawl", "desertrealm",
                "gcreep", "golem", "griffon", "gromit", "gulliver", "gulper", "whowhere", "havindex", "hotwired",
                "htdig", "ingrid", "informant", "inspectorwww", "iron33", "teoma", "ask jeeves", "jeeves",
                "image.kapsi.net", "kdd-explorer", "label-grabber", "larbin", "linkidator", "linkwalker",
                "lockon", "marvin", "mattie", "mediafox", "merzscope", "nec-meshexplorer", "udmsearch", "moget",
                "motor", "muncher", "muninn", "muscatferret", "mwdsearch", "sharp-info-agent", "webmechanic",
                "netscoop", "newscan-online", "objectssearch", "orbsearch", "packrat", "pageboy", "parasite",
                "patric", "pegasus", "phpdig", "piltdownman", "pimptrain", "plumtreewebaccessor", "getterrobo-plus",
                "raven", "roadrunner", "robbie", "robocrawl", "robofox", "webbandit", "scooter", "search-au",
                "searchprocess", "senrigan", "shagseeker", "site valet", "skymob", "slurp", "snooper", "speedy",
                "curl_image_client", "suke", "www.sygol.com", "tach_bw", "templeton", "titin", "topiclink", "udmsearch",
                "urlck", "valkyrie libwww-perl", "verticrawl", "victoria", "webscout", "voyager", "crawlpaper",
                "webcatcher", "t-h-u-n-d-e-r-s-t-o-n-e", "webmoose", "pagesinventory", "webquest", "webreaper",
                "webwalker", "winona", "occam", "robi", "fdse", "jobo", "rhcs", "gazz", "dwcp", "yeti", "fido", "wlm",
                "wolp", "wwwc", "xget", "legs", "curl", "webs", "wget", "sift", "cmc")
    for kw in keywords:
        if kw in ua:
            return True
    return False
