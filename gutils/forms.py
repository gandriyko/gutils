# -*- coding: utf-8 -*-

from django import forms
from django.utils import formats
from django.conf import settings
from django.db.models import Q
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.encoding import force_str
from django.utils.html import strip_tags
from datetime import datetime
from modeltranslation.translator import translator
from modeltranslation.translator import NotRegistered
from gutils import to_int, get_name
from gutils.dates import date_filter
from gutils import widgets
from gutils.strings import clean_number, clean_phone, clean_string
from gutils.validators import validate_phone
import re


def get_form_errors(form):
    if not form.errors:
        return []
    errors = [_('Make sure that all fields are filled in correctly.')]
    for key, error in form.errors.items():
        name = force_str(form.fields[key].label)
        error = error.as_text().replace('*', '')
        errors.append('%s:%s' % (name, error))
    return errors


class BaseForm(forms.BaseForm):
    required_css_class = 'required'
    error_css_class = 'error'

    def get_title(self):
        return self.__class__.__name__


class Form(forms.Form, forms.BaseForm):
    strip = True

    def clean(self):
        cleaned_data = super(Form, self).clean()
        for (key, value) in cleaned_data.items():
            if value and isinstance(value, str):
                if self.strip:
                    cleaned_data[key] = strip_tags(clean_string(value)).replace('<', '').replace('>', '')
                cleaned_data[key] = clean_string(cleaned_data[key])
        return cleaned_data


class ModelForm(forms.ModelForm, BaseForm):
    strip = True

    def get_title(self):
        try:
            model = get_name(self.__class__._meta.model)
        except AttributeError:
            model = _('Item')
        if self.instance.pk:
            return _('Edit %(model)s "%(name)s"') % {'model': model, 'name': self.instance}
        else:
            return _('New %s') % model

    def clean(self):
        cleaned_data = super(ModelForm, self).clean()
        for (key, value) in cleaned_data.items():
            if value and isinstance(value, str):
                if self.strip:
                    cleaned_data[key] = strip_tags(value).replace('<', '').replace('>', '')
                cleaned_data[key] = clean_string(cleaned_data[key])
        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.base_fields['next'] = forms.CharField(required=False, widget=forms.HiddenInput)
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        if 'modeltranslation' in settings.INSTALLED_APPS and self._meta.model in translator._registry:
            try:
                options = translator.get_options_for_model(self._meta.model)
                for f in self._meta.model._meta.fields:
                    if options and f.name in options.fields and f.name in self.fields:
                        del self.fields[f.name]
            except NotRegistered:
                pass


