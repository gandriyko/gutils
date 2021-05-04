# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404
from django.apps import apps
from django.urls import reverse
from django.utils.encoding import smart_text
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import View, TemplateView
from django.views.generic.edit import FormView
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext_lazy as _
from django.db.models import ProtectedError
from gutils.files import upload_file
from gutils.querysets import get_realated_items
from gutils.shortcuts import get_referer, response_json, close_view
from gutils.admin.forms import ImageForm, FileImportForm
from gutils import to_int
from gutils.images import save_image, delete_image
from gutils.views import PermissionMixin, AdminFormView
from gutils.strings import get_slug
from gutils.signals import post_delete, post_change
from gutils.reader import Reader
import datetime
import random
import shutil
import logging
import glob
import os
import re


logger = logging.getLogger(__name__)


class ItemChangeView(PermissionMixin, View):

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ItemChangeView, self).dispatch(*args, **kwargs)

    def get_perms(self):
        model_path = self.kwargs['model_path']
        app_label, model_name = model_path.split('.')
        model = apps.get_model(app_label=app_label, model_name=model_name)
        if hasattr(model, 'EDIT_PERMISSIONS'):
            return model.EDIT_PERMISSIONS
        return ['%s.%s_%s' % (app_label, 'edit', model_name)]

    def post(self, request, *args, **kwargs):
        model_path = kwargs['model_path']
        app_label, model_name = model_path.split('.')
        self.model = apps.get_model(app_label=app_label, model_name=model_name)
        obj = get_object_or_404(self.model, pk=kwargs['pk'])
        field = kwargs['field']
        value = not getattr(obj, field)
        func = getattr(obj, 'change_%s' % field, None)
        try:
            if func:
                value = func(request.user)
            else:
                setattr(obj, field, value)
                obj.save()
            post_change.send(obj.__class__, request=self.request, instance=obj)
        except Exception as e:
            return response_json({'id': obj.pk, 'value': to_int(value), 'error': smart_text(e)})
        return response_json({'id': obj.pk, 'value': to_int(value)})


class ItemDeleteView(PermissionMixin, TemplateView):
    template_name = 'gutils/item_delete.html'
    admin_login_url = False

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ItemDeleteView, self).dispatch(*args, **kwargs)

    def get_object(self):
        app_label, model_name = self.kwargs['model_path'].split('.')
        self.model = apps.get_model(app_label=app_label, model_name=model_name)
        self.object = get_object_or_404(self.model, pk=self.kwargs['pk'])
        return self.object

    def get_perms(self):
        app_label, model_name = self.kwargs['model_path'].split('.')
        Model = apps.get_model(app_label=app_label, model_name=model_name)
        if hasattr(Model, 'DELETE_PERMISSIONS'):
            return Model.DELETE_PERMISSIONS
        return ['%s.%s_%s' % (app_label, 'delete', model_name)]

    def get(self, request, *args, **kwargs):
        self.get_object()
        items = get_realated_items(self.object)
        return self.render_to_response(self.get_context_data(object=self.object,
                                                             items=items, next=get_referer(self.request)))

    def post(self, request, *args, **kwargs):
        self.get_object()
        timeout = 0
        try:
            post_delete.send(self.object.__class__, request=self.request, instance=self.object)
            self.object.delete()
            messages.info(request, _('Item "%s" deleted.') % smart_text(self.object))
        except ProtectedError as e:
            messages.error(request, _('Impossible delete "%s". This element depended others.') % self.object)
            messages.error(request, repr(e))
            timeout = 60 * 1000
        return close_view(self.request, next=self.request.POST.get('next') or '/admin', timeout=timeout)
        # return redirect()


