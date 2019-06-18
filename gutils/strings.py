# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
from django.utils.html import escape, strip_tags
from django.utils.encoding import force_text, smart_bytes
from django.conf import settings
from django.utils.functional import Promise
from django.utils.encoding import force_text
from django.core.serializers.json import DjangoJSONEncoder
from unidecode import unidecode
from decimal import Decimal
import random

try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote


CLEAN_NUMBER = re.compile(r'[^A-Z0-9АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯЫЭЪ]+')
CLEAN_NUMBER_SOFT = re.compile(r'[^A-Z0-9АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯЫЭЪ \-\.\\/\+]+')
CLEAN_VALUE = re.compile(r'[^\d\.]')

# CLEAN_STRING = re.compile(u'[\U00010000-\U0010ffff]+', flags=re.UNICODE)
try:
    CLEAN_STRING = re.compile("["
                              "\U0001F600-\U0001F64F"  # emoticons
                              "\U0001F300-\U0001F5FF"  # symbols & pictographs
                              "\U0001F680-\U0001F6FF"  # transport & map symbols
                              "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                              "]+", flags=re.UNICODE)

except re.error:
    CLEAN_STRING = re.compile("(\ud83d[\ude00-\ude4f])|"  # emoticons
                              "(\ud83c[\udf00-\uffff])|"  # symbols & pictographs (1 of 2)
                              "(\ud83d[\u0000-\uddff])|"  # symbols & pictographs (2 of 2)
                              "(\ud83d[\ude80-\udeff])|"  # transport & map symbols
                              "(\ud83c[\udde0-\uddff])"   # flags (iOS)
                              "+", flags=re.UNICODE)


class JSONEncoder(DjangoJSONEncoder):

    def default(self, obj):
        if isinstance(obj, Promise):
            return force_text(obj)
        elif isinstance(obj, Decimal):
            return float(obj)
        return super(JSONEncoder, self).default(obj)


def translate(string):
    if string is None:
        return None
    return unidecode(string)


def get_slug(value, max_length=100):
    if value is None:
        return None
    value = force_text(value)
    value = unidecode(value)
    value = re.sub('[\.\']', '', value).strip().lower()
    value = re.sub('[^\w]', '-', value).strip().lower()
    value = re.sub('[-\s]+', '-', value)
    value = re.sub('\-$', '', value)
    value = re.sub('^\-', '', value)
    return value[:max_length]


def check_slug(Model, slug, pk=None, max_length=100):
    slug = slug[:max_length]
    check = Model.objects.filter(slug=slug).exclude(pk=pk).exists()
    while check:
        slug = "%s~%s" % (slug[:max_length - 4], random.randint(0, 99))
        check = Model.objects.filter(slug=slug).exclude(pk=pk).exists()
    return slug


def clean_number(number, soft=False, max_length=None):
    if max_length is None:
        max_length = getattr(settings, 'GUTILS_MAX_NUMBER_LENGTH', 40)
    if not number:
        return ''
    result = number.upper()
    if soft:
        result = CLEAN_NUMBER_SOFT.sub('', result)[:max_length].strip()
    else:
        result = CLEAN_NUMBER.sub('', result)[:max_length].strip()
    return result


def correct_number(number):
    if not number:
        return ''
    number = number.upper()
    number = force_text(number)
    abc_ru = 'ЙЦУКЕНГШЩЗФІВАПРОЛДЯЧСМИТЬ'
    abc_en = 'QWERTYUIOPASDFGHJKLZXCVBNM'
    table = dict((ord(c1), ord(c2)) for c1, c2 in zip(abc_ru, abc_en))
    return clean_number(number.translate(table))


def clean_non_alphanumerics(value, replace_to=''):
    not_letters_or_digits = '!"#%\'()*+,-./:;<=>?@[\\]^_`{|}~'
    translate_table = dict((ord(char), replace_to)
                           for char in not_letters_or_digits)
    return value.translate(translate_table)


def clean_decimal(value, default=""):
    value = value.replace(',', '.')
    value = CLEAN_VALUE.sub('', value)
    if not value:
        return default
    return value.upper()


def clean_string(value):
    return CLEAN_STRING.sub('', value)


def trim(value, size=100):
    size = int(size)
    try:
        if len(value) > size:
            value = '%s…' % value[:size]
        return value
    except Exception:
        return value


def clean_email(email):
    if email is None:
        return ''
    return email.strip()


def clean_phone(phone):
    if not phone:
        return ''
    phone = re.sub(r'[^\d]', '', phone)
    if len(phone) == 10:
        phone = '38%s' % phone
    if len(phone) == 11:
        phone = '3%s' % phone
    return phone[:12]


def format_phone(phone):
    items = re.sub(r'[^\d\,;]', '', phone)
    items = re.findall(r'(\w+)', items)
    result = []
    for p in items:
        pl = len(p)
        if pl == 12:
            result.append("+%s (%s) %s-%s-%s" % (p[0:2], p[2:5], p[5:8], p[8:10], p[10:12]))
        elif pl == 11:
            result.append("+%s (%s) %s-%s-%s" % (p[0], p[1:4], p[4:7], p[7:9], p[9:11]))
        elif pl == 10:
            result.append("(%s) %s-%s-%s" % (p[:3], p[3:6], p[6:8], p[8:10]))
        elif pl == 7:
            result.append("%s-%s-%s" % (p[:3], p[3:5], p[5:7]))
        elif pl == 6:
            result.append("%s-%s-%s" % (p[:2], p[2:4], p[4:6]))
        elif pl == 5:
            result.append("%s-%s-%s" % (p[:1], p[1:3], p[3:5]))
        else:
            result.append(p)
    return ", ".join(result)


def plain_text(text, n=0):
    result = strip_tags(text).replace('&nbsp;', ' ').replace('"', '').strip()
    result = re.sub(r'\s+', ' ', result)
    if n and len(result) > n:
        return '%s...' % result[:n]
    return result


def hide_text(value, force=False):
    if not value:
        return ''
    value = force_text(value)
    if force:
        return '*' * len(value)
    if len(value) > 2:
        return value[0] + '*' * (len(value) - 2) + value[-1]
    else:
        return '***'


def escape_url(value):
    return quote(smart_bytes(value))


def upper_first(x):
    if not x:
        return ''
    return x[0].upper() + x[1:]


def linebreaksbr(value, use_escape=True):
    if value is None:
        return ''
    if use_escape:
        value = escape(value)
    return value.replace('\r\n', '<br /> ').replace('\n', '<br /> ').replace('\r', '<br />')
