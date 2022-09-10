from django.conf import settings
from django.urls import reverse
from django.core.exceptions import FieldDoesNotExist
from django.utils.html import escape, escapejs, strip_tags
from django.utils.encoding import smart_text, force_str
from django.utils.translation import gettext_lazy as _
from django.template import engines
from django.utils import formats
from gutils import get_attribute, to_int
from gutils.decimals import to_decimal
from gutils.images import thumbnail
from gutils.strings import format_phone, upper_first
from gutils.templatetags.gutils_tags import date
from gutils.templatetags.gutils_tags import _admin_item_change, admin_bool_icon
import itertools
import weakref
import datetime
import os


class Column(object):
    name = None
    icon = None
    field = None
    tooltip = None
    tooltip_field = None
    verbose_name = None
    header_name = None
    sort = None
    short_header = False
    style = 'str'
    safe = False
    default = ''
    trim = None
    empty = False
    attrs = None

    edit = False
    edit_fields = None
    edit_form_class = None

    _counter = itertools.count()

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if not getattr(self, 'index', None):
            self.index = next(Column._counter)
        if self.attrs:
            self.attrs = self.attrs.copy()
        else:
            self.attrs = {}

    @property
    def view(self):
        view_ref = getattr(self, 'view_ref')
        if view_ref:
            return self.view_ref()

    @view.setter
    def view(self, view):
        self.view_ref = weakref.ref(view)

    def init(self, view, name):
        self.name = name
        if not self.field:
            self.field = name
        self.view = view
        try:
            if self.view.model:
                field_class = self.view.model._meta.get_field(self.name)
            else:
                field_class = self.view.queryset.model._meta.get_field(self.name)
        except FieldDoesNotExist:
            field_class = None
        if self.verbose_name is None and field_class:
            if hasattr(field_class, 'verbose_name'):
                self.verbose_name = upper_first(field_class.verbose_name)
            else:
                self.verbose_name = ''
        if self.sort is None and field_class:
            self.sort = name
        if self.header_name is None:
            self.header_name = self.verbose_name
        if self.icon:
            self.short_header = True
        if self.header_name and self.short_header:
            self.header_name = self.header_name[:1]
        self.edit = any((self.edit, self.edit_form_class, self.edit_fields))
        if self.edit:
            self.style = '%s col-editable' % self.style
            self.attrs['data-column'] = self.name

    def get_value(self, item):
        field = self.field or self.name
        if not field:
            return
        if callable(field):
            return field(item)
        return get_attribute(item, field, call=True)

    def get_tooltip_value(self, item):
        if self.tooltip:
            if callable(self.tooltip):
                tooltip = self.tooltip(item)
            else:
                tooltip = self.tooltip
            return tooltip
        if not self.tooltip_field:
            return ''
        return get_attribute(item, self.tooltip_field)

    def display(self, item):
        if not self.name:
            return
        value = self.get_value(item)
        if self.empty and not value:
            return ''
        if value is not None:
            value = smart_text(value)
            if self.trim and len(value) > self.trim:
                value = strip_tags(value).replace('<', '').replace('>', '')
                value = '<span title="%s">%s ' \
                        '<i class="fa fa-angle-double-right red"></i></span>' % (value, value[:self.trim])
                self.safe = True
            tooltip = self.get_tooltip_value(item)
            if tooltip:
                if isinstance(value, str):
                    value = strip_tags(value).replace('<', '').replace('>', '')
                return '<span title="%s">%s</span>' % (tooltip, value)
            return value
        return ''

    def get_display(self, item):
        func = getattr(self.view, 'get_%s_display' % self.name, None)
        if func:
            result = func(item)
        else:
            result = self.display(item)
        if result is None:
            return self.default
        if not self.safe:
            return escape(result)
        return result

    def get_attrs(self, item):
        return self.attrs or {}

    def get_style(self, item=None):
        return self.style


class TipMixin(object):
    tip_url = None
    tip_args = ['pk']

    def get_tip_url(self, item):
        if not self.tip_url:
            return ''
        args = []
        for attr in self.tip_args:
            a = get_attribute(item, attr)
            if a is None:
                return ''
            args.append(a)
        return reverse(self.tip_url, args=args)


class TemplateColumn(Column):
    safe = True

    def __init__(self, *args, **kwargs):
        super(TemplateColumn, self).__init__(*args, **kwargs)
        env = engines["jinja2"]
        self.template = env.from_string(self.template)

    def display(self, item):
        return self.template.render({'item': item})


class IntegerColumn(Column):
    style = 'int'
    default = 0

    def display(self, item):
        value = self.get_value(item)
        if not value and self.default is not None:
            return self.default
        return value


class PercentColumn(Column):
    style = 'int'
    safe = True
    short_header = True

    def display(self, item):
        value = self.get_value(item)
        if value > 95:
            color = 'green'
        elif value <= 10:
            color = 'red'
        else:
            color = 'orange'
        return '<span class="%s">%s%%</span>' % (color, value)


