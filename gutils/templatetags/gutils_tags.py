from django_jinja import library
from itertools import groupby
import jinja2
from django.utils.html import escape, escapejs
from django.utils.encoding import force_str, force_bytes
from django.conf import settings
from django.utils import formats
from django.utils.dateformat import format
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from django.utils.translation import gettext as _, pgettext as _pgettext
from django.template.loader import render_to_string
from markupsafe import Markup
from gutils import to_int, get_name
from gutils.strings import trim as _trim, linebreaksbr as _linebreaksbr, upper_first
from gutils.images import thumbnail, text_thumbnails
from gutils.decorators import safe
from gutils import numbers
from gutils.strings import format_phone as _format_phone, clean_phone, escape_url as _escape_url
from gutils.decimals import decimal_format
from gutils.dates import format_date_range as _format_date_range
from django.utils.http import urlencode as _urlencode
from django.forms.widgets import Media
from decimal import Decimal
import calendar
import datetime
import os
import re
from urllib.parse import quote


@library.filter
def default(value, arg=''):
    if value:
        return force_str(value)
    return Markup(arg)


@library.global_function
def static(path):
    return staticfiles_storage.url(path)


_counter = 0


@library.global_function
def counter(initial=None):
    global _counter
    if initial is not None:
        _counter = initial
        return ''
    _counter += 1
    return _counter


def _static_register(context, data, media='all'):
    """
    data = 'path/example.js'
    data = ['path/example.css', 'path/example.js']
    data = {'all': ('example1.css', 'example2.css')}
    data = form.media
    """
    if not data:
        return
    if isinstance(data, Media):
        _static_register(context, getattr(data, '_js'))
        _static_register(context, getattr(data, '_css'))
        return
    if isinstance(data, dict):
        for media, css in data.items():
            _static_register(context, css, media)
        return
    if type(data) not in (tuple, list):
        data = [data]
    for path in data:
        if path.startswith('http://') or path.startswith('https://'):
            continue
        if path.endswith('.js'):
            if path not in context['static_js']:
                context['static_js'].append(path)
        elif path.endswith('.css'):
            if media in context['static_css'].keys():
                if path not in context['static_css'][media]:
                    context['static_css'][media].append(path)
            else:
                context['static_css'][media] = [path]


@library.global_function
@jinja2.pass_context
def static_register(context, path, media='all'):
    _static_register(context, path, media)
    return ''


@library.global_function
@jinja2.pass_context
@safe
def static_render(context):
    result = []
    for js in context['static_js']:
        result.append('<script type="text/javascript" src="%s"></script>' % staticfiles_storage.url(js))
    for media, items in context['static_css'].items():
        for css in items:
            result.append('<link type="text/css" href="%s" media="%s" rel="stylesheet" />' %
                          (staticfiles_storage.url(css), media))
    return '\n'.join(result)


@library.global_function
def pgettext(context_name, message):
    return _pgettext(context_name, message)


@library.filter
@safe
def linebreaksbr(value):
    return _linebreaksbr(value)


@library.filter
def get_item(obj, key):
    if isinstance(obj, dict):
        result = obj.get(key)
    else:
        result = getattr(obj, key)
    if hasattr(result, '__call__'):
        return result(obj)
    return result


@library.global_function
def regroup(items, key):
    def getx(item, key):
        try:
            result = getattr(item, key)
            if callable(result):
                return result()
            else:
                return result
        except AttributeError:
            return item[key]

    if not items:
        return []
    return [{'grouper': k, 'list': list(v)} for k, v in groupby(items, lambda obj: getx(obj, key))]


@library.filter
def yesno(value, arg=None):
    if arg is None:
        arg = _('yes,no,---')
    bits = arg.split(',')
    if len(bits) < 2:
        return value  # Invalid arg.
    try:
        yes, no, maybe = bits
    except ValueError:
        # Unpack list of wrong size (no "maybe" value provided).
        yes, no, maybe = bits[0], bits[1], bits[1]
    if value is None:
        return maybe
    if value:
        return yes
    return no


