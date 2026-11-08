from wagtail.admin.viewsets.model import ModelViewSet

from wagtail_crm.models import Contact


class ContactViewSet(ModelViewSet):
    model = Contact
    icon = "user"
    menu_label = "Contacts"
    add_to_admin_menu = True
    url_prefix = "crm/contacts"
    url_namespace = "wagtail_crm_contacts"
    form_fields = ("display_name", "kind", "email")
    list_display = ("display_name", "kind", "email")
    list_filter = ("kind",)
    search_fields = ("display_name", "email")
    inspect_view_enabled = True
    copy_view_enabled = False
