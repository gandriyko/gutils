# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.text import capfirst
from gutils import forms
from gutils import widgets
from ajax_select.fields import AutoCompleteSelectField, AutoCompleteSelectMultipleField
from uuid import uuid4
import os


class DecimalField(models.DecimalField):

    def formfield(self, **kwargs):
        defaults = {
            'max_digits': self.max_digits,
            'decimal_places': self.decimal_places,
            'form_class': forms.DecimalField,
        }
        defaults.update(kwargs)
        return super(DecimalField, self).formfield(**defaults)


class DateField(models.DateField):

    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.DateField,
        }
        defaults.update(kwargs)
        return super(DateField, self).formfield(**defaults)


class DateTimeField(models.DateTimeField):

    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.DateTimeField,
        }
        defaults.update(kwargs)
        return super(DateTimeField, self).formfield(**defaults)


class TextField(models.TextField):

    def formfield(self, **kwargs):
        defaults = {'widget': widgets.Textarea}
        defaults.update(kwargs)
        return super(TextField, self).formfield(**defaults)


class PhoneField(models.CharField):

    description = _("Phone")

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 12)
        super(PhoneField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(PhoneField, self).deconstruct()
        # We do not exclude max_length if it matches default as we want to change
        # the default in future.
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        # As with CharField, this will cause email validation to be performed
        # twice.
        defaults = {
            'form_class': forms.PhoneField,
        }
        defaults.update(kwargs)
        return super(PhoneField, self).formfield(**defaults)


class ForeignKey(models.ForeignKey):

    def __init__(self, *args, **kwargs):
        self.channel = kwargs.get('channel')
        if not self.channel and args:
            self.channel = args[0]._meta.model_name
        if 'channel' in kwargs:
            del kwargs['channel']
        super(ForeignKey, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'channel': self.channel, 'required': not self.blank, 'label': capfirst(self.verbose_name)}
        # 'label': self.rel.to._meta.object_name
        defaults.update(kwargs)
        # defaults.update(help_text='')
        return AutoCompleteSelectField(**defaults)


class ManyToManyField(models.ManyToManyField):
    def __init__(self, *args, **kwargs):
        self.channel = kwargs.get('channel')
        if 'channel' in kwargs:
            del kwargs['channel']
        super(ManyToManyField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'channel': self.channel, 'required': not self.blank, 'label': capfirst(self.verbose_name)}
        defaults.update(kwargs)
        defaults.update(help_text='')
        return AutoCompleteSelectMultipleField(**defaults)


class ImageField(models.ImageField):
    def generate_filename(self, instance, filename):
        ext = filename.split('.')[-1]
        # get filename
        if instance.slug:
            _filename = '%s.%s' % (instance.slug, ext)
        else:
            _filename = '%s.%s' % (uuid4().hex, ext)
        return self.storage.generate_filename(os.path.join(self.upload_to, _filename))


class FixedCharField(models.CharField):

    def get_internal_type(self):
        return

    def db_type(self, connection):
        return 'char(%s)' % self.max_length


class UniqueBooleanField(models.BooleanField):
    def pre_save(self, model_instance, add):
        objects = model_instance.__class__.objects
        if getattr(model_instance, self.attname):
            objects.update(**{self.attname: False})
        elif not objects.exclude(pk=model_instance.pk).filter(**{self.attname: True}):
            return True
        return getattr(model_instance, self.attname)


class ChangedModel(models.Model):

    class Meta:
        abstract = True

    CHANGED_FIELDS = []

    def has_change(self, field):
        return True

    def __init__(self, *args, **kwargs):
        super(ChangedModel, self).__init__(*args, **kwargs)
        self.__original_values = {}
        for field in self.CHANGED_FIELDS:
            self.__original_values[field] = getattr(self, field, None)

    def save(self, *args, **kwargs):
        if not self.is_changed:
            for field in self.CHANGED_FIELDS:
                if self.__original_values[field] != getattr(self, field, None) and self.has_change(field):
                    self.is_changed = True
                    break

        super(ChangedModel, self).save(*args, **kwargs)