class AdminFileImportView(AdminFormView):
    success_url = ''
    form1_class = FileImportForm
    form_class = None
    prefix1 = ''
    initial1 = {}
    enctype = 'multipart/form-data'
    destination = None
    title = _('Import')
    submit_text = _('Upload')
    template_name = 'gutils/item_edit_preview.html'

    def generate_name(self, form):
        return '%s' % random.randint(1, 99999)

    def check_file(self):
        f = self.request.GET.get('file')
        if not self.destination:
            raise Exception('destination not set for AdminFileImportView')
        if f:
            filename = os.path.join(self.destination, os.path.basename(f))
            if os.path.exists(filename):
                self.filename = filename
                return self.filename
        self.filename = None

    def get_context_data(self, *args, **kwargs):
        context = super(AdminFileImportView, self).get_context_data(*args, **kwargs)
        self.check_file()
        if self.filename:
            context['preview'] = Reader(self.filename).preview()
        return context

    def get_prefix1(self):
        return self.prefix1

    def get_form1_kwargs(self):
        kwargs = {
            'initial': self.get_initial1(),
            'prefix': self.get_prefix1(),
        }
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def get_form1(self, form_class=None):
        return self.form1_class(**self.get_form1_kwargs())

    def get_initial1(self):
        return self.initial1.copy()

    def get(self, request, *args, **kwargs):
        if self.model or self.queryset:
            self.object = self.get_object()
            response = self.check_object()
            if response:
                return response
        else:
            self.object = None
        self.check_file()
        if self.filename:
            form = self.get_form()
            return self.render_to_response(self.get_context_data(form=form))
        form1 = self.get_form1()
        return self.render_to_response(self.get_context_data(form=form1))

    def post(self, request, *args, **kwargs):
        if self.model or self.queryset:
            self.object = self.get_object()
            response = self.check_object()
            if response:
                return response
        else:
            self.object = None
        self.check_file()
        if self.filename:
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            return self.form_invalid(form)
        form1 = self.form1_class(request.POST, request.FILES)
        if form1.is_valid():
            return self.form1_valid(form1)
        return self.form1_invalid(form1)

    def form1_valid(self, form1):
        file = form1.cleaned_data.get('file')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in settings.SHOP_ALLOWED_FORMATS:
                messages.error(self.request, _('Wrong file format.'))
                return self.render_to_response(self.get_context_data(form=form1))
            res = upload_file(file, self.destination, self.generate_name(form1))
            if not res:
                messages.error(self.request, _('Error on uploading file.'))
                return self.render_to_response(self.get_context_data(form=form1))
            self.filename = res
            url = self.request.get_full_path()
            if '?' in url:
                url = '%s&file=%s' % (url, os.path.basename(self.filename))
            else:
                url = '%s?file=%s' % (url, os.path.basename(self.filename))
            return redirect(url)
        return self.render_to_response(self.get_context_data(form=form1))

    def form1_invalid(self, form1):
        return self.render_to_response(self.get_context_data(form=form1))


class ImageListView(PermissionMixin, TemplateView):
    template_name = 'gutils/image_list.html'
    path = ''
    image_path = ''
    folder = ''
    folders = []

    def dispatch(self, request, *args, **kwargs):
        self.path = os.path.join(settings.MEDIA_ROOT, settings.IMAGES_PREFIX)
        self.image_path = settings.IMAGES_PREFIX
        self.folders = [f for f in os.listdir(self.path) if os.path.isdir(os.path.join(self.path, f))]
        self.folder = self.request.GET.get('folder', '')
        if self.folder:
            if self.folder not in self.folders:
                raise Http404
            self.path = os.path.join(self.path, self.folder)
            self.image_path = '%s/%s' % (self.image_path, self.folder)
        self.path = self.path.replace('\\', '/')
        return super(ImageListView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        images = []
        for i in glob.glob('%s/*.*' % self.path):
            date = os.stat(i).st_mtime
            name = os.path.basename(i)
            images.append({'name': name,
                           'url': '%s/%s' % (self.image_path, name),
                           'date': date})
        images = sorted(images, key=lambda x: -x['date'])
        kwargs.update({'images': images, 'images_url': self.image_path, 'folders': self.folders, 'folder': self.folder})
        if 'form' not in kwargs:
            kwargs['form'] = ImageForm()
        return super(ImageListView, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if request.FILES.get('image'):
            form = ImageForm(request.POST, request.FILES)
            if form.is_valid():
                image = form.cleaned_data['image']
                if form.cleaned_data['naming'] == 'original':
                    name = str(image)
                else:
                    name = None
                save_image(image, folder=self.image_path, name=name)
            else:
                context = self.get_context_data(**kwargs)
                return self.render_to_response(context)
        if request.POST.get('delete_image'):
            image = request.POST.get('delete_image')
            image = os.path.basename(image)
            if image:
                delete_image(os.path.join(self.image_path, image))
        if request.POST.get('delete_folder') and self.folder:
            if os.path.exists(self.path):
                shutil.rmtree(self.path)
                self.folder = ''
        new_folder = get_slug(request.POST.get('create_folder', ''))
        if new_folder:
            path = os.path.join(settings.MEDIA_ROOT, settings.IMAGES_PREFIX, new_folder)
            if not os.path.exists(path):
                current_mask = os.umask(0000)
                os.makedirs(path)
                os.umask(current_mask)
            self.folder = new_folder
        if self.folder:
            return redirect('%s?folder=%s' % (reverse('admin-image-list'), self.folder))
        return redirect('admin-image-list')
