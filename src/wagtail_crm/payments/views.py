import hashlib
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import django_filters
from django import forms
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.html import format_html, format_html_join
from django.utils.timezone import localtime
from django.views.generic import FormView
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.panels import (
    FieldPanel,
    FieldRowPanel,
    MultiFieldPanel,
    ObjectList,
    Panel,
)
from wagtail.admin.ui.tables import Column
from wagtail.admin.views.generic.base import WagtailAdminTemplateMixin
from wagtail.admin.views.generic.models import (
    CreateView,
    EditView,
    IndexView,
)
from wagtail.admin.views.generic.permissions import PermissionCheckedMixin
from wagtail.admin.widgets import AdminDateInput, HeaderButton
from wagtail.log_actions import log

from wagtail_crm.admin_views import CRMViewSet, InspectView

from .models import REFUND_NOT_LINKED, Payment, Reconciliation, Source
from .paypal import ActivityFileError, read_activity_csv

# Shown in History as "Accepted reconciliation".
ACCEPT_RECONCILIATION = "wagtail_crm_payments.accept_reconciliation"

RECORD_CHECK = "Record check"

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
            self.take_preview()
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

    def take_preview(self):
        """Remove the preview this page showed; a newer one stays in place."""
        pending = self.request.session.get(SESSION_KEY)
        if pending and pending["digest"] == self.request.POST.get("digest"):
            del self.request.session[SESSION_KEY]
            return pending
        return None

    def confirm(self):
        pending = self.take_preview()
        if not pending:
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


class PaymentFilterSet(WagtailFilterSet):
    needs_donor = django_filters.BooleanFilter(
        label="Needs donor", method="filter_needs", field_name="donor"
    )
    needs_charitable_amount = django_filters.BooleanFilter(
        label="Needs charitable amount",
        method="filter_needs",
        field_name="charitable_amount",
    )

    unmatched_refund = django_filters.BooleanFilter(
        label="Unmatched refund", method="filter_unmatched_refund"
    )

    class Meta:
        model = Payment
        fields = ["source", "type"]

    def filter_unmatched_refund(self, queryset, name, value):
        if value is None:
            return queryset
        unmatched = queryset.unmatched_refunds()
        return unmatched if value else queryset.exclude(pk__in=unmatched)

    def filter_needs(self, queryset, name, value):
        if value is None:
            return queryset
        blank = {f"{name}__isnull": True}
        received = queryset.exclude_refunds()
        return received.filter(**blank) if value else received.exclude(**blank)


class PaymentIndexView(IndexView):
    add_item_label = "Import PayPal CSV"

    def get_base_queryset(self):
        return super().get_base_queryset().with_refunded()

    @cached_property
    def header_buttons(self):
        buttons = super().header_buttons
        if self.add_url:  # The same add permission as importing.
            buttons.append(
                HeaderButton(
                    RECORD_CHECK,
                    url=reverse("wagtail_crm_payments:add_check"),
                    icon_name="plus",
                )
            )
        return buttons


class CheckForm(WagtailAdminModelForm):
    """A mailed check. Its facts are form fields, not model fields, because
    they are editable=False: PayPal's imported facts stay read-only."""

    received = forms.DateField(label="Date received", widget=AdminDateInput)
    check_number = forms.CharField(label="Check number", max_length=64)
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Entered together, so a check never waits for its donor or amount.
        self.fields["donor"].required = True
        self.fields["charitable_amount"].required = True
        check = self.instance
        if check.pk:
            self.initial.setdefault(
                "received", check.occurred_at.astimezone(UTC).date()
            )
            self.initial.setdefault("check_number", check.transaction_id)
            self.initial.setdefault("amount", check.gross)

    def clean(self):
        cleaned = super().clean()
        # Set before _post_clean, so Payment.clean() checks the charitable
        # amount against this gross.
        check = self.instance
        check.source = Source.CHECK
        check.type = "Check"
        check.status = "Completed"
        check.currency = "USD"
        check.event_code = ""  # Never T11xx, so never a refund.
        if received := cleaned.get("received"):
            # Noon UTC is the same UTC day for periods and shows the same
            # date in time zones from UTC-11 to UTC+11.
            check.occurred_at = datetime.combine(received, time(12), tzinfo=UTC)
        if number := cleaned.get("check_number"):
            check.transaction_id = number
        if (amount := cleaned.get("amount")) is not None:
            check.gross = check.net = amount
            check.fee = Decimal("0.00")
        return cleaned


CHECK_PANEL = ObjectList(
    [
        FieldRowPanel(
            [FieldPanel("received"), FieldPanel("check_number"), FieldPanel("amount")]
        ),
        FieldPanel("donor"),
        FieldPanel("charitable_amount"),
    ],
    base_form_class=CheckForm,
).bind_to_model(Payment)


