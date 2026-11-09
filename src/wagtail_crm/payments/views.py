import hashlib

from django import forms
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin
from wagtail.admin.views.generic.models import IndexView
from wagtail.admin.views.generic.permissions import PermissionCheckedMixin
from wagtail.admin.viewsets.model import ModelViewSet

from .models import Payment
from .paypal import ActivityFileError, read_activity_csv

# The uploaded file waits here between preview and confirm, and is removed on
# confirm, cancel, a new upload, or when the session expires.
SESSION_KEY = "wagtail_crm_payments_import"


class UploadForm(forms.Form):
    file = forms.FileField(
        label="PayPal activity CSV",
        help_text="Download it from PayPal: Activity → Statements → Activity download.",
    )


class PaypalImportView(PermissionCheckedMixin, WagtailAdminTemplateMixin, FormView):
    """Upload, preview, then confirm in one transaction.

    Wagtail's CreateView saves a single form; it has no multi-row preview.
    """

    model = Payment
    permission_required = "add"
    form_class = UploadForm
    template_name = "wagtail_crm_payments/import.html"
    page_title = "Import PayPal CSV"
    header_icon = ""
    index_url_name = ""
    add_url_name = ""

    def get_breadcrumbs_items(self):
        return [
            *self.breadcrumbs_items,
            {"url": reverse(self.index_url_name), "label": "Payments"},
            {"url": "", "label": self.page_title},
        ]

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            index_url=reverse(self.index_url_name), **kwargs
        )

    def post(self, request, *args, **kwargs):
        if "confirm" in request.POST:
            return self.confirm()
        if "cancel" in request.POST:
            request.session.pop(SESSION_KEY, None)
            return redirect(self.index_url_name)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        self.request.session.pop(SESSION_KEY, None)
        try:
            text = form.cleaned_data["file"].read().decode("utf-8")
            result = read_activity_csv(text)
        except UnicodeDecodeError:
            form.add_error("file", "Save the file as a UTF-8 CSV and upload it again.")
            return self.form_invalid(form)
        except ActivityFileError as error:
            form.add_error("file", str(error))
            return self.form_invalid(form)
        digest = hashlib.sha256(text.encode()).hexdigest()
        if result.payments:
            self.request.session[SESSION_KEY] = {"text": text, "digest": digest}
        return self.render_to_response(
            self.get_context_data(
                form=form,
                result=result,
                digest=digest,
                filename=form.cleaned_data["file"].name,
            )
        )

    def confirm(self):
        pending = self.request.session.pop(SESSION_KEY, None)
        if not pending or pending["digest"] != self.request.POST.get("digest"):
            messages.error(
                self.request, "This preview is out of date. Upload the file again."
            )
            return redirect(self.add_url_name)
        payments = read_activity_csv(pending["text"]).payments
        try:
            with transaction.atomic():
                Payment.objects.bulk_create(payments)
        except IntegrityError:
            messages.error(
                self.request,
                "Nothing was imported: some of these payments were imported "
                "meanwhile. Upload the file again to see what is new.",
            )
            return redirect(self.add_url_name)
        messages.success(self.request, f"Imported {len(payments)} payments.")
        return redirect(self.index_url_name)


class PaymentIndexView(IndexView):
    add_item_label = "Import PayPal CSV"


class PaymentViewSet(ModelViewSet):
    model = Payment
    icon = "table"
    menu_label = "Payments"
    add_to_admin_menu = True
    url_prefix = "crm/payments"
    url_namespace = "wagtail_crm_payments"
    index_view_class = PaymentIndexView
    index_results_template_name = "wagtail_crm_payments/index_results.html"
    list_display = (
        "occurred_at",
        "name",
        "email",
        "gross",
        "fee",
        "net",
        "currency",
        "status",
        "transaction_id",
    )
    list_filter = ("type",)
    search_fields = ("name", "email", "transaction_id")
    inspect_view_enabled = True
    inspect_view_fields = (
        "occurred_at",
        "name",
        "email",
        "type",
        "event_code",
        "status",
        "currency",
        "gross",
        "fee",
        "net",
        "transaction_id",
        "reference_transaction_id",
    )
    copy_view_enabled = False
    # Imported fields are read-only; #6 adds the donor and charitable amount.
    form_fields: list[str] = []

    @property
    def add_view(self):
        return self.construct_view(PaypalImportView)
