from django.conf.urls import url
from django.utils import timezone
from django.views.decorators.http import last_modified
from gutils.views import JavaScriptCatalog
from gutils.admin import views

last_modified_date = timezone.now()

urlpatterns = [
    url(r'^item\-change/(?P<model_path>[\w\.\-]+)/(?P<pk>\d+)/(?P<field>[\w_\.]+)/$', views.ItemChangeView.as_view(),
        name='admin-item-change'),
    url(r'^item\-delete/(?P<model_path>[\w\.]+)/(?P<pk>\d+)/$', views.ItemDeleteView.as_view(),
        name='admin-item-delete'),
    url(r'^images/$', views.ImageListView.as_view(),
        name='admin-image-list'),
    url(r'^gutils\-locale\.js$', last_modified(lambda req, **kw: last_modified_date)(JavaScriptCatalog.as_view()),
        name='gutils-locale-js'),
]