class CheckCreateView(CreateView):
    page_title = RECORD_CHECK
    submit_button_label = RECORD_CHECK
    success_message = "Recorded %(object)s."

    def get_page_subtitle(self):
        return "Mailed check"

    def get_add_url(self):
        # The form posts here, not to the viewset's add view (the import).
        return reverse("wagtail_crm_payments:add_check")

    def get_success_buttons(self):
        return []


class PaymentEditView(EditView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        if self.panel is CHECK_PANEL:
            self.form_class = CHECK_PANEL.get_form_class()

    def get_panel(self):
        # Wagtail picks the panel in setup(), before its permission check and
        # before loading the object. Read only the source here, so a missing
        # payment is still refused, not reported as missing.
        pk = str(self.kwargs.get("pk", ""))
        source = (
            Payment.objects.filter(pk=pk).values_list("source", flat=True).first()
            if pk.isdecimal()
            else None
        )
        return CHECK_PANEL if source == Source.CHECK else super().get_panel()


def refunds_html(payment, action):
    """A payment's refunds, or a refund's original, linked to `action` pages."""
    if payment.is_refund:
        original = payment.refunded_payment
        if original is None:
            return format_html(
                "Original payment {} is not imported. {}",
                payment.reference_transaction_id,
                REFUND_NOT_LINKED,
            )
        return format_html(
            'Refund of <a href="{}">{}</a>. {}',
            reverse(f"wagtail_crm_payments:{action}", args=[original.pk]),
            original,
            REFUND_NOT_LINKED,
        )
    refunds = list(payment.refunds)
    if not refunds:
        return "No refunds"
    return format_html_join(
        ", ",
        '<a href="{}">{} on {}</a>',
        (
            (
                reverse(f"wagtail_crm_payments:{action}", args=[refund.pk]),
                refund.gross,
                date_format(localtime(refund.occurred_at)),
            )
            for refund in refunds
        ),
    )


class RefundsPanel(Panel):
    """Read-only refunds; FieldPanel(read_only) only shows model fields."""

    class BoundPanel(Panel.BoundPanel):
        template_name = "wagtail_crm_payments/refunds_panel.html"

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.heading = "Refund" if self.instance.is_refund else "Refunds"

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            context["refunds"] = refunds_html(self.instance, "edit")
            context["payment"] = self.instance
            return context


# PayPal facts a mailed check doesn't have.
NOT_ON_CHECKS = {
    "name",
    "email",
    "event_code",
    "status",
    "currency",
    "fee",
    "net",
    "reference_transaction_id",
    "refunds",
    "adjusted_charitable_amount",
}


class PaymentInspectView(InspectView):
    def get_fields_context(self):
        # Fields are listed before the object loads; filter them here.
        if self.object.is_check:
            return [
                self.get_context_for_field(name)
                for name in self.get_fields()
                if name not in NOT_ON_CHECKS
            ]
        return super().get_fields_context()

    def get_field_label(self, field_name, field):
        if field_name == "transaction_id" and self.object.is_check:
            return "Check number"
        return super().get_field_label(field_name, field)

    def get_refunds_display_value(self):
        return refunds_html(self.object, "inspect")


class PaymentViewSet(CRMViewSet):
    model = Payment
    icon = "table"
    menu_label = "Payments"
    add_to_admin_menu = True
    url_prefix = "crm/payments"
    url_namespace = "wagtail_crm_payments"
    index_view_class = PaymentIndexView
    edit_view_class = PaymentEditView
    index_results_template_name = "wagtail_crm_payments/index_results.html"
    list_display = (
        "occurred_at",
        "source",
        Column("transaction_id", label="Transaction ID or check number"),
        "name",
        "email",
        "donor",
        "gross",
        "charitable_amount",
        "non_charitable_amount",
        Column("refunded_amount", label="Refunded"),
        "fee",
        "status",
    )
    filterset_class = PaymentFilterSet
    search_fields = ("name", "email", "transaction_id")
    inspect_view_enabled = True
    inspect_view_fields = (
        "source",
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
        "donor",
        "charitable_amount",
        "non_charitable_amount",
        "refunds",
        "adjusted_charitable_amount",
    )
    inspect_view_class = PaymentInspectView
    copy_view_enabled = False
    panels = (
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("name", read_only=True),
                        FieldPanel("email", read_only=True),
                    ]
                ),
                FieldRowPanel(
                    [
                        FieldPanel("gross", read_only=True),
                        FieldPanel("fee", read_only=True),
                        FieldPanel("net", read_only=True),
                    ]
                ),
                FieldRowPanel(
                    [
                        FieldPanel("occurred_at", read_only=True),
                        FieldPanel("type", read_only=True),
                        FieldPanel("transaction_id", read_only=True),
                    ]
                ),
            ],
            heading="From PayPal",
        ),
        RefundsPanel(),
        FieldPanel("donor"),
        FieldPanel("charitable_amount"),
    )

    @property
    def add_view(self):
        return self.construct_view(PaypalImportView)

    @property
    def add_check_view(self):
        return self.construct_view(
            CheckCreateView,
            **self.get_add_view_kwargs(
                panel=CHECK_PANEL, form_class=CHECK_PANEL.get_form_class()
            ),
        )

    def get_urlpatterns(self):
        return [
            *super().get_urlpatterns(),
            path("checks/new/", self.add_check_view, name="add_check"),
        ]


