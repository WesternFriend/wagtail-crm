from wagtail import hooks

from wagtail_crm.views import ContactViewSet


@hooks.register("register_admin_viewset")
def register_contacts_viewset():
    return ContactViewSet("wagtail_crm_contacts")
