from typing import override

from django import forms
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.template.defaultfilters import linebreaksbr
from django.views import View
from wagtail.admin.forms.choosers import BaseFilterForm
from wagtail.admin.views.generic.chooser import (
    ChooseResultsView,
    ChooseView,
    ChosenMultipleView,
    ChosenView,
    CreateView,
)
from wagtail.admin.viewsets.chooser import ChooserViewSet
from wagtail.log_actions import log

from wagtail_crm.admin_views import CRMViewSet, InspectView

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


class ContactViewSet(CRMViewSet):
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


class ContactSearchForm(BaseFilterForm):
    """Search by name or email, as the contact list does.

    Wagtail's chooser only offers search for search-indexed models; Contact
    uses database search, like its listing.
    """

    q = forms.CharField(
        label="Search term",
        widget=forms.TextInput(attrs={"placeholder": "Search"}),
        required=False,
    )

    def filter(self, objects):
        objects = super().filter(objects)
        query = self.cleaned_data.get("q")
        if query:
            self.is_searching = True
            self.search_query = query
            objects = objects.filter(
                Q(display_name__icontains=query) | Q(email__icontains=query)
            )
        return objects


class ContactAccessMixin(View):
    """Wagtail checks only "add" on the chooser's Create tab; listing and
    choosing contacts need the same access as the Contacts menu."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_module_perms("wagtail_crm_contacts"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ContactChooseView(ContactAccessMixin, ChooseView):
    filter_form_class = ContactSearchForm


class ContactChooseResultsView(ContactAccessMixin, ChooseResultsView):
    filter_form_class = ContactSearchForm


class ContactChosenView(ContactAccessMixin, ChosenView):
    pass


class ContactChosenMultipleView(ContactAccessMixin, ChosenMultipleView):
    pass


class ContactChooserCreateView(CreateView):
    # Wagtail's chooser saves without a log entry; the Contacts form logs one.
    def save_form(self, form):
        with transaction.atomic():
            contact = super().save_form(form)
            log(instance=contact, action="wagtail.create", content_changed=True)
        return contact


class ContactChooserViewSet(ChooserViewSet):
    """Choose a contact, or create one with the same rules as the Contacts form."""

    model = Contact
    icon = "user"
    choose_one_text = "Choose a contact"
    choose_another_text = "Choose another contact"
    edit_item_text = "Edit this contact"
    creation_form_class = ContactForm
    choose_view_class = ContactChooseView
    choose_results_view_class = ContactChooseResultsView
    chosen_view_class = ContactChosenView
    chosen_multiple_view_class = ContactChosenMultipleView
    create_view_class = ContactChooserCreateView
