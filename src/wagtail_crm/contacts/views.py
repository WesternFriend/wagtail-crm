from typing import override

from django.template.defaultfilters import linebreaksbr
from wagtail.admin.views.generic.models import InspectView
from wagtail.admin.viewsets.model import ModelViewSet

from .forms import ContactForm
from .models import Contact


class ContactInspectView(InspectView):
    # Default Inspect rendering collapses the lines of a postal address.
    def get_postal_address_display_value(self):
        return (
            linebreaksbr(self.object.postal_address)
            if self.object.postal_address
            else "—"
        )


class ContactViewSet(ModelViewSet):
    model = Contact
    icon = "user"
    menu_label = "Contacts"
    add_to_admin_menu = True
    url_prefix = "crm/contacts"
    url_namespace = "wagtail_crm_contacts"
    list_display = ("display_name", "kind", "email")
    list_filter = ("kind",)
    search_fields = ("display_name", "email")
    inspect_view_enabled = True
    inspect_view_class = ContactInspectView
    inspect_view_fields = ("display_name", "kind", "email", "postal_address")
    copy_view_enabled = False

    @override
    def get_form_class(self, for_update=False):
        return ContactForm
