from django.conf import settings
from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.forms.models import ModelForm as _ModelForm, BaseModelFormSet, modelform_factory
from django.core.paginator import InvalidPage
from django.template.loader import render_to_string
from django.urls import NoReverseMatch
from django.urls import reverse_lazy, reverse
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.views.generic import View, TemplateView, ListView, DetailView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormMixin, FormView
from django.views.i18n import JavaScriptCatalog as _JavaScriptCatalog
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import force_bytes
from django.contrib import messages
from django.shortcuts import redirect, resolve_url, get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
from django.utils import formats
from django.utils.html import escape
from django.http import Http404
from django.core.mail import mail_admins
from gutils.forms import ModelForm
from gutils.querysets import get_realated_items
from gutils import to_int, get_attribute, get_name
from gutils.strings import upper_first
from gutils.users import is_superuser, is_user
from gutils.shortcuts import get_referer, close_view
from gutils.columns import Column
from gutils.models import AdminViewConfModel
from gutils.signals import pre_init_view, post_init_view

import logging
import copy
import datetime
import time
import hashlib
import random
import pickle


logger = logging.getLogger(__name__)


class LoggedUserMixin(object):
    login_url = None

    def get_login_url(self):
        return resolve_url(self.login_url or settings.LOGIN_URL)

    def dispatch(self, request, *args, **kwargs):
        if not is_user(request.user):
            if request.is_ajax():
                raise PermissionDenied()
            return redirect('%s?next=%s' % (self.get_login_url(), request.get_full_path()))
        return super(LoggedUserMixin, self).dispatch(request, *args, **kwargs)


class DuplicateProtectionMixin(object):

    def post(self, request, *args, **kwargs):
        post = u','.join(['%s=%s' % (k, v) for k, v in request.POST.items() if k != 'csrfmiddlewaretoken'])
        key = 'USER:%s;GET:%s;POST:%s' % (getattr(request.user, 'pk', 0), request.get_full_path(), post)
        key = hashlib.md5(force_bytes(key)).hexdigest()
        response = cache.get(key)
        if response is not None:
            if response == '':
                secure_random = random.SystemRandom()
                time.sleep(secure_random.uniform(0.1, 0.6))
                if not settings.DEBUG:
                    mail_admins('duplication error', 'Path: %s' % request.get_full_path())
                return HttpResponse('Dublication error')
            return pickle.loads(force_bytes(response))
        cache.set(key, '', 2)
        response = super(DuplicateProtectionMixin, self).post(request, *args, **kwargs)
        if hasattr(response, 'render'):
            response.render()
        cache.set(key, pickle.dumps(response), 2)
        return response


class PermissionMixin(object):
    model = None
    perms = []
    queryset = None
    perm_prefix = 'view'
    admin_login_url = None

    def get_perms(self):
        model = None
        if self.perms is None:
            return
        if self.perms:
            if not isinstance(self.perms, (list, tuple)):
                self.perms = (self.perms, )
            return self.perms
        if self.model:
            model = self.model
        elif self.queryset is not None:
            model = self.queryset.model
        if model:
            if getattr(model, 'EDIT_PERMISSIONS', None):
                self.perms = model.EDIT_PERMISSIONS
            else:
                self.perms = ('%s.%s_%s' % (model._meta.app_label, self.perm_prefix, model._meta.model_name), )
        return self.perms

    def get_admin_login_url(self):
        if self.admin_login_url is False:
            return False
        return resolve_url(self.admin_login_url or getattr(settings, 'ADMIN_LOGIN_URL', '') or settings.LOGIN_URL)

    def check_perms(self):
        perms = self.get_perms()
        if is_superuser(self.request.user):
            return True
        elif is_user(self.request.user):
            return self.request.user.has_perms(perms)
        else:
            # logger.debug('User "%s" hasn\'t has permisssions "%s"' % (request.user, perms))
            return False

    def dispatch(self, request, *args, **kwargs):
        if not self.check_perms():
            if request.is_ajax():
                raise PermissionDenied()
            url = self.get_admin_login_url()
            if url is False:
                raise PermissionDenied()
            return redirect('%s?next=%s' % (self.get_admin_login_url(), request.get_full_path()))
        return super(PermissionMixin, self).dispatch(request, *args, **kwargs)


class TitleMixin(object):
    title = ''

    def get_title(self):
        if self.title:
            return self.title
        try:
            return get_name(self.model)
        except AttributeError:
            return ''

    def get_context_data(self, **kwargs):
        kwargs.update({'title': self.get_title()})
        return super(TitleMixin, self).get_context_data(**kwargs)


class ListLinkMixin(object):
    list_link = []

    def get_list_link(self):
        return self.list_link