pos_inf = 1e200 * 1e200
neg_inf = -1e200 * 1e200
nan = (1e200 * 1e200) // (1e200 * 1e200)
special_floats = [str(pos_inf), str(neg_inf), str(nan)]


@library.filter
@safe
def floatformat(text, arg=-1):
    return decimal_format(text, arg)


@library.filter
def format_phone(value):
    return _format_phone(clean_phone(value))


@library.filter
@safe
def thumb(value, size='', fake=False, exclude=None):
    return thumbnail(value, size, fake=fake, exclude=exclude)


@library.filter
def text_thumb(text):
    return text_thumbnails(text)


@library.filter
@safe
def default_image(value, name=''):
    if not name:
        name = os.path.join(settings.MEDIA_URL, 'no.png')
    if value:
        return value
    return name


@library.filter
def number_format(value, decimal_pos=0):
    try:
        return formats.number_format(value, decimal_pos=decimal_pos, force_grouping=True)
    except ValueError:
        return value


@library.filter
def hide(value, hide=True):
    if not hide:
        return value
    if not isinstance(value, str):
        value = force_str(value)
    return '*' * len(value)


@library.global_function
@safe
def yesno_icon(value, title=""):
    result = 'fa-minus-circle'
    if value:
        result = 'fa-check-circle'
    t = ' title="%s"' % escape(title) if title else ''
    return '<span class="fa %s"%s></span>' % (result, t)


@library.global_function
def get_setting(config):
    if 'PASS' in config:
        return ''
    return getattr(settings, config, '')


@library.global_function
def domain():
    return settings.DOMAIN


@library.global_function
def site_url():
    return '%s%s' % (settings.SITE_SCHEMA, settings.DOMAIN)


@library.global_function
@jinja2.pass_context
def absolute_url(context, url, *args):
    if '/' in url:
        return '%s://%s%s' % (context['scheme'], settings.DOMAIN, url)
    else:
        return '%s://%s%s' % (context['scheme'], settings.DOMAIN, reverse(url, args=args))


@library.global_function
def sitename():
    return settings.SITENAME


@library.filter
def date(value, arg=None):
    if not value:
        return ''
    if not arg:
        if isinstance(value, datetime.datetime):
            arg = 'DATETIME_FORMAT'
        else:
            arg = 'DATE_FORMAT'
    try:
        return formats.date_format(value, arg, use_l10n=True)
    except AttributeError:
        try:
            return format(value, arg)
        except AttributeError:
            return ''


@library.filter
def time(value, arg):
    if not value:
        return ''
    if not arg:
        arg = 'TIME_FORMAT'
    if arg == 'DATETIME_FORMAT' or arg == 'DATE_FORMAT':
        return formats.date_format(value, arg, use_l10n=True)
    try:
        return formats.time_format(value, arg, use_l10n=True)
    except AttributeError:
        try:
            return format(value, arg)
        except AttributeError:
            return ''


@library.global_function
def now():
    return datetime.datetime.now()


@library.global_function
def format_date_range(date_from, date_to):
    return _format_date_range(date_from, date_to)