class ReconciliationForm(WagtailAdminModelForm):
    accept = forms.BooleanField(
        label="Accept this reconciliation",
        required=False,
        help_text="Records who accepted it and when, with the totals shown. "
        "An accepted reconciliation cannot be changed.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            # Staff see the comparison before accepting it.
            del self.fields["accept"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("accept"):
            # Compare the dates being saved, not the stored ones.
            period = Reconciliation(
                start=cleaned.get("start", self.instance.start),
                end=cleaned.get("end", self.instance.end),
            )
            reasons = [
                f"{rows.count()} {label}"
                for label, rows in period.blockers().items()
                if rows.exists()
            ]
            if reasons:
                self.add_error(
                    "accept",
                    "Resolve these payments in the period first: "
                    + ", ".join(reasons)
                    + ".",
                )
        return cleaned


COMPARED = (
    ("count", "Received payments (completed, USD)"),
    ("gross", "Gross"),
    ("fees", "Fees"),
    ("net", "Net"),
    ("refunds", "Refunds"),
)


def comparison(reconciliation):
    """CRM, PayPal and difference for each total."""
    crm = reconciliation.payments.paypal().totals()
    paypal = reconciliation.paypal_totals()
    rows = []
    for key, label in COMPARED:
        entered = paypal[key]
        difference = None if entered is None else crm[key] - entered
        rows.append((label, crm[key], entered, difference))
    return crm, rows


class ReconciliationPanel(Panel):
    """The live comparison; FieldPanel(read_only) only shows model fields."""

    class BoundPanel(Panel.BoundPanel):
        template_name = "wagtail_crm_payments/reconciliation_panel.html"

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            reconciliation = self.instance
            start, end = reconciliation.period_range
            context.update(
                reconciliation=reconciliation,
                first=start,
                last=end - timedelta(minutes=1),
                rows=comparison(reconciliation)[1],
                checks=reconciliation.check_totals(),
                check_rows=[
                    (reverse("wagtail_crm_payments:edit", args=[p.pk]), p)
                    for p in reconciliation.payments.checks()
                    .select_related("donor")
                    .order_by("occurred_at")
                ],
                # Listed here: the payment list has no UTC period filter.
                blockers=[
                    (
                        label,
                        [
                            (reverse("wagtail_crm_payments:edit", args=[p.pk]), p)
                            for p in rows
                        ],
                    )
                    for label, rows in reconciliation.blockers().items()
                ],
            )
            return context


class ReconciliationEditView(EditView):
    def post(self, request, *args, **kwargs):
        if self.get_object().accepted_at:
            # Reopening an accepted reconciliation is deferred (AC trim).
            messages.error(request, "This reconciliation is accepted.")
            return redirect(request.path)
        return super().post(request, *args, **kwargs)

    def save_instance(self):
        instance = super().save_instance()
        if self.form.cleaned_data.get("accept"):
            instance.accepted_at = timezone.now()
            instance.save(update_fields=["accepted_at"])
            crm, _ = comparison(instance)
            log(
                instance=instance,
                action=ACCEPT_RECONCILIATION,
                data={
                    "crm": {key: str(value) for key, value in crm.items()},
                    "paypal": {
                        key: str(value)
                        for key, value in instance.paypal_totals().items()
                    },
                    "checks": {
                        key: str(value)
                        for key, value in instance.check_totals().items()
                    },
                },
            )
        return instance


class ReconciliationViewSet(CRMViewSet):
    model = Reconciliation
    icon = "tasks"
    menu_label = "Reconciliations"
    add_to_admin_menu = True
    url_prefix = "crm/reconciliations"
    url_namespace = "wagtail_crm_reconciliations"
    edit_view_class = ReconciliationEditView
    list_display = ("__str__", "accepted_at")
    copy_view_enabled = False
    edit_handler = ObjectList(
        [
            FieldRowPanel([FieldPanel("start"), FieldPanel("end")]),
            ReconciliationPanel(heading="Comparison"),
            MultiFieldPanel(
                [
                    FieldPanel("paypal_count"),
                    FieldRowPanel(
                        [
                            FieldPanel("paypal_gross"),
                            FieldPanel("paypal_fees"),
                            FieldPanel("paypal_net"),
                        ]
                    ),
                    FieldPanel("paypal_refunds"),
                ],
                heading="From PayPal's report",
            ),
            FieldPanel("accept"),
        ],
        base_form_class=ReconciliationForm,
    )