class EditFormMixin(TitleMixin, ListLinkMixin):
    form_details = []
    formset_title = ''
    success_url = None

    def get_title(self):
        if self.title:
            return self.title
        if self.object:
            return _('Editing "%s"') % self.object
        else:
            try:
                model_name = get_name(self.model)
            except AttributeError:
                model_name = _('Item')
            return _('Creating "%(model_name)s"') % {'model_name': model_name}

    def get_formset_title(self):
        return self.formset_title

    def get_success_url(self):
        if hasattr(self, 'form') and self.form.cleaned_data.get('next'):
            return self.form.cleaned_data.get('next')
        if self.success_url:
            return self.success_url
        return reverse_lazy('admin-%s-list' % self.model._meta.model_name)

    def get_form_details(self):
        if not self.form_details or not self.object:
            return []
        result = []
        for detail in self.form_details:
            if isinstance(detail, (list, tuple)):
                name = detail[0]
                value = get_attribute(self.object, detail[1])
            else:
                value = get_attribute(self.object, detail)
                if isinstance(value, datetime.datetime):
                    value = formats.date_format(value, 'DATETIME_FORMAT', use_l10n=True)
                elif isinstance(value, datetime.date):
                    value = formats.date_format(value, 'DATE_FORMAT', use_l10n=True)
                elif isinstance(value, bool):
                    value = _('Yes') if value else _('No')
                try:
                    name = upper_first(self.object.__class__._meta.get_field(detail).verbose_name)
                except FieldDoesNotExist:
                    name = detail
            result.append((name, value))
        return result


class ItemFormView(TitleMixin, UpdateView):
    model = None
    queryset = None
    perms = []
    form_class = None
    template_name = 'gutils/item_edit.html'

    def __init__(self, *args, **kwargs):
        super(ItemFormView, self).__init__(*args, **kwargs)
        self.is_editing = False

    def get_queryset(self):
        queryset = None
        if self.model or self.queryset:
            queryset = super(ItemFormView, self).get_queryset()
            if self.is_editing:
                queryset = queryset.select_for_update()
        return queryset

    def get_object(self):
        if not to_int(self.kwargs.get(self.pk_url_kwarg)) and not self.kwargs.get(self.slug_url_kwarg):
            return
        return super(ItemFormView, self).get_object()

    def get_initial(self):
        initial = super(ItemFormView, self).get_initial().copy()
        initial['next'] = get_referer(self.request, default_url=settings.GUTILS_ADMIN_INDEX)
        return initial

    def check_object(self):
        return

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()
        if not issubclass(form_class, _ModelForm) and 'instance' in kwargs:
            del kwargs['instance']
        return form_class(**kwargs)

    def get(self, request, *args, **kwargs):
        self.is_editing = False
        if self.model or self.queryset:
            self.object = self.get_object()
            response = self.check_object()
            if response:
                return response
        else:
            self.object = None
        form = self.get_form(self.get_form_class())
        return self.render_to_response(self.get_context_data(form=form))

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.is_editing = True
        if self.model or self.queryset:
            self.object = self.get_object()
            response = self.check_object()
            if response:
                return response
        else:
            self.object = None
        self.form = self.get_form(self.get_form_class())
        if self.form.is_valid():
            return self.form_valid(self.form)
        else:
            return self.form_invalid(self.form)

    def form_save(self, form):
        pass

    def form_valid(self, form):
        self.form_save(form)
        return close_view(self.request, next=self.get_success_url(), popup=self.request.is_popup)


