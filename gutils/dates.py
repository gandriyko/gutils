from django.conf import settings
from datetime import timedelta
from django.utils import formats
from django.db.models import Q
from django.utils.formats import get_format
import datetime
import random


def date_range(from_date=datetime.datetime.now(), to_date=None, days=1):
    while (to_date is None) or (from_date <= to_date):
        yield from_date
        from_date = from_date + datetime.timedelta(days=days)
    return


def random_date(start, end):
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + datetime.timedelta(seconds=random_second)


def date_month_ranges(date_from=None, date_to=None):
    date_from = date_from or datetime.datetime.now()
    date_to = date_to or datetime.datetime.now()
    if isinstance(date_from, datetime.datetime):
        date_from = datetime.datetime.date(date_from)
    if isinstance(date_to, datetime.datetime):
        date_to = datetime.datetime.date(date_to)
    d1 = date_from
    result = []
    while d1 <= date_to:
        d2 = d1 + datetime.timedelta(days=(32 - d1.day))
        d2 = d2.replace(day=1) + datetime.timedelta(days=-1)
        if d2 < date_to:
            result.append((d1, d2))
        else:
            result.append((d1, date_to))
            break
        d1 = d2 + datetime.timedelta(days=1)
    return result


def date_filter(field, date_from, date_to):
    if date_from and date_to:
        return Q(**{'%s__gte' % field: date_from, '%s__lt' % field: date_to + timedelta(days=1)})
    elif date_from:
        return Q(**{'%s__gte' % field: date_from})
    elif date_to:
        return Q(**{'%s__lt' % field: date_to + timedelta(days=1)})
    return Q()


def year_filter(field, year_from, year_to):
    if year_from and year_to:
        return Q(**{'%s__gte' % field: year_from, '%s__lte' % field: year_to})
    elif year_to:
        return Q(**{'%s__gte' % field: year_from})
    elif year_to:
        return Q(**{'%s__lt' % field: year_from})
    return Q()


def year_slice(year_from, year_to, range=5):
    result = []
    year = year_to
    while year > year_from:
        result.append([year - range, year])
        year -= range + 1
    if year > year_from:
        result.append([year_from, year])
    return result


def working_days(date_from, date_to):
    days = (date_from + timedelta(x + 1) for x in range((date_to - date_from).days))
    return sum(1 for day in days if day.weekday() < settings.GUTILS_WORKING_DAYS)


def add_working_days(date_from, days):
    days = min(abs(days), 60)  # force limit
    if isinstance(date_from, datetime.datetime):
        date_to = date_from.date()
    else:
        date_to = date_from
    d = 0
    while d < days:
        date_to += timedelta(days=1)
        if date_to.weekday() < settings.GUTILS_WORKING_DAYS:
            d += 1
    return date_to


def format_date_range(date_from, date_to):
    return '%s%s%s' % (formats.date_format(date_from, 'DATE_FORMAT', use_l10n=True) if date_from else '',
                       formats.get_format('DATE_SEPARATOR'),
                       formats.date_format(date_to, 'DATE_FORMAT', use_l10n=True) if date_to else '')


def to_date(value):
    if not value:
        return
    for f in get_format('DATETIME_INPUT_FORMATS'):
        try:
            return datetime.datetime.strptime(value, f)
        except (ValueError, TypeError):
            continue
    for f in get_format('DATE_INPUT_FORMATS'):
        try:
            return datetime.datetime.strptime(value, f)
        except (ValueError, TypeError):
            continue


def utc_to_local(utc_dt):
    import pytz
    local_tz = pytz.timezone(settings.TIME_ZONE)
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)