@library.global_function
def relative_date(value):
    day = datetime.date.today()
    if value == 'first-day':
        day = day.replace(day=1)
    elif value == 'last-day':
        day = day.replace(day=calendar.monthrange(day.year, day.month)[1])
    elif value == 'prev-month-first-day':
        day = (day.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    elif value == 'prev-month-last-day':
        day = (day.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
        day = day.replace(day=calendar.monthrange(day.year, day.month)[1])
    return date(day)


@library.filter
def trim(value, size):
    return _trim(value, size)


@library.filter
def urlquote(value):
    return quote(force_bytes(value))


@library.global_function
@safe
def urlencode(**kwargs):
    return _urlencode(kwargs)


@library.global_function
def is_string(value):
    return isinstance(value, string_types)


@library.filter
def field_name(model, field_name, capitalize=True):
    result = model._meta.get_field(field_name).verbose_name
    if capitalize:
        return upper_first(result)
    return result


@library.filter
def field_value(obj, field_name):
    result = getattr(obj, field_name, '')
    if callable(result):
        result = result()
    if result is None:
        result = ''
    elif isinstance(result, datetime.datetime):
        result = formats.date_format(result, 'DATETIME_FORMAT', use_l10n=True)
    elif isinstance(result, datetime.date):
        result = formats.date_format(result, 'DATE_FORMAT', use_l10n=True)
    elif isinstance(result, bool):
        result = _('Yes') if result else _('No')
    return result


@library.filter
def human_number(value):
    orig = force_str(value)
    new = re.sub(r"^(-?\d+)(\d{3})", r'\g<1> \g<2>', orig)
    if orig == new:
        return new
    else:
        return human_number(new)


@library.filter
@safe
def escape_url(value):
    return _escape_url(value)


@library.filter
@safe
def escape_csv(value):
    if not value:
        return ''
    value = force_str(value)
    if value.startswith('='):
        value = re.sub(r'^=+', '', value)
    value = re.sub(r'[\x00-\x19]', '', value)
    return value.replace(';', ',').replace('\n', ' ').replace('\r', ' ')


@library.filter
@safe
def as_decimal(value):
    if not value:
        return ''
    value = force_str(value)
    return value.replace('.', ',')


@library.global_function
@jinja2.pass_context
@safe
def unsafe(context, value):
    if value is None:
        return ''
    if not context.get('mark_unsafe', False):
        return value
    if isinstance(value, int):
        return 'integer:%s' % value
    if isinstance(value, (float, Decimal)):
        return 'decimal:%s' % value
    if isinstance(value, datetime.datetime):
        return 'datetime:%s' % value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, datetime.date):
        return 'date:%s' % value.strftime('%Y-%m-%d')
    return value


@library.filter
def rows(thelist, n):
    """
    Break a list into ``n`` rows, filling up each row to the maximum equal
    length possible. For example::

        >>> l = range(10)

        >>> rows(l, 2)
        [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]

        >>> rows(l, 3)
        [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]

        >>> rows(l, 4)
        [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]

        >>> rows(l, 5)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]

        >>> rows(l, 9)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [], [], [], []]

        # This filter will always return `n` rows, even if some are empty:
        >>> rows(range(2), 3)
        [[0], [1], []]
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    list_len = len(thelist)
    split = list_len // n

    if list_len % n != 0:
        split += 1
    return [thelist[split * i:split * (i + 1)] for i in range(n)]


@library.filter
def rows_distributed(thelist, n):
    """
    Break a list into ``n`` rows, distributing columns as evenly as possible
    across the rows. For example::

        >>> l = range(10)

        >>> rows_distributed(l, 2)
        [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]

        >>> rows_distributed(l, 3)
        [[0, 1, 2, 3], [4, 5, 6], [7, 8, 9]]

        >>> rows_distributed(l, 4)
        [[0, 1, 2], [3, 4, 5], [6, 7], [8, 9]]

        >>> rows_distributed(l, 5)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]

        >>> rows_distributed(l, 9)
        [[0, 1], [2], [3], [4], [5], [6], [7], [8], [9]]

        # This filter will always return `n` rows, even if some are empty:
        >>> rows(range(2), 3)
        [[0], [1], []]
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    list_len = len(thelist)
    split = list_len // n

    remainder = list_len % n
    offset = 0
    rows = []
    for i in range(n):
        if remainder:
            start, end = (split + 1) * i, (split + 1) * (i + 1)
        else:
            start, end = split * i + offset, split * (i + 1) + offset
        rows.append(thelist[start:end])
        if remainder:
            remainder -= 1
            offset += 1
    return rows


