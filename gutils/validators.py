from django import forms
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _
from django.core.mail import mail_admins
from django.conf import settings
from gutils.strings import clean_phone
import datetime
import re
import os


def validate_unique_field(form, Model, model, field_name):
    '''Check a single 'unique' or 'unique_together' constraint'''
    filter = {}
    field_name = str(field_name)
    # search for other objects with the same data for the unique fields
    if field_name not in form.cleaned_data:
        return
    if not form.cleaned_data[field_name]:
        return
    filter[field_name] = form.cleaned_data[field_name]
    query_set = Model.objects.filter(**filter)
    # exclude model instance
    if model is not None:
        query_set = query_set.exclude(id=model.id)
    # raise ValidationError if query gives a result
    if query_set.count() > 0:
        raise forms.ValidationError(_('Field "%s" must be unique.') % Model._meta.get_field(field_name).verbose_name)


def validate_name(name, min_length=0):
    name = re.sub(r'\s+', ' ', name).strip()
    if len(name) < min_length:
        raise forms.ValidationError(_('This field is too short'))
    if re.search(r'[^\w\-]', force_text(name), re.U):
        raise forms.ValidationError(_('This field must contain only letters'))
    return name


def validate_phone(phone):
    phone = clean_phone(phone)
    if len(phone) != 12:
        raise forms.ValidationError(_('Incorrect phone'))
    if settings.GUTILS_ALLOWED_PHONES and int(phone[0:5]) not in settings.GUTILS_ALLOWED_PHONES:
        raise forms.ValidationError(_('Only numbers of Ukrainian operators are allowed'))
    return phone


def validate_birthday(birthday):
    if not birthday:
        return
    today = datetime.date.today()
    if birthday < today - datetime.timedelta(days=100 * 365) or \
            birthday > today - datetime.timedelta(days=16 * 365):
        raise forms.ValidationError(_('Enter correct date of birth, or leave blank'))
    return birthday


def validate_email(email):
    import dns.resolver
    import dns.exception
    if not email or '@' not in email:
        return False
    domain = email.split('@')[1]
    try:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 5
        resolver.timeout = 5
        resolver.query(domain, 'MX')
        return True
    except dns.exception.DNSException:
        if not settings.DEBUG:
            mail_admins('EMAIL ERROR in %s' % settings.DOMAIN, 'Not valid email: %s' % email)
        return False


def validate_image(value):
    if not value:
        return
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.gif', '.png'):
        raise forms.ValidationError(_('Upload correct image'))