class DecimalColumn(Column):
    style = 'decimal'
    decimal_places = 2
    default = None
    discard_zeros = False
    colorize = False
    sign = False
    color = ''

    def display(self, item):
        value = self.get_value(item)
        if value is None:
            return ''
        if not value and self.default is not None:
            return self.default
        v = value = to_decimal(value, self.decimal_places)
        value_as_text = force_str(value)
        if self.colorize:
            if value >= 0:
                self.color = 'green'
            else:
                self.color = 'red'
        if self.discard_zeros and (value_as_text.endswith('.00') or '.' not in value_as_text):
            value = formats.number_format(value, decimal_pos=0, force_grouping=True)
        else:
            value = formats.number_format(value, decimal_pos=self.decimal_places, force_grouping=True)
        if self.sign and v > 0:
            value = '+%s' % value
        if self.color:
            return '<span class="%s">%s</span>' % (self.color, value)
        return value


class PhoneColumn(Column):
    style = 'phone'

    def display(self, item):
        return format_phone(self.get_value(item))


class SecondColumn(Column):
    style = 'int'

    def display(self, item):
        value = self.get_value(item)
        return datetime.timedelta(seconds=value)


class TypedColumn(Column):
    icons = {}
    choices = []
    safe = True
    only_icon = False

    def display(self, item):
        value = self.get_value(item)
        icon = style = ''
        for i in self.choices:
            if i[0] == value:
                icon = i[1].get('icon')
                style = i[1].get('style')
                break
        value_display = get_attribute(item, 'get_%s_display' % (self.field or self.name), call=True)
        if icon:
            icon = '<span class="fa %s" title="%s"></span>' % (icon, value_display)
        if not self.only_icon:
            if icon:
                return '<span class="%s">%s %s</span>' % (style, icon, value_display)
            else:
                return '<span class="%s">%s</span>' % (style, value_display)
        else:
            return '<span class="%s">%s</span>' % (style, icon)


class ManyToManyColumn(Column):
    style = 'object'
    inner_field = None
    safe = True

    def get_value(self, item):
        field = self.field or self.name
        if not field:
            return
        value = get_attribute(item, field, call=False)
        if self.inner_field:
            return '<br/>'.join([escape(smart_text(getattr(i, self.inner_field))) for i in value.all()])
        return '<br/>'.join([escape(smart_text(i)) for i in value.all()])


class MultiColumn(Column):
    style = 'text'
    fields = []

    def get_value(self, item):
        if not self.fields:
            return ''
        result = [smart_text(get_attribute(item, f)) for f in self.fields]
        return ', '.join([r for r in result if r])


class DateTimeColumn(Column):
    style = 'datetime'
    format = None
    short = False
    safe = True

    def display(self, item):
        value = self.get_value(item)
        if value:
            date_format = 'DATE_FORMAT'
            if self.format:
                date_format = self.format
            elif isinstance(value, datetime.datetime):
                date_format = 'DATETIME_FORMAT'
            elif isinstance(value, datetime.date):
                date_format = 'DATE_FORMAT'
            if self.short:
                return '<span title="%s">%s</span>' % (formats.date_format(value, date_format, use_l10n=True),
                                                       formats.date_format(value, 'DATE_FORMAT', use_l10n=True))
            else:
                return formats.date_format(value, date_format, use_l10n=True)
        return ''


class TimeColumn(Column):
    style = 'time'
    format = None

    def display(self, item):
        value = self.get_value(item)
        if value:
            if self.format:
                time_format = self.format
            else:
                time_format = 'TIME_FORMAT'
            return formats.time_format(value, time_format, use_l10n=True)
        return ''


class BoolColumn(Column):
    style = 'bool'
    safe = True
    short_header = True
    icons = None

    def display(self, item):
        value = self.get_value(item)
        if value is None:
            return ''
        return admin_bool_icon(value, icons=self.icons, title=self.get_tooltip_value(item))


class ChangerColumn(Column):
    style = 'bool'
    short_header = True
    safe = True
    confirm = False
    icons = None
    enable = True

    def get_enable(self, item):
        return True

    def display(self, item):
        if self.get_enable(item):
            return _admin_item_change(item, self.name, title=self.get_tooltip_value(item), icons=self.icons,
                                      confirm=self.confirm, user=self.view.request.user)
        value = self.get_value(item)
        return admin_bool_icon(value, icons=self.icons, title=self.get_tooltip_value(item))


class TextColumn(Column):
    style = 'text'
    sort = False
    trim = None
    strip_tags = False

    def display(self, item):
        value = self.get_value(item)
        if self.strip_tags:
            value = strip_tags(value).replace('&nbsp;', ' ').replace('<', '').replace('>', '').strip()
        if self.trim:
            value = value[:self.trim]
        return value