class ItemListView(TitleMixin, FormMixin, ListView):
    # context_object_name = 'items'
    paginate_by = 30
    parent_model = None
    parent_queryset = None
    parent_slug = 'slug'
    parent_pk = 'slug'
    parent_object = None
    parent_lookup = None
    title = None
    select_related = None
    prefetch_related = None
    ordering = None
    default_sort = None
    sort = None
    sort_list = None
    empty_query = False

    def get(self, request, *args, **kwargs):
        # My View
        self.parent_queryset = self.get_parent_queryset()
        if self.parent_queryset is not None:
            if not self.parent_model:
                self.parent_model = self.parent_queryset.model
            try:
                self.parent_object = self.parent_queryset.get(**{self.parent_pk: self.kwargs.get(self.parent_slug)})
            except self.parent_queryset.model.DoesNotExist:
                raise Http404
        # From ProcessFormMixin
        form_class = self.get_form_class()
        if form_class:
            self.form = self.get_form(form_class)
        else:
            self.form = None
        # From BaseListView
        self.object_list = self.get_queryset()
        context = self.get_context_data(object_list=self.object_list, form=self.form)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
        }
        keys = self.request.GET.keys()
        not_form_keys = ['page', 'sort']
        if keys and set(keys) - set(not_form_keys):
            kwargs.update({'data': self.request.GET})
        return kwargs

    def get_default_sort(self):
        return self.default_sort

    def get_parent_queryset(self):
        if self.parent_model is not None:
            return self.parent_model.objects.all()
        if self.parent_queryset is not None:
            return self.parent_queryset

    def get_queryset(self):
        queryset = None
        if self.queryset is not None:
            queryset = self.queryset.all()
        elif self.model:
            queryset = self.model.objects.all()
        if self.parent_object:
            if not self.parent_lookup:
                self.parent_lookup = self.parent_queryset.model._meta.model_name
            queryset = queryset.filter(**{self.parent_lookup: self.parent_object})
        if self.form:
            if self.form.is_valid():
                q = self.form.get_query()
                if q is None:
                    queryset = queryset.none()
                else:
                    queryset = queryset.filter(q)
            else:
                if self.form.errors:
                    return queryset.model.objects.none()
                if self.empty_query:
                    return queryset.model.objects.none()
        if self.select_related:
            if isinstance(self.select_related, str):
                queryset = queryset.select_related(self.select_related)
            elif hasattr(self.select_related, '__iter__'):
                queryset = queryset.select_related(*self.select_related)
            else:
                queryset = queryset.select_related()
        if self.prefetch_related:
            if isinstance(self.prefetch_related, str):
                queryset = queryset.prefetch_related(self.prefetch_related)
            elif hasattr(self.prefetch_related, '__iter__'):
                queryset = queryset.prefetch_related(*self.prefetch_related)
            else:
                queryset = queryset.prefetch_related()

        self.sort = None
        ordering = self.ordering or []
        sort = self.request.GET.get('sort', self.get_default_sort())
        if sort and self.sort_list:
            if sort.startswith('-'):
                _sort = sort[1:]
            else:
                _sort = sort
            for s in self.sort_list:
                if s[0] == _sort:
                    ordering = [sort] + ordering
                    self.sort = sort
                    break
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset

    def get_context_data(self, **kwargs):
        context = super(ItemListView, self).get_context_data(**kwargs)
        context['parent_object'] = self.parent_object
        context['form'] = self.form
        return context

    def get_template_names(self):
        if self.template_name:
            return [self.template_name]
        return ['%s/%s_list.html' % (getattr(settings, 'GUTILS_TEMPLATE_PREFIX', 'gutils'), self.object_list.model._meta.model_name.lower())]


class ItemDetailView(FormMixin, DetailView):
    model = None
    form_class = None

    def get_template_names(self):
        if self.template_name:
            return [self.template_name]
        return ['%s%s_detail.html' % (getattr(settings, 'GUTILS_TEMPLATE_PREFIX', 'gutils'), self.object._meta.model_name.lower())]

    def get_form_kwargs(self):
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
        }
        if self.request.method in ('GET',):
            kwargs.update({'data': self.request.GET})
        return kwargs

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        if form_class:
            return form_class(**self.get_form_kwargs())

    def check_object(self):
        return

    def get(self, request, *args, **kwargs):
        #  Process FormMixin
        form_class = self.get_form_class()
        if form_class:
            self.form = self.get_form(form_class)
        else:
            self.form = None
        # Process DetailView
        self.object = self.get_object()
        response = self.check_object()
        if response:
            return response
        context = self.get_context_data(object=self.object, form=self.form)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class ItemActionView(SingleObjectMixin, View):
    url = None
    pattern_name = None

    def check_object(self):
        return

    def get_queryset(self):
        return super(ItemActionView, self).get_queryset().select_for_update()

    @transaction.atomic
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        response = self.check_object()
        if response:
            return response
        response = self.action()
        if response:
            return response
        url = self.get_redirect_url(*args, **kwargs)
        return HttpResponseRedirect(url)

    def get_redirect_url(self, *args, **kwargs):
        if self.url:
            url = self.url % kwargs
        elif self.pattern_name:
            try:
                url = reverse(self.pattern_name, args=args, kwargs=kwargs)
            except NoReverseMatch:
                return None
        else:
            return get_referer(self.request)
        args = self.request.META.get('QUERY_STRING', '')
        if args and self.query_string:
            url = "%s?%s" % (url, args)
        return url

    def action(self):
        pass

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class FormProcessView(TitleMixin, FormView):

    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if (request.GET or request.POST):
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
        }
        if self.request.POST:
            kwargs.update({'data': self.request.POST})
        elif self.request.GET:
            kwargs.update({'data': self.request.GET})
        return kwargs


