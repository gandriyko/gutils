# -*- coding: utf-8 -*-
from django import forms
from gutils.forms import Form
from django.utils.translation import gettext_lazy as _


class ImageForm(Form):
    naming = forms.ChoiceField(choices=(('original', _('original name')), ('random', _('random name'))), required=False)
    image = forms.ImageField(label=_('image'))


class FileImportForm(Form):
    file = forms.FileField(label=_('Upload file'), required=True)
