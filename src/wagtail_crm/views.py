from typing import override

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import redirect
from wagtail.admin import messages
from wagtail.admin.views.generic.models import (
    CreateView,
    DeleteView,
    EditView,
    InspectView,
)
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.log_actions import log

from wagtail_crm.forms import ContactForm
from wagtail_crm.models import Contact
from wagtail_crm.services import delete_contact


class ContactCreateView(CreateView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["actor"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValidationError as exc:
            form.add_error(None, exc.messages)
            self.produced_error_message = self.get_error_message()
            self.produced_error_code = "validation_error"
            return self.form_invalid(form)


class ContactEditView(EditView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["actor"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValidationError as exc:
            form.add_error(None, exc.messages)
            self.produced_error_message = self.get_error_message()
            self.produced_error_code = "validation_error"
            return self.form_invalid(form)


class ContactDeleteView(DeleteView):
    def delete_action(self):
        with transaction.atomic():
            log(instance=self.object, action="wagtail.delete")
            delete_contact(self.object, actor=self.request.user)

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ValidationError as exc:
            messages.error(self.request, " ".join(exc.messages))
            return redirect(self.get_success_url())


class ContactInspectView(InspectView):
    permission_required = "view"
    any_permission_required = None
    template_name = "wagtail_crm/contacts/inspect.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        history = self.object.history.select_related("actor")
        context["contact_history"] = Paginator(history, 20).get_page(
            self.request.GET.get("history_page")
        )
        return context


class ContactViewSet(ModelViewSet):
    model = Contact
    icon = "user"
    menu_label = "Contacts"
    add_to_admin_menu = True
    url_prefix = "crm/contacts"
    url_namespace = "wagtail_crm_contacts"
    form_fields = ("name", "kind", "email", "postal_address")
    list_display = ("display_name", "kind", "email")
    list_filter = ("kind",)
    search_fields = ("display_name", "email")
    inspect_view_enabled = True
    inspect_view_class = ContactInspectView
    inspect_view_fields = ("display_name", "kind", "email", "uid")
    add_view_class = ContactCreateView
    edit_view_class = ContactEditView
    delete_view_class = ContactDeleteView
    copy_view_enabled = False

    @override
    def get_form_class(self, for_update=False):
        return ContactForm
