from django.urls import include, path
from django.views.generic import RedirectView
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
]

# Do not expose MEDIA_ROOT through a catch-all static route: that would bypass
# document access checks. CRM artifact storage will be added with its workflow.
