from django.urls import reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .views import ContactViewSet


@hooks.register("register_admin_viewset")
def register_contacts_viewset():
    return ContactViewSet("wagtail_crm_contacts")


@hooks.register("construct_reports_menu")
def show_contact_activity(request, items):
    # Wagtail normally hides Site history from staff without page permissions.
    if request.user.has_module_perms("wagtail_crm_contacts") and not any(
        item.name == "site-history" for item in items
    ):
        items.append(
            MenuItem(
                "Site history",
                reverse("wagtailadmin_reports:site_history"),
                name="site-history",
                icon_name="history",
            )
        )
