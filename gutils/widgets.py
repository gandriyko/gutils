from django import forms
from django.conf import settings
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.encoding import force_str
from django.forms.utils import flatatt
from django.utils.html import escape, conditional_escape
from time import strftime
from gutils.dates import format_date_range
from gutils.images import save_image
import os
import re


class FileInput(forms.FileInput):
    input_type = 'file'

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(attrs)
        attrs['class'] = 'file-hidden'
        input = super(FileInput, self).render(name, value, attrs)
        return mark_safe('<label id="file-%s" class="btn" for="%s">%s</label>%s' %
                         (attrs['id'], attrs['id'], _('Select file'), input))


class Textarea(forms.widgets.Textarea):

    class Media:
        js = ('gutils/js/tinymce/tinymce.min.js', 'gutils/js/textarea.js')

    def __init__(self, attrs=None):
        if not attrs:
            attrs = {'class': 'rich-editor'}
        else:
            attrs['class'] = "rich-editor text-input %s" % attrs.get('class', '')
        attrs['data-url-images'] = reverse_lazy('admin-image-list')
        super(Textarea, self).__init__(attrs)


class DateInput(forms.DateInput):

    class Media:
        js = ['gutils/js/datetimepicker.js']

    def __init__(self, attrs=None, format=None):
        if not attrs:
            attrs = {'class': 'date-input', 'autocomplete': 'off'}
        else:
            attrs['class'] = "%s %s " % ('date-input', attrs.get('class', ''))
        super(DateInput, self).__init__(attrs, format)

    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(attrs)
        output = super(DateInput, self).render(name, value, attrs)
        return mark_safe("%s<script>$(function(){$('#%s').widgetDate();});</script>" % (output, final_attrs['id']))


class DateTimeInput(forms.DateTimeInput):

    class Media:
        js = ('gutils/js/jquery/jquery-ui-timepicker-addon.js',
              'gutils/js/datetimepicker.js')
        css = {'all': ('gutils/js/jquery/jquery-ui-timepicker-addon.css',)}

    def __init__(self, attrs=None, format=None):
        if not attrs:
            attrs = {'class': 'datetime-input', 'autocomplete': 'off'}
        else:
            attrs['class'] = "%s %s " % ('date-input', attrs.get('class'))
        super(DateTimeInput, self).__init__(attrs, format)

    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(attrs)
        output = super(DateTimeInput, self).render(name, value, attrs)
        return mark_safe("%s<script>$(function(){$('#%s').widgetDateTime();});</script>" % (output, final_attrs['id']))


class DateRangeInput(forms.DateInput):

    class Media:
        js = ['gutils/js/datetimepicker.js']

    def __init__(self, attrs=None):
        if not attrs:
            attrs = {'class': 'daterange-input'}
        else:
            attrs['class'] = "%s %s " % ('daterange-input', attrs.get('class'))
        attrs['autocomplete'] = 'off'
        super(DateRangeInput, self).__init__(attrs, format)

    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(attrs)
        output = super(DateRangeInput, self).render(name, value, attrs)
        return mark_safe("%s<script>$(function(){$('#%s').widgetDateRange();});</script>" % (output, final_attrs['id']))

    def format_value(self, value):
        if isinstance(value, list) or isinstance(value, tuple):
            return format_date_range(value[0], value[1])
        return value


class PasswordInput(forms.PasswordInput):
    class Media:
        css = {
            'all': ('gutils/js/sauron/sauron.css',),
        }
        js = ('gutils/js/sauron/jquery.sauron.min.js',)

    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(attrs)
        output = super(PasswordInput, self).render(name, value, attrs)
        return mark_safe("%s<script>$(function(){$('#%s').sauron();});</script>" % (output, final_attrs['id']))


class NullBooleanSelect(forms.NullBooleanSelect):

    def __init__(self, attrs=None):
        choices = (
            ('unknown', _('--------')),
            ('true', _('Yes')),
            ('false', _('No')),
        )
        super(forms.NullBooleanSelect, self).__init__(attrs, choices)


class SelectColored(forms.Select):

    def __init__(self, attrs=None, choices=()):
        if not attrs:
            attrs = {'class': 'colored'}
        super(SelectColored, self).__init__(attrs)

    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs)
        final_attrs['class'] = "%s-%s" % (final_attrs.get('class'), value)
        output = ['<select%s>' % flatatt(final_attrs)]
        options = self.render_options(choices, [value])
        if options:
            output.append(options)
        output.append('</select>')
        return mark_safe('\n'.join(output))

    def render_option(self, selected_choices, option_value, option_label):
        option_value = force_str(option_value)
        selected_html = (option_value in selected_choices) and ' selected="selected"' or ''
        return '<option class="%s-%s" value="%s"%s>%s</option>' % (
            self.attrs.get('class'), escape(option_value), escape(option_value), selected_html,
            conditional_escape(force_str(option_label)))