class FilterForm(forms.Form, BaseForm):
    rules = {}
    distinct = False

    def __init__(self, *args, **kwargs):
        if kwargs.get('data'):
            if not (set(kwargs['data'].dict().keys()) - set(['popup', 'page'])):
                del kwargs['data']
        super(FilterForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            field = self.fields.get(field_name)
            if field:
                # if type(field.widget) in (forms.TextInput, forms.DateInput):
                if field.label:
                    field.widget.attrs.update({'placeholder': field.label})

    def clean(self):
        cleaned_data = super(FilterForm, self).clean()
        for (key, value) in cleaned_data.items():
            if value and isinstance(value, str):
                value = clean_string(value)
                cleaned_data[key] = value.replace('+', ' ')
                cleaned_data[key] = value.replace('%2B', '+')
        return cleaned_data

    def is_empty(self, exclude=None):
        if exclude:
            exclude = exclude.split(',')
        else:
            exclude = []
        if not hasattr(self, 'cleaned_data'):
            return True
        for key, value in self.cleaned_data.items():
            if key not in exclude and value:
                return False
        return True

    def get_query(self):
        query = Q()
        for key in self.fields.keys():
            func = getattr(self, 'get_%s_query' % key, None)
            if func:
                q = func()
                if q:
                    query &= q
                continue
            rule = self.rules.get(key)
            if rule is False:
                continue
            if not rule:
                rule = key
            value = self.cleaned_data.get(key)
            if isinstance(value, str):
                value = value.strip()
            if value in (None, '', []):
                continue
            if isinstance(value, QuerySet) and not value:
                continue
            if rule.endswith('__important'):
                return Q(**{rule[:-11]: value})
            if rule.endswith('__daterange'):
                query &= date_filter(rule[:-11], value[0], value[1])
                continue
            if rule.startswith('~'):
                query &= ~Q(**{rule[1:]: value})
                continue
            if rule.endswith('__strip'):
                value = re.sub(r'(\W+)', '', value, flags=re.U)
                query &= Q(**{rule[:-7]: value})
                continue
            query &= Q(**{rule: value})
        return query


class DateField(forms.DateField):
    widget = widgets.DateInput

    def clean(self, value):
        if value:
            value = value.strip()
        return super(DateField, self).clean(value)


class DateTimeField(forms.DateTimeField):
    widget = widgets.DateTimeInput

    def clean(self, value):
        if value:
            value = value.strip()
        return super(DateTimeField, self).clean(value)


class DateRangeField(forms.DateField):
    widget = widgets.DateRangeInput

    def prepare_value(self, value):
        if isinstance(value, str):
            return value
        elif isinstance(value, list):
            if value[0]:
                a = formats.date_format(value[0], 'DATE_FORMAT', use_l10n=True)
            else:
                a = ''
            if value[1]:
                b = formats.date_format(value[1], 'DATE_FORMAT', use_l10n=True)
            else:
                b = ''
            s = formats.get_format('DATE_SEPARATOR')
            return '%s%s%s' % (a, s, b)

    def to_python(self, value):
        separator = formats.get_format('DATE_SEPARATOR')
        value = force_str(value, strings_only=True)
        if not value or value.count(separator) != 1:
            return
        try:
            date_from, date_to = value.strip().split(separator)
        except IndexError:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        for format in self.input_formats:
            try:
                return self.strptime(date_from, format) if date_from else None,\
                       self.strptime(date_to, format) if date_to else None
            except (ValueError, TypeError):
                continue
        raise ValidationError(self.error_messages['invalid'], code='invalid')


class PhoneField(forms.CharField):

    def clean(self, value):
        if value:
            value = clean_phone(value)
            validate_phone(value)
        return super(PhoneField, self).clean(value)


class NullBooleanField(forms.NullBooleanField):
    widget = widgets.NullBooleanSelect


class NullChoiceField(forms.ChoiceField):

    def __init__(self, choices=(), *args, **kwargs):
        if 'null_value' in kwargs.keys():
            null_value = kwargs['null_value']
            del kwargs['null_value']
        else:
            null_value = None
        if 'empty_value' in kwargs.keys():
            empty_value = kwargs['empty_value']
            del kwargs['empty_value']
        else:
            empty_value = '------'
        choices = list(choices)
        choices.insert(0, (null_value, empty_value))
        super(NullChoiceField, self).__init__(choices=choices, *args, **kwargs)

    def to_python(self, value):
        if value == '':
            return
        return value


class IntListField(forms.CharField):

    def to_python(self, value):
        if not value:
            return []
        result = []
        try:
            for s in value.split(','):
                v = int(s.strip())
                result.append(v)
        except Exception:
            raise ValidationError(_('Enter a number, or few separated by comma'))
        return result


class IdListField(IntListField):

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        if 'widget' not in kwargs.keys():
            kwargs['widget'] = forms.HiddenInput
        super(IdListField, self).__init__(*args, **kwargs)


class SplitDateTimeField(forms.fields.MultiValueField):
    widget = widgets.SplitDateTimeWidget

    def __init__(self, *args, **kwargs):
        all_fields = (
            forms.fields.CharField(max_length=10),
            forms.fields.CharField(max_length=2),
            forms.fields.CharField(max_length=2))
        super(SplitDateTimeField, self).__init__(all_fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            if not (data_list[0] and data_list[1] and data_list[2]):
                raise forms.ValidationError(_('Date or time is empty!'))
            try:
                input_value = '%s %s:%s' % (data_list[0], data_list[1], data_list[2])
                return datetime.strptime(input_value, '%d.%m.%Y %H:%M')
            except ValueError:
                raise forms.ValidationError(_('Enter the correct date and time'))
        return None


class DecimalField(forms.DecimalField):
    input_type = 'text'

    def __init__(self, max_value=None, min_value=None, *args, **kwargs):
        kwargs.setdefault('widget', forms.TextInput)
        super(DecimalField, self).__init__(*args, **kwargs)

    def prepare_value(self, value):
        if value is None or value == '':
            return ''
        if to_int(value) == value:
            try:
                return formats.number_format(value, decimal_pos=0)
            except ValueError:
                return value
        try:
            return formats.number_format(value)
        except ValueError:
            return value

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, str):
            value = value.replace(',', '.')
            # value = re.sub(r'[^\d\.\-]', '', value)
        try:
            value = super(DecimalField, self).to_python(value)
        except UnicodeEncodeError:
            raise ValidationError(self.error_messages['invalid'])
        return value


class NumberField(forms.CharField):

    def prepare_value(self, value):
        if value is None:
            return value
        return clean_number(value)

    def to_python(self, value):
        if value is None:
            return value
        return clean_number(value)


class FileField(forms.Field):
    widget = widgets.FileInput


class ImagesField(forms.fields.Field):
    widget = widgets.ImagesWidget

    def __init__(self, max_images=20, size='800x600', quality=50, button_text='', button_class='', *args, **kwargs):
        self.widget = widgets.ImagesWidget(max_images=max_images,
                                           size=size,
                                           quality=quality,
                                           button_text=button_text,
                                           button_class=button_class)
        super(ImagesField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if value[1]:
            raise forms.ValidationError(_('Incorrect file: %s') % ', '.join(value[1]))
        return value[0]
