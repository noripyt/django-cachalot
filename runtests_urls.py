import debug_toolbar
from django.urls import path, re_path, include
from django.http import HttpResponse
from django.contrib import admin


def empty_page(request):
    return HttpResponse('<body></body>')


urlpatterns = [
    re_path(r'^$', empty_page),
    re_path(r'^__debug__/', include(debug_toolbar.urls)),
    path('admin/', admin.site.urls),
]