class SelectMultiple(forms.SelectMultiple):

    class Media:
        css = {
            'all': ('gutils/js/sumoselect/sumoselect.css', )
        }
        js = ('gutils/js/sumoselect/jquery.sumoselect.min.js', )

    TEMPLATE = """%s
    <script type="text/javascript">
        $(document).ready(function() {
            $('#%s').SumoSelect({search:true,selectAll:true,placeholder:'%s',locale:['%s','%s','%s'],captionFormat:'%s',captionFormatAllSelected:'%s'});
        });
    </script>
    """

    def render(self, name, value, attrs=None, **kwargs):
        result = super(SelectMultiple, self).render(name, value, attrs, **kwargs)
        if value is None:
            value = []
        final_attrs = self.build_attrs(attrs)
        return mark_safe(self.TEMPLATE % (result, final_attrs['id'],
                                          _('Select'), _('OK'), _('Cancel'),
                                          _('Select all'), _('Selected: {0}'), _('Selected: {0}')))


class SplitDateTimeWidget(forms.widgets.MultiWidget):

    def __init__(self, attrs=None, date_format=None, time_format=None):
        date_attrs = {'class': 'datetime-input', 'autocomplete': 'off'}
        time_attrs = {'class': 'time-input', 'autocomplete': 'off', 'maxlength': 2}
        if attrs:
            if attrs.get('date_attrs'):
                date_attrs = attrs.get('date_attrs')
            if attrs.get('time_attrs'):
                time_attrs = attrs.get('time_attrs')
        widgets = (DateInput(attrs=date_attrs, format=date_format),
                   forms.widgets.TextInput(attrs=time_attrs),
                   forms.widgets.TextInput(attrs=time_attrs))

        super(SplitDateTimeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            d = strftime("%d.%m.%Y", value.timetuple())
            hour = strftime("%H", value.timetuple())
            minute = strftime("%M", value.timetuple())
            return (d, hour, minute)
        else:
            return (None, None, None)

    def format_output(self, rendered_widgets):

        return '<div class="split-datetime">%s %s %s %s %s</div>' % \
            (rendered_widgets[0], rendered_widgets[1], _('h.'), rendered_widgets[2], _('min.'))


class ImagesWidget(forms.widgets.Widget):
    needs_multipart_form = True

    def __init__(self, attrs=None, max_images=20, size='800x600', quality=50, button_text='', button_class=''):
        self.max_images = max_images
        self.size = size
        self.quality = quality
        self.button_text = button_text or _('Add Image')
        self.button_class = button_class
        super(ImagesWidget, self).__init__(attrs)

    def value_from_datadict(self, data, files, name):
        images = []
        errors = []
        for image in data.getlist(name, []):
            if re.match(r'^\w{32}\.\w{3}$', image) and os.path.isfile(os.path.join(settings.MEDIA_ROOT, 'temp', image)):
                images.append(image)
        for i in range(0, self.max_images):
            f = files.get('%s%s' % (name, i), None)
            if not f:
                continue
            try:
                image = save_image(f, folder='temp', size=self.size, quality=self.quality)
            except Exception:
                image = None
            if image:
                images.append(os.path.basename(image))
            else:
                errors.append(f.name)
        return images, errors

    def render(self, name, value, attrs=None, renderer=None):
        if value and value[0]:
            images = []
            for image in value[0]:
                images.append(
                    '<li><label><input type="checkbox" name="%s" value="%s" checked="checked"/> <img src="%s" alt=""/></label></li>' %
                    (name, image, os.path.join(settings.MEDIA_URL, 'temp', image).replace('\\', '/')))
            images = '\n<ul class="form-select-images">\n%s\n</ul>\n' % '\n'.join(images)
        else:
            images = ''
        output = '''%(images)s
<ul id="id_%(name)s_list" class="form-upload-images"></ul>
<p><button id="id_%(name)s_button" class="%(button_class)s" type="button">%(button_text)s</button></p>
<script>
$(function() {
    $('#id_%(name)s_button').click(function() {
        var count = $('#id_%(name)s_list input').length;
        $('#id_%(name)s_list').append('<li><input type="file" name="%(name)s'+count+'" /></li>');
        $('#id_%(name)s_list input:last').click();
    });
});
</script>'''
        return output % {'name': name,
                         'images': images,
                         'button_class': self.button_class,
                         'button_text': force_str(self.button_text)}
