from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
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


class ChangedModelMixin(object):

    CHANGED_FIELDS = []

    def has_change(self, field):
        return True

    def update_changed(self, old_instance):
        if old_instance and not self.is_changed:  # noqa
            for field in self.CHANGED_FIELDS:
                if getattr(self, field, None) != getattr(old_instance, field, None) and self.has_change(field):
                    self.is_changed = True
                    break


class AdminViewConfModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    url_name = models.CharField(max_length=64)
    selected_columns = models.CharField(max_length=2048, null=True)

    class Meta:
        db_table = 'admin_view_conf'
        unique_together = ('user', 'url_name')

    def get_selected_columns(self):
        if self.selected_columns:
            return self.selected_columns.split(',')
        else:
            return []

    @classmethod
    def get_user_selected_columns(cls, user, url_name):
        obj = cls.objects.filter(user=user, url_name=url_name).first()
        if obj:
            return obj.get_selected_columns()
        default_obj = cls.objects.filter(user__isnull=True, url_name=url_name).first()
        if default_obj:
            return default_obj.get_selected_columns()
        return []

    @classmethod
    def set_user_selected_columns(cls, user, url_name, columns):
        if columns:
            cls.objects.update_or_create(
                user=user,
                url_name=url_name,
                defaults={
                    'selected_columns': ','.join(columns) if columns else None
                }
            )
        else:
            cls.objects.filter(user=user, url_name=url_name).delete()