@library.filter
def columns(thelist, n):
    """
    Break a list into ``n`` columns, filling up each column to the maximum equal
    length possible. For example::

    # Note that this filter does not guarantee that `n` columns will be
    # present:
    >>> pprint(columns(range(4), 3), width=10)
    [[0, 2],
    [1, 3]]
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    list_len = len(thelist)
    split = list_len // n
    if list_len % n != 0:
        split += 1
    return [thelist[i::split] for i in range(split)]


@library.filter
def parts(thelist, n):
    """
    >>> pprint(parts(range(10), 2))
    >>> [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    result = []
    part = []
    i = 0
    for item in thelist:
        if i == n:
            i = 0
            result.append(part)
            part = []
        part.append(item)
        i += 1
    result.append(part)
    return result


@library.filter
def parts2(thelist, n):
    """
    >>> pprint(parts(range(10), 3))
    >>> [[0, 1, 2], [2, 3, 4], [5, 6, 7], [8, None, None]]
    """
    result = parts(thelist, n)
    if not result or len(result) <= 1:
        return result
    m = len(result[-1])
    if m < n:
        result[-1] += [None] * (n - m)
    return result


@library.global_function
@safe
def mailto(emails):
    results = []
    emails = emails.split(',')
    for email in emails:
        email = email.split('@')
        html = '''
<script type="text/javascript">
    var mt1 = '%s';
    var mt2 = '%s';
    var mt = mt1.split('').reverse().join('') + '@' + mt2.split('').reverse().join('');
    document.write('<a href="'+'mailto:'+mt+'">'+mt+'</a>');
</script>''' % (email[0][::-1], email[1][::-1])
        results.append(html)
    return '\n,\n'.join(results)


@library.global_function
@jinja2.pass_context
@safe
def input_next(context):
    return '<input type="hidden" name="next" value="%s" />' % escape(context.get('next_url', ''))


@library.global_function
@jinja2.pass_context
@safe
def if_url_name(context, value, *args):
    url_name = context.get('url_name', '')
    for a in args:
        if url_name == a:
            return value
    return ''


def _paginator(context, page):
    path = context['path']
    page_url = '?page='
    query = re.findall(r'\?(.+)', context['full_path'])
    if query:
        params = []
        for p in query[0].split('&'):
            if not p.startswith('page='):
                params.append(p)
        if params:
            page_url = '?%s&page=' % '&'.join(params)
            path = '%s?%s' % (path, '&'.join(params))
    has_first = False
    has_last = False
    page_range = []
    if getattr(page, 'paginator', False):
        if page.paginator.num_pages < 8:
            page_range = page.paginator.page_range
        else:
            begin = page.number - 2
            end = page.number + 2
            if begin == 2:
                begin = 1
            elif begin > 2:
                has_first = True
            if end == page.paginator.num_pages - 1:
                end = page.paginator.num_pages
            elif end < page.paginator.num_pages - 1:
                has_last = True
            if begin < 1:
                end = end - begin
                begin = 1
            elif end > page.paginator.num_pages:
                begin = begin - (end - page.paginator.num_pages)
                end = page.paginator.num_pages
            page_range = range(begin, end + 1)
    return {'page': page, 'page_url': page_url, 'path': path,
            'page_range': page_range, 'has_first': has_first, 'has_last': has_last}


@library.global_function
@jinja2.pass_context
@library.render_with('gutils/admin_paginator.html')
def admin_paginator(context, page):
    return _paginator(context, page)


@library.global_function
@jinja2.pass_context
@library.render_with('gutils/paginator.html')
def get_paginator(context, page):
    return _paginator(context, page)


@library.global_function
@library.render_with('gutils/form_show.html')
@jinja2.pass_context
def form_show(context, form=None, formset=None, **kwargs):
    data = kwargs.copy()
    data['form'] = form
    data['formset'] = formset
    data['title'] = kwargs.get('title')
    data['form_buttons'] = kwargs.get('form_buttons') or []
    data['action'] = kwargs.get('action') or ''
    data['method'] = kwargs.get('method') or 'post'
    if data['method'].lower() == 'get':
        data['hide_csrf'] = True
    else:
        data['hide_csrf'] = kwargs.get('hide_csrf', False)
    if data['action'] and data['action'].find('/') < 0:
        data['action'] = reverse(data['action'])
    data['enctype'] = kwargs.get('enctype', None)
    data['form_tag'] = kwargs.get('form_tag', True)
    data['autocomplete'] = kwargs.get('autocomplete', True)
    data['submit_text'] = kwargs.get('submit_text') or _('Save')
    data['form_details'] = kwargs.get('form_details')
    data['help_icons'] = kwargs.get('help_icons', {})
    data['back'] = kwargs.get('back', False)
    data['is_popup'] = context.get('is_popup', False)
    data['csrf_token'] = context.get('csrf_token', None)
    return data


@library.global_function
@jinja2.pass_context
@safe
def admin_form_show(context, form=None, formset=None, **kwargs):
    data = kwargs.copy()
    data['form'] = form
    data['formset'] = formset
    data['formset_label'] = ''
    if formset and hasattr(formset.forms[0].__class__, '_meta'):
        data['formset_label'] = get_name(formset.forms[0].__class__._meta.model, plural=True)
    data['title'] = kwargs.get('title')
    data['form_buttons'] = kwargs.get('form_buttons')
    data['formset_title'] = kwargs.get('formset_title')
    data['action'] = kwargs.get('action') or ''
    if data['action'] and data['action'].find('/') < 0:
        data['action'] = reverse(data['action'])
    data['method'] = kwargs.get('method') or 'post'
    data['enctype'] = kwargs.get('enctype', None)
    data['form_tag'] = kwargs.get('form_tag', True)
    data['formset_horizontal'] = kwargs.get('formset_horizontal', False)
    data['save_on_top'] = kwargs.get('save_on_top', False)
    data['autocomplete'] = kwargs.get('autocomplete', True)
    data['submit_text'] = kwargs.get('submit_text') or _('Save')
    data['form_details'] = kwargs.get('form_details')
    if data['method'].lower() == 'get':
        data['hide_csrf'] = True
    else:
        data['hide_csrf'] = kwargs.get('hide_csrf', False)
    data['reload_when_close'] = kwargs.get('reload_when_close') or False
    data['is_popup'] = context.get('is_popup', False)
    data['csrf_token'] = context.get('csrf_token', None)
    if form:
        template_name = 'gutils/admin_form_show.html'
    elif formset:
        template_name = 'gutils/admin_formset_show.html'
    return render_to_string(template_name, data)


@library.global_function
@jinja2.pass_context
@safe
def admin_form_close_button(context):
    if context.get('is_popup'):
        result = '<input type="button" name="back" value="%s" class="btn-close-popup"/>' % _('Close')
    else:
        result = '<input type="button" name="back" value="%s" onclick="history.back();"/>' % _('Back')
    return result


@library.global_function
@library.render_with('gutils/admin_filter_show.html')
@jinja2.pass_context
def admin_filter_show(context, form, **kwargs):
    return {'form': form, 'path': context.get('path', '')}


@library.global_function
@jinja2.pass_context
@safe
def admin_table_sort(context, sort, name, title=''):
    if not sort:
        if name != title:
            return '<abbr title="%s">%s</abbr>' % (upper_first(title), upper_first(name))
        else:
            return name or ''
    current = context.get('sort', '')
    if not current:
        view = context.get('view')
        if view and hasattr(view, 'sort'):
            current = view.sort
    if current and current.startswith('-'):
        c0 = current.replace('-', '')
    else:
        c0 = current
    if sort.startswith('-'):
        s0 = sort.replace('-', '')
    else:
        s0 = sort
    icon = ''
    if c0 == s0:
        if current[0] == '-':
            icon = 'fa-sort-down'
        else:
            icon = 'fa-sort-up'
        if current == sort:
            if sort.startswith('-'):
                sort = s0
            else:
                sort = ','.join(['-%s' % s for s in sort.split(',')])
    else:
        icon = ''
    if not title:
        title = name
    query_dict = context['query_dict'].copy()
    query_dict['sort'] = sort
    if icon:
        return '<a href="?%s" class="sort" title="%s">%s <span class="fa %s"></span></a>' % \
            (query_dict.urlencode(), upper_first(title), upper_first(name), icon)
    else:
        return '<a href="?%s" class="sort" title="%s">%s</a>' % \
            (query_dict.urlencode(), upper_first(title), upper_first(name))


def _admin_item_change(item, fieldname, title='', icons=None, confirm='', user=None, url=None):
    app_name = item._meta.app_label
    model_name = item.__class__.__name__.lower()
    model_path = '%s.%s' % (app_name, model_name)
    value = item
    if icons:
        attr_icons = 'data-icons="%s"' % icons
    else:
        # icons = 'negative fa-minus-square,positive fa-check-square'
        icons = 'fa-minus-circle negative,fa-check-circle positive'
        attr_icons = ''
    icons = icons.split(',')
    for f in fieldname.split('.'):
        value = getattr(value, f)
    icon = icons[to_int(value)]
    if not (getattr(item.__class__, 'EDIT_PERMISSIONS', None) or user.has_perm("%s.edit_%s" % (app_name, model_name))):
        return '<span class="fa %s" title="%s"></span>' % \
               (icon, _('Do not have permission to change'))
    if confirm:
        confirm = ' onclick="return confirm(\'%s\')";' % escapejs(confirm)
        confirm = force_str(confirm)
    else:
        confirm = ''
    if not url:
        url = reverse('admin-item-change', args=[model_path, item.pk, fieldname])
    return '<a class="item-change fa %s" %s href="%s" title="%s"%s></a>' % (icon, attr_icons, url, title, confirm)


@library.global_function
@jinja2.pass_context
@safe
def admin_item_change(context, item, fieldname, title='', icon=None, confirm=False, url=None):
    '''
    example: {{ item_change(order, 'is_active', 'Change') }}
    '''
    return _admin_item_change(item, fieldname, title, icon, confirm, context['user'], url)


@library.global_function
@jinja2.pass_context
@safe
def item_delete(context, item, title='', confirm=''):
    app_name = item._meta.app_label
    model = item.__class__.__name__.lower()
    model_path = '%s.%s' % (app_name, model)
    if confirm:
        confirm = ' onclick="return confirm(\'%s\')";' % escapejs(confirm)
    if not title:
        title = _('Delete')
    url = reverse('admin-item-delete', args=[model_path, item.pk])
    return '<a class="item-delete popup" href="%s" title="%s"%s><span class="danger fa fa-remove"></span></a>' % \
        (url, title[:], confirm)


@library.global_function
@safe
def admin_bool_icon(value, icons=None, title=''):
    if not icons:
        icons = 'fa-minus-circle red, fa-check-circle green'
    value = to_int(value or 0)
    icon = icons.split(',')[value]
    if ',' in title:
        title = title.split(',')[value]
    return '<span class="fa %s" title="%s"></span>' % (icon, title)


@library.global_function
@jinja2.pass_context
@safe
def generate_get(context, **kwargs):
    query_dict = context['query_dict'].copy()
    for k, v in kwargs.items():
        query_dict[k] = v
    return '?%s' % query_dict.urlencode()


@library.filter
def field_class(field, lower=True):
    value = field.field.__class__.__name__
    if lower:
        return '-'.join([s.lower() for s in re.findall('[A-Z][a-z]+', value)])
    else:
        return value


@library.global_function
@jinja2.pass_context
def money_words(context, value, currency_name='UAH'):
    language = context['LANGUAGE_CODE']
    return numbers.get_money(language, currency_name).make(value)
