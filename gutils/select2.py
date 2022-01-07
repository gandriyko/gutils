from django import forms
from django.forms import widgets
from django.utils.encoding import force_text


class AjaxSelectMixin(object):
    choices = []

    class Media:
        js = ('gutils/js/select2/select2.full.min.js',
              'gutils/js/select2/select2_widget.js')
        css = {'all': ('gutils/js/select2/select2.min.css',)}

    def __init__(self, attrs=None, choices=(), allow_empty=None, url=None):
        self.allow_empty = allow_empty
        self.url = url
        self.value_text = None
        super(AjaxSelectMixin, self).__init__(attrs=attrs, choices=choices)

    def get_context(self, name, value, attrs):
        # emulate choices
        if value and hasattr(self, 'queryset'):
            obj = self.queryset.filter(pk=value).first()
            if obj:
                self.value_text = getattr(obj, 'select2', str(obj))
            self.choices = [(value, self.value_text)]
        return super(AjaxSelectMixin, self).get_context(name, value, attrs)

    def build_attrs(self, *args, **kwargs):
        attrs = super(AjaxSelectMixin, self).build_attrs(*args, **kwargs)
        if 'class' in attrs:
            attrs['class'] += ' select2-widget'
        else:
            attrs['class'] = 'select2-widget'
        if self.allow_empty:
            attrs.setdefault('data-allow-clear', 'true')
        else:
            attrs.setdefault('data-allow-clear', 'false')
        if self.url:
            attrs.setdefault('data-ajax--url', self.url)
        attrs.setdefault('data-ajax--cache', 'false')
        attrs.setdefault('data-ajax--type', 'GET')
        attrs.setdefault('data-dropdown-auto-width', 'true')
        return attrs


class AjaxSelect(AjaxSelectMixin, widgets.Select):
    pass


class AjaxMultipleSelect(AjaxSelectMixin, widgets.SelectMultiple):
    def get_context(self, name, value, attrs):
        # emulate choices
        if value and self.value_text:
            self.choices = self.value_text.items()
        return super(AjaxSelectMixin, self).get_context(name, value, attrs)


class AjaxModelMixin(object):
    widget = None
    _url = None
    _allow_empty = None
    queryset = None

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = self.widget.url = value

    @property
    def allow_empty(self):
        return self._allow_empty

    @allow_empty.setter
    def allow_empty(self, value):
        self._allow_empty = self.widget.allow_empty = value

    def coerce(self, value):
        if value:
            result = self.queryset.get(pk=value)
        else:
            result = None
        self.widget.value_text = result or ''
        return result

    def clean(self, value):
        if value:
            try:
                return self.coerce(value)
            except self.queryset.model.DoesNotExist as e:
                raise forms.ValidationError(force_text(e))
        return value


class AjaxModelField(AjaxModelMixin, forms.ChoiceField):
    widget = AjaxSelect

    def __init__(self, *args, **kwargs):
        _queryset = kwargs.pop('queryset')
        _url = kwargs.pop('url', None)
        _allow_empty = kwargs.pop('allow_empty', not kwargs.get('required'))
        super(AjaxModelMixin, self).__init__(*args, **kwargs)
        self.allow_empty = _allow_empty
        self.queryset = _queryset
        self.widget.queryset = _queryset
        self.url = _url


class AjaxMultipleModelField(AjaxModelMixin, forms.MultipleChoiceField):
    widget = AjaxMultipleSelect

    def __init__(self, *args, **kwargs):
        _queryset = kwargs.pop('queryset')
        _url = kwargs.pop('url', None)
        _allow_empty = kwargs.pop('allow_empty', None)
        super(AjaxMultipleModelField, self).__init__(choices=(), *args, **kwargs)
        self.allow_empty = _allow_empty
        self.queryset = _queryset
        self.url = _url

    def coerce(self, value):
        if value:
            result = self.queryset.filter(pk__in=value)
            qs = self.queryset.filter(pk__in=value)
            self.widget.value_text = {v.id: force_text(v) for v in qs}
        else:
            result = None
            self.widget.value_text = None
        return result
