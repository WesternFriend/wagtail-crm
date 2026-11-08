import json
from collections.abc import Callable
from typing import override

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.shortcuts import redirect
from django.template.defaultfilters import linebreaksbr
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic.edit import FormMixin
from wagtail.admin import messages
from wagtail.admin.ui.tables import Column, DateColumn, UserColumn
from wagtail.admin.views.generic.history import HistoryView
from wagtail.admin.views.generic.models import (
    CreateView,
    DeleteView,
    EditView,
    InspectView,
)
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.log_actions import log

from wagtail_crm.forms import ContactDeleteForm, ContactForm
from wagtail_crm.models import Contact
from wagtail_crm.services import delete_contact


class ContactFormViewMixin(FormMixin):
    request: HttpRequest
    get_error_message: Callable[[], str]

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


class ContactCreateView(ContactFormViewMixin, CreateView):
    pass


class ContactEditView(ContactFormViewMixin, EditView):
    pass


class ContactDeleteView(DeleteView):
    form_class = ContactDeleteForm
    template_name = "wagtail_crm/contacts/confirm_delete.html"

    def get_initial(self):
        return super().get_initial() | {"expected_revision": self.object.revision}

    def delete_action(self):
        with transaction.atomic():
            log(instance=self.object, action="wagtail.delete")
            delete_contact(
                self.object,
                actor=self.request.user,
                expected_revision=self.expected_revision,
            )

    def form_valid(self, form):
        self.expected_revision = form.cleaned_data["expected_revision"]
        try:
            return super().form_valid(form)
        except ValidationError as exc:
            messages.error(self.request, " ".join(exc.messages))
            return redirect(self.get_delete_url())


class ContactInspectView(InspectView):
    permission_required = "view"
    any_permission_required = None

    def get_field_display_value(self, field_name, field):
        if field_name == "postal_address":
            return (
                linebreaksbr(self.object.postal_address)
                if self.object.postal_address
                else "—"
            )
        return super().get_field_display_value(field_name, field)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["history_url"] = reverse(
            "wagtail_crm_contacts:history", args=[self.object.pk]
        )
        return context


class ContactChangesColumn(Column):
    cell_template_name = "wagtail_crm/contacts/history_changes.html"

    def get_cell_context_data(self, instance, parent_context):
        context = super().get_cell_context_data(instance, parent_context)
        before, after = instance.before or {}, instance.after or {}
        changes = []
        for field, label in (
            ("display_name", "Name"),
            ("kind", "Contact type"),
            ("email", "Email"),
            ("postal_address", "Postal address"),
        ):
            old, new = before.get(field), after.get(field)
            if (old or "") != (new or ""):
                if field == "kind":
                    old = Contact.Kind(old).label if old else None
                    new = Contact.Kind(new).label if new else None
                changes.append(
                    {
                        "label": label,
                        "before": old,
                        "after": new,
                        "whitespace_changed": (
                            field in {"display_name", "postal_address"}
                            and isinstance(old, str)
                            and isinstance(new, str)
                            and " ".join(old.split()) == " ".join(new.split())
                        ),
                    }
                )
        context["action_label"] = instance.get_action_display()
        context["changes"] = changes
        context["structure_changed"] = before.get("name") != after.get(
            "name"
        ) and before.get("display_name") == after.get("display_name")
        context["before_snapshot"] = json.dumps(
            instance.before, ensure_ascii=False, indent=2
        )
        context["after_snapshot"] = json.dumps(
            instance.after, ensure_ascii=False, indent=2
        )
        return context


class ContactHistoryView(HistoryView):
    permission_required = "view"
    any_permission_required = None
    filterset_class = None
    verbose_name_plural = "contact changes"

    @cached_property
    def columns(self):
        return [
            ContactChangesColumn("action", label="Changes"),
            UserColumn(
                "actor",
                label="Changed by",
                blank_display_name="System or unavailable account",
            ),
            DateColumn("occurred_at", label="Date"),
            Column("origin", label="Origin", accessor="get_origin_display"),
        ]

    def get_base_queryset(self):
        return self.object.history.select_related("actor", "actor__wagtail_userprofile")

    def get_edit_url(self, instance):
        if self.user_has_permission("change"):
            return super().get_edit_url(instance)
        return None

    def get_breadcrumbs_items(self):
        items = super().get_breadcrumbs_items()
        if not self.get_edit_url(self.object):
            items.insert(
                -1,
                {
                    "url": reverse(
                        "wagtail_crm_contacts:inspect", args=[self.object.pk]
                    ),
                    "label": self.get_page_subtitle(),
                },
            )
        return items

    @cached_property
    def header_buttons(self):
        return super().header_buttons if self.get_edit_url(self.object) else []


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
    history_view_class = ContactHistoryView
    add_view_class = ContactCreateView
    edit_view_class = ContactEditView
    delete_view_class = ContactDeleteView
    copy_view_enabled = False

    @override
    def get_form_class(self, for_update=False):
        return ContactForm