class AdminListView(PermissionMixin, TitleMixin, ListLinkMixin, FormMixin, ListView):
    # context_object_name = 'items'
    css = None
    js = None
    perm_prefix = 'view'
    perm_delete_prefix = 'edit'
    list_action = []
    paginate_by = getattr(settings, 'GUTILS_ITEMS_PER_PAGE', 50)
    detail_url = None
    edit_url = None
    create_url = None
    # form_class = None
    # model = None
    template_name = 'gutils/item_list.html'
    allow_delete = True
    delete_link = True
    sort = None
    default_sort = None
    have_checkbox = False
    select_related = None
    distinct = None
    prefetch_related = None
    save_query = False
    empty_query = False
    column_list = []
    columns = {}
    table_class = None
    excluded_column_list = None
    allow_select_columns = True
    tabs = None
    parent_model = None
    parent_queryset = None
    parent_slug = 'pk'
    parent_pk = 'pk'
    parent_object = None
    parent_lookup = None
    form = None
    form_classes = None
    edit_form_class = None

    details = {}

    def __init__(self, *args, **kwargs):
        pre_init_view.send(sender=self.__class__, instance=self)
        super(AdminListView, self).__init__(*args, **kwargs)
        column_list = []
        if not self.model:
            self.model = self.queryset.model

        _columns = self.get_columns()  # add by columns property get_columns
        if not _columns:
            if hasattr(self, 'Columns'):
                _columns = self.Columns.__dict__  # add columns by Columns subclass
            elif self.table_class:
                table = self.table_class(self)
                _columns = table.get_columns()  # add columns by table_class

        self.update_columns()

        excluded_column_list = self.get_excluded_column_list()
        self_columns = {}

        for key, value in _columns.items():
            if isinstance(value, Column) and key not in excluded_column_list:
                column = copy.deepcopy(value)
                column.init(self, key)
                column_list.append(column)
                self_columns[key] = column
        self.columns = self_columns

        self.column_list = sorted(column_list, key=lambda c: c.index)
        post_init_view.send(sender=self.__class__, instance=self)

    def update_columns(self):
        pass

    def get_columns(self):
        return self.columns

    def get_column_list(self):
        selected_column_list = self.get_selected_column_list()
        if selected_column_list:
            return [c for c in self.column_list if c.name in selected_column_list]
        else:
            return self.column_list

    def get_excluded_column_list(self):
        return self.excluded_column_list or []

    def get_selected_column_list(self):
        if self.allow_select_columns:
            return AdminViewConfModel.get_user_selected_columns(self.request.user,
                                                                self.request.url_name)
        return []

    def add_column(self, name, column, after=None, before=None):
        column = copy.deepcopy(column)
        column.init(self, name)
        self.columns[name] = column
        if after:
            index = self.column_list.index(self.columns[after])
            self.column_list.insert(index + 1, column)
        elif before:
            index = self.column_list.index(self.columns[before])
            self.column_list.insert(index, column)
        else:
            self.column_list.append(column)

    def replace_column(self, name, column, new_name=None):
        column = copy.deepcopy(column)
        column.init(self, name)
        index = self.column_list.index(self.columns[name])
        self.column_list[index] = column
        if new_name:
            self.columns[new_name] = column
            del self.columns[name]
        else:
            self.columns[name] = column

    def delete_column(self, name):
        self.column_list.remove(self.columns[name])
        del self.columns[name]

    def get_model_name(self):
        try:
            return get_name(self.model, plural=True)
        except AttributeError:
            return _('Items')

    def get_title(self):
        return self.title or self.get_model_name()

    def get_detail_url(self, item):
        if not self.detail_url:
            self.detail_url = 'admin-%s-detail' % self.model._meta.model_name
        return reverse(self.detail_url, args=[item.pk])

    def get_edit_url(self, item):
        if not self.edit_url:
            self.edit_url = 'admin-%s-edit' % self.model._meta.model_name
        return reverse(self.edit_url, args=[item.pk])

    def get_create_url(self):
        if self.create_url:
            return reverse(self.create_url, args=[0])
        elif self.create_url is None:
            return reverse('admin-%s-edit' % self.model._meta.model_name, args=[0])

    def get_default_sort(self):
        return self.default_sort

    @cached_property
    def sort_list(self):
        result = []
        for c in self.column_list:
            result.append(c.sort)
        return result

    def get_list_action(self):
        return self.list_action or []

    def can_delete(self):
        if not self.allow_delete:
            return False
        perms = getattr(self.model, 'DELETE_PERMISSIONS', None)
        if perms is None:
            perms = ['%s.%s_%s' % (self.model._meta.app_label, self.perm_delete_prefix, self.model._meta.model_name)]
        return self.request.user.has_perms(perms)

    def get_queryset(self):
        if self.queryset is not None:
            queryset = self.queryset.all()
        elif self.model:
            queryset = self.model.objects.all()
        if self.parent_object:
            if not self.parent_lookup:
                self.parent_lookup = self.parent_queryset.model._meta.model_name
            if self.get_parent_query():
                queryset = queryset.filter(self.get_parent_query())
            else:
                queryset = queryset.filter(**{self.parent_lookup: self.parent_object})
        if self.form:
            if self.form.is_valid():
                query = self.form.get_query()
                if not query and self.empty_query:
                    return queryset.model.objects.none()
                queryset = queryset.filter(query)
                if getattr(self.form, 'distinct'):
                    queryset = queryset.distinct()
            else:
                if self.form.errors:
                    return queryset.model.objects.none()
                if self.empty_query:
                    return queryset.model.objects.none()
        if self.select_related:
            if isinstance(self.select_related, str):
                queryset = queryset.select_related(self.select_related)
            elif hasattr(self.select_related, '__iter__'):
                queryset = queryset.select_related(*self.select_related)
            else:
                queryset = queryset.select_related()
        if self.distinct is not None:
            queryset = queryset.distinct()
        if self.prefetch_related:
            if isinstance(self.prefetch_related, str):
                queryset = queryset.prefetch_related(self.prefetch_related)
            elif hasattr(self.prefetch_related, '__iter__'):
                queryset = queryset.prefetch_related(*self.prefetch_related)
            else:
                queryset = queryset.prefetch_related()
        sort = self.request.GET.get('sort')
        if sort and (sort in self.sort_list or sort[0] == '-' and sort[1:] in self.sort_list):
            queryset = queryset.order_by(sort)
            self.sort = sort
        else:
            self.sort = None
            default_sort = self.get_default_sort()
            if default_sort:
                if isinstance(default_sort, str):
                    queryset = queryset.order_by(default_sort)
                else:
                    queryset = queryset.order_by(*default_sort)
        return queryset

    def get_context_data(self, **kwargs):
        context = super(AdminListView, self).get_context_data(**kwargs)
        if self.parent_object:
            context['object'] = self.parent_object
        return context

    def dispatch(self, request, *args, **kwargs):
        if self.save_query and request.method == 'GET':
            # referer = get_referer(request, default_url='', with_params=False, local_only=True)
            queries = request.session.get('queries', {})
            query = queries.get(request.url_name)
            if 'restore' in request.GET and query:
                del queries[request.url_name]
                request.session['queries'] = queries
                request.session.modified = True
                return redirect('%s?%s' % (request.path, query))
            query = request.GET.urlencode()
            if query and query != queries.get(request.url_name):
                queries[request.url_name] = query
                request.session['queries'] = queries
                request.session.modified = True
        return super(AdminListView, self).dispatch(request, *args, **kwargs)

    def get_parent_object(self):
        if self.parent_model is None and self.parent_queryset is None:
            return None
        if self.parent_queryset is None:
            self.parent_queryset = self.parent_model.objects.all()
        if not self.parent_model:
            self.parent_model = self.queryset.model
        try:
            return self.parent_queryset.get(**{self.parent_pk: self.kwargs.get(self.parent_slug)})
        except self.parent_queryset.model.DoesNotExist:
            raise Http404

    def get_parent_query(self):
        pass

    def get_form_kwargs(self):
        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
        }
        if self.request.GET:
            kwargs.update({'data': self.request.GET or None})
        return kwargs

    def on_get(self):
        pass

    def get(self, request, *args, **kwargs):
        self.parent_object = self.get_parent_object()
        # From ProcessFormMixin
        form_class = self.get_form_class()
        if form_class:
            self.form = self.get_form(form_class)
        # From BaseListView
        self.object_list = self.get_queryset()
        forms = self.get_forms()
        self.on_get()
        context = self.get_context_data(object_list=self.object_list, form=self.form, forms=forms)
        return self.render_to_response(context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.parent_object = self.get_parent_object()
        form_class = self.get_form_class()
        if form_class:
            self.form = self.get_form(form_class)
        forms = self.get_forms()
        if forms:
            for name, form in forms.items():
                if request.POST.get('%s_submit' % name):
                    if form.is_valid():
                        form_valid = getattr(self, '%s_form_valid' % name)
                        if form_valid:
                            response = form_valid(form)
                            if response:
                                return response
                    else:
                        messages.error(request, form.errors)
                        return redirect(self.request.get_full_path())
        action = request.POST.get('_action')
        if action:
            action_function = getattr(self, 'action_%s' % action)
            if not action_function:
                raise Http404(_('Invalid action "%s"') % action)
            response = action_function()
            if response:
                return response
        return redirect(self.request.get_full_path())  # self.get(request, *args, **kwargs)

    def paginate_queryset(self, queryset, page_size):
        #    try:
        #        return super(AdminListView, self).paginate_queryset(queryset, page_size)
        #    except Http404:
        #        self.kwargs[self.page_kwarg] = 1
        #        return super(AdminListView, self).paginate_queryset(queryset, page_size)
        paginator = self.get_paginator(
            queryset, page_size, orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty())
        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        try:
            page_number = int(page)
        except ValueError:
            if page == 'last':
                page_number = paginator.num_pages
            else:
                page_number = 1
        if page_number > paginator.num_pages:
            page_number = 1
        try:
            page = paginator.page(page_number)
            return (paginator, page, page.object_list, page.has_other_pages())
        except InvalidPage as e:
            raise Http404(_('Invalid page (%(page_number)s): %(message)s') % {
                'page_number': page_number,
                'message': str(e)
            })

    def get_forms_initials(self):
        return {}

    def get_forms_kwargs(self):
        if not self.form_classes:
            return {}
        result = {}
        initials = self.get_forms_initials()
        for key in self.form_classes.keys():
            if self.request.POST.get('%s_submit' % key):
                data = self.request.POST
            else:
                data = None
            result[key] = {
                'data': data,
                'initial': initials.get(key),
                'prefix': key
            }
        return result

    def get_forms(self):
        if not self.form_classes:
            return {}
        kwargs = self.get_forms_kwargs()
        return dict((name, form_class(**kwargs.get(name))) for name, form_class in self.form_classes.items())

    def get_details(self):
        if not self.parent_object:
            return []
        result = []
        for detail in self.details:
            if isinstance(detail, (list, tuple)):
                name = detail[0]
                value = get_attribute(self.parent_object, detail[1])
            else:
                value = get_attribute(self.parent_object, detail)
                if isinstance(value, datetime.datetime):
                    value = formats.date_format(value, 'DATETIME_FORMAT', use_l10n=True)
                elif isinstance(value, datetime.date):
                    value = formats.date_format(value, 'DATE_FORMAT', use_l10n=True)
                elif isinstance(value, bool):
                    value = _('Yes') if value else _('No')
                try:
                    name = upper_first(self.parent_object.__class__._meta.get_field(detail).verbose_name)
                except FieldDoesNotExist:
                    name = detail
            result.append((name, value))
        return result

    def get_summary(self):
        pass

    def get_edit_object(self):
        pk = self.request.POST.get('id')
        return get_object_or_404(self.model, pk=pk)

    def get_edit_form(self, data, column_name, instance):
        auto_id = 'id_%s_%s_%%s' % (instance.pk, column_name)
        column = self.columns.get(column_name)
        if not column.edit:
            raise Http404
        if column.edit_form_class:
            return column.edit_form_class(data, instance=instance, auto_id=auto_id)
        if column.edit_fields:
            fields = column.edit_fields
        else:
            fields = [column.field]
        if self.edit_form_class:
            form = self.edit_form_class(data, instance=instance, auto_id=auto_id)
            for field in list(form.fields.keys()):
                if field not in fields:
                    form.fields.pop(field)
            return form
        else:
            form_class = modelform_factory(self.model, fields=fields)
            return form_class(data, instance=instance, auto_id=auto_id)

    def action_edit(self):
        data = self.request.POST
        column = data.get('_column')
        instance = self.get_edit_object()

        if '_save' not in data:
            form = self.get_edit_form(None, column, instance)
            result = {
                'success': True,
                'content': render_to_string('gutils/item_list_edit.html',
                                            {'view': self,
                                             'column': column,
                                             'form': form},
                                            self.request)
            }
            return JsonResponse(result)
        form = self.get_edit_form(data, column, instance)
        if form.is_valid():
            item = form.save()
            result = {
                'success': True,
                'content': render_to_string('gutils/table_row.html',
                                            {'view': self,
                                             'column_list': self.get_column_list(),
                                             'item': item},
                                            self.request)
            }
        else:
            result = {
                'success': False,
                'content': render_to_string('gutils/item_list_edit.html',
                                            {'view': self,
                                             'column': column,
                                             'form': form},
                                            self.request)
            }
        return JsonResponse(result)

    def action_delete(self):
        if self.can_delete():
            ids = [to_int(i) for i in self.request.POST.getlist('ids') if to_int(i)]
            total = 0
            for o in self.get_queryset().filter(pk__in=ids):
                try:
                    o.delete()
                    total += 1
                except ProtectedError:
                    messages.error(self.request, _('Impossible delete "%s". This element depended others.') % o)
            messages.info(self.request, _('%s deleted.') % total)
        else:
            messages.error(self.request, _('You haven\'t permissions to delete items.'))

    def action_select_columns(self):
        if self.allow_select_columns:
            columns = set(self.columns.keys()) & set(self.request.POST.getlist('column'))
            AdminViewConfModel.set_user_selected_columns(
                user=self.request.user,
                url_name=self.request.url_name,
                columns=columns)


class AdminDetailView(PermissionMixin, TitleMixin, ListLinkMixin, DetailView):
    model = None
    perm_prefix = 'view'
    tabs = None

    def get_title(self):
        return self.title or self.object

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        return super(AdminDetailView, self).post(request, *args, **kwargs)


class AdminEditView(PermissionMixin, EditFormMixin, UpdateView):
    model = None
    template_name = 'gutils/item_edit.html'
    css = None
    js = None
    perm_prefix = 'edit'
    allow_create = True
    form_details = []
    formset_class = None
    formset_horizontal = False
    save_on_top = False
    form_enctype = ''
    form_buttons = []
    exclude = []
    tabs = None
    initial_get = False
    stay = False
    popup = True

    def __init__(self, *args, **kwargs):
        pre_init_view.send(sender=self.__class__, instance=self)
        super(AdminEditView, self).__init__(*args, **kwargs)
        self.is_editing = False
        post_init_view.send(sender=self.__class__, instance=self)

    def form_save(self, form):
        self.object = form.save()

    def formset_save(self, formset):
        if issubclass(self.formset_class, BaseModelFormSet):
            formset.save()

    def get_queryset(self):
        queryset = super(AdminEditView, self).get_queryset()
        if self.is_editing:
            queryset = queryset.select_for_update()
        return queryset

    def get_object(self, *args, **kwargs):
        if self.allow_create and not to_int(self.kwargs.get(self.pk_url_kwarg)) \
                and not self.kwargs.get(self.slug_url_kwarg):
            return
        return super(AdminEditView, self).get_object(*args, **kwargs)

    def get_form_kwargs(self):
        res = super(AdminEditView, self).get_form_kwargs()
        return res

    def get_form_buttons(self):
        return self.form_buttons

    def get_initial(self):
        initial = super(AdminEditView, self).get_initial().copy()
        initial['next'] = get_referer(self.request, default_url=settings.GUTILS_ADMIN_INDEX)
        if self.initial_get:
            for key, value in self.request.GET.items():
                if value and key in self.get_form_class()._meta.fields:
                    initial[key] = value
        return initial

    def get_formset_initial(self):
        return {}

    def form_valid(self, form, formset=None):
        if self.form_save(form) is False:
            return self.form_invalid(form, formset)
        if formset:
            formset.instance = self.object
            if self.formset_save(formset) is False:
                return self.form_invalid(form, formset)
        messages.info(self.request, _('%s saved.') % get_name(self.model))
        # return redirect(self.get_success_url())
        return close_view(self.request, next=self.get_success_url(), stay=self.stay,
                          popup=self.request.is_popup)

    def form_invalid(self, form, formset=None):
        print(form.errors)
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    def get_form_class(self):
        if self.form_class:
            return self.form_class
        else:
            if self.model is not None:
                model = self.model
            else:
                model = self.get_queryset().model
            return modelform_factory(model, form=ModelForm, fields=self.fields, exclude=self.exclude)

    def get_formset_queryset(self):
        return

    def on_get(self):
        pass

    def check_object(self):
        return

    def get(self, request, *args, **kwargs):
        self.is_editing = False
        self.object = self.get_object()
        response = self.check_object()
        if response:
            return response
        form = self.get_form(self.get_form_class())
        if self.formset_class:
            if issubclass(self.formset_class, BaseModelFormSet):
                formset = self.formset_class(None, instance=self.object, queryset=self.get_formset_queryset(),
                                             initial=self.get_formset_initial())
            else:
                formset = self.formset_class(None, initial=self.get_formset_initial())
        else:
            formset = None
        self.on_get()
        return self.render_to_response(self.get_context_data(form=form, formset=formset))

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.is_editing = True
        self.object = self.get_object()
        response = self.check_object()
        if response:
            return response
        form_class = self.get_form_class()
        self.form = self.get_form(form_class)
        if self.formset_class:
            if issubclass(self.formset_class, BaseModelFormSet):
                self.formset = self.formset_class(request.POST, instance=self.object, queryset=self.get_formset_queryset())
            else:
                self.formset = self.formset_class(request.POST)
        else:
            self.formset = None
        if self.form.is_valid():
            if self.formset and not self.formset.is_valid():
                return self.form_invalid(self.form, self.formset)
            return self.form_valid(self.form, self.formset)
        else:
            return self.form_invalid(self.form, self.formset)


class AdminFormSetView(PermissionMixin, EditFormMixin, DetailView):
    model = None
    template_name = 'gutils/item_edit.html'
    save_on_top = False
    perm_prefix = 'edit'
    formset_class = None
    form_enctype = ''
    form_buttons = []
    exclude = []
    tabs = None
    title = None

    def __init__(self, *args, **kwargs):
        pre_init_view.send(sender=self.__class__, instance=self)
        super(AdminFormSetView, self).__init__(*args, **kwargs)
        self.is_editing = False
        post_init_view.send(sender=self.__class__, instance=self)

    def formset_save(self, formset):
        self.object_list = formset.save()

    def get_queryset(self):
        queryset = super(AdminEditView, self).get_queryset()
        if self.is_editing:
            queryset = queryset.select_for_update()
        return queryset

    def get_object(self):
        return super(AdminFormSetView, self).get_object()

    def get_form_buttons(self):
        return self.form_buttons

    def get_initial(self):
        initial = super(AdminFormSetView, self).get_initial().copy()
        initial['next'] = get_referer(self.request, default_url=settings.GUTILS_ADMIN_INDEX)
        return initial

    def formset_valid(self, formset=None):
        self.formset_save(formset)
        messages.info(self.request, _('%s saved.') % get_name(self.model))
        return close_view(self.request, next=self.get_success_url(), popup=self.request.is_popup)

    def formset_invalid(self, formset):
        return self.render_to_response(self.get_context_data(formset=formset))

    def get(self, request, *args, **kwargs):
        self.is_editing = False
        self.object = self.get_object()
        formset = self.formset_class(instance=self.object)
        return self.render_to_response(self.get_context_data(formset=formset))

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.is_editing = True
        self.object = self.get_object()
        formset = self.formset_class(request.POST, instance=self.object)
        if formset.is_valid():
            return self.formset_valid(formset)
        return self.formset_invalid(formset)


class AdminFormView(PermissionMixin, EditFormMixin, ItemFormView):
    template_name = 'gutils/item_edit.html'
    form_buttons = []

    def __init__(self, *args, **kwargs):
        pre_init_view.send(sender=self.__class__, instance=self)
        super(AdminFormView, self).__init__(*args, **kwargs)
        post_init_view.send(sender=self.__class__, instance=self)

    def get_form_buttons(self):
        return self.form_buttons


class AdminItemActionView(PermissionMixin, ItemActionView):
    perm_prefix = 'edit'

    def __init__(self, *args, **kwargs):
        pre_init_view.send(sender=self.__class__, instance=self)
        super(AdminItemActionView, self).__init__(*args, **kwargs)
        post_init_view.send(sender=self.__class__, instance=self)


class AdminItemDeleteView(PermissionMixin, TemplateView):
    model = None
    template_name = 'gutils/item_delete.html'
    admin_login_url = False

    def __init__(self, *args, **kwargs):
        pre_init_view.send(sender=self.__class__, instance=self)
        super(AdminItemDeleteView, self).__init__(*args, **kwargs)
        post_init_view.send(sender=self.__class__, instance=self)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(AdminItemDeleteView, self).dispatch(*args, **kwargs)

    def get_object(self):
        self.object = get_object_or_404(self.model, pk=self.kwargs['pk'])
        return self.object

    def get_perms(self):
        if self.perms:
            return self.perms
        if hasattr(self.model, 'DELETE_PERMISSIONS'):
            return self.model.DELETE_PERMISSIONS
        ct = ContentType.objects.get_for_model(self.model)
        return ['%s.%s_%s' % (ct.app_label, 'delete', ct.model)]

    def get(self, request, *args, **kwargs):
        self.get_object()
        items = get_realated_items(self.object)
        return self.render_to_response(self.get_context_data(object=self.object,
                                                             items=items, next=get_referer(self.request)))

    def post(self, request, *args, **kwargs):
        self.get_object()
        self.do_delete()
        timeout = 0
        return close_view(self.request, next=self.request.POST.get('next') or '/admin',
                          timeout=timeout, popup=request.is_popup)

    def do_delete(self):
        pass


class Action(object):

    def __init__(self, **kwargs):
        self.action = kwargs.get('action')
        self.name = kwargs.get('name', '')
        self.title = kwargs.get('title', '') or self.name
        self.icon = kwargs.get('icon', '')
        self.style = kwargs.get('style', '')

    def display(self, view):
        icon = ''
        if self.icon:
            icon = '<span class="fa %s"></span></span> ' % self.icon
        return '<button class="btn %s" type="submit" name="_action" value="%s" title="%s">%s%s</button>' % \
            (self.style, self.action, self.title, icon, self.name)


class Link(object):
    id = None
    url = None
    modal = None
    name = None
    title = None
    icon = None
    type = None
    popup = False
    target = None

    def __init__(self, url=None, modal=None, name=None, title=None, icon=None, type=None,
                 popup=False, popup_reload=False, id=None, target=None):
        self.url = url
        self.modal = modal
        self.name = name
        self.title = title
        self.icon = icon
        self.type = type
        self.popup = popup
        self.popup_reload = popup_reload
        self.id = id
        self.target = target

    def get_url(self, view):
        if self.url:
            if hasattr(self.url, '__call__'):
                return self.url(view)
            elif '/' in self.url or '#' in self.url:
                return self.url
            else:
                return reverse(self.url)
        elif self.modal:
            return '#%s-form' % self.modal
        else:
            return '#'

    def display(self, view):
        url = self.get_url(view)
        if self.title:
            title = ' title="%s"' % escape(self.title)
        else:
            title = ''
        if self.icon:
            icon = '<span class="fa %s"></span> ' % self.icon
        else:
            icon = ''
        cls = ['btn']
        if self.type:
            cls.append('btn-%s' % self.type)
        if self.modal:
            cls.append('modal-box')
        if self.popup:
            cls.append('popup')
            if self.popup_reload:
                cls.append('popup-reload')
        if self.id:
            id = ' id="%s"' % self.id
        else:
            id = ''
        if self.target:
            target = ' target="%s"' % self.target
        else:
            target = ''
        name = escape(self.name or '')
        return '<a href="%s" class="%s"%s%s%s>%s%s</a>' % (url, ' '.join(cls), id, title, target, icon, name)


class JavaScriptCatalog(_JavaScriptCatalog):

    def get_context_data(self, **kwargs):
        context = super(JavaScriptCatalog, self).get_context_data(**kwargs)
        for key in ('DATE_SEPARATOR', 'JS_DATE_FORMAT', 'JS_TIME_FORMAT', 'JS_DATETIME_FORMAT'):
            context['formats'][key] = formats.get_format(key)
        return context