class UrlColumn(TipMixin, Column):
    safe = True
    short_header = False
    icon = ''
    popup = True
    text = ''
    args = ['pk']
    url = None
    confirm = False
    target = None
    non_empty = False
    popup_reload = False
    id = None

    def get_url(self, item):
        if hasattr(self.url, '__call__'):
            return self.url(item)
        args = []
        if not self.url:
            return
        if '/' in self.url:
            return self.url
        for arg in self.args:
            a = get_attribute(item, arg)
            if a is None:
                return ''
            args.append(a)
        return reverse(self.url, args=args)

    def get_title(self, item):
        if self.tooltip:
            if callable(self.tooltip):
                return self.tooltip(item)
            else:
                return self.tooltip
        return smart_text(self.verbose_name)

    def display(self, item):
        attrs = dict()
        attrs['title'] = self.get_title(item)
        attrs['class'] = self.get_style(item) or ''
        if self.id is not None:
            attrs['id'] = self.id
        if self.icon:
            if ',' in self.icon:
                value = '<span class="fa %s"></span>' % self.icon.split(',')[to_int(self.get_value(item))]
            else:
                value = '<span class="fa %s"></span>' % self.icon
        elif self.text:
            value = self.text
        else:
            value = self.get_value(item)
            if isinstance(value, str):
                value = strip_tags(value).replace('<', '').replace('>', '')
            if isinstance(value, datetime.datetime) or isinstance(value, datetime.date):
                value = date(value)
            if value is None:
                value = ''
            if self.non_empty and value == '':
                value = _('None')
            value = force_str(value)
        attrs['href'] = self.get_url(item)
        tip_url = self.get_tip_url(item)
        if tip_url:
            attrs['class'] += ' tip'
            attrs['data-url'] = tip_url
        if self.popup:
            attrs['class'] += ' popup'
        if self.popup_reload:
            attrs['class'] += ' popup-reload'
        if self.confirm:
            attrs['onclick'] = 'return confirm(\'%s\')' % escapejs(self.confirm)
        if self.target:
            attrs['target'] = '_blank'
        return '<a %s>%s</a>' % (' '.join('%s="%s"' % (k, smart_text(v).strip()) for k, v in attrs.items() if v), value)


class EditColumn(UrlColumn):
    style = 'edit'
    safe = True
    popup = True
    icon = ''

    def get_url(self, item):
        return self.view.get_edit_url(item)

    def get_value(self, item):
        value = super(EditColumn, self).get_value(item)
        if value:
            return value
        else:
            return '#%s' % item.pk


class ImageColumn(Column):
    style = 'image'
    safe = True
    size = '32x32'
    short_header = True
    preview = True
    sub_field = None

    def display(self, item):
        result = []
        values = self.get_value(item)
        if hasattr(values, 'all'):
            values = values.all()
        else:
            values = [values]
        for value in values:
            if self.sub_field:
                value = force_str(getattr(value, self.sub_field))
            else:
                value = force_str(value)
            path = os.path.join(settings.MEDIA_ROOT, smart_text(value)).replace('\\', '/')
            exists = True
            if not os.path.exists(path) or not value:
                result.append('<img src="%s" alt="" />' % thumbnail('no.png', self.size))
                continue
            thumb = thumbnail(value, self.size)
            image_url = '%s%s' % (settings.MEDIA_URL, value)
            if not self.preview or not exists:
                result.append('<img src="%s" alt="" />' % thumb)
            else:
                result.append('<a href="%s" class="image-box thumbnail" title="%s"><img src="%s" alt="" /></a>' %
                              (image_url, self.verbose_name, thumb))
        return ''.join(result)


class SeparatorColumn(Column):
    style = 'separator'
    icon = ''
    text = ''
    safe = True

    def display(self, item):
        if self.icon:
            return '<span class="%s">%s</span>' % (self.icon, self.text)
        return self.text or ''


class TranslateColumn(Column):
    safe = True

    def display(self, item):
        if len(settings.LANGUAGES) < 2:
            return super(TranslateColumn, self).display(item)
        values = []
        field = self.field or self.name
        for code, name in settings.LANGUAGES:
            value = get_attribute(item, '%s_%s' % (field, code))
            if value:
                value = escape(value)
            else:
                value = '&mdash;'
            values.append('<strong><code>%s</code></strong> %s' % (code.upper(), value))
        return '<br/>'.join(values)


class LocationColumn(Column):
    safe = True
    verbose_name = _('Location')
    short_header = True
    latitude = 'latitude'
    longitude = 'longitude'
    target = '_blank'
    icon = 'fa fa-map-marker'
    text = ''
    url = 'http://maps.google.com/maps?ll=%(latitude)s,%(longitude)s&spn=0.1,0.1&q=%(latitude)s,%(longitude)s'

    def display(self, item):
        latitude = getattr(item, self.latitude, None)
        longitude = getattr(item, self.longitude, None)
        if latitude is None or longitude is None:
            return ''
        if self.target:
            target = ' target="%s"' % self.target
        else:
            target = ''
        if self.icon:
            icon = '<span class="%s"></span>' % self.icon
        else:
            icon = ''
        url = self.url % {'longitude': longitude, 'latitude': latitude}
        return '<a href="%s" title="%s;%s"%s>%s%s</a>' % (url, longitude, latitude, target, icon, self.text)
