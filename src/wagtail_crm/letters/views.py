from django import forms
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import linebreaksbr
from django.urls import path, reverse
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.utils.functional import cached_property
from django.utils.html import format_html, format_html_join
from django.views.generic import View
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.panels import FieldPanel, ObjectList, Panel
from wagtail.admin.ui.tables import Column
from wagtail.admin.views.generic.models import CreateView, IndexView, InspectView
from wagtail.admin.views.generic.permissions import PermissionCheckedMixin
from wagtail.admin.viewsets.model import ModelViewSet
from wagtail.admin.widgets import HeaderButton
from wagtail.log_actions import log

from .models import Letter, letter_values, needing_charitable_amount
from .pdf import render_pdf

ISSUE = "Issue letter"
# Shown in History as "Issued letter".
ISSUE_LETTER = "wagtail_crm_letters.issue"


def private(response):
    """Letters hold donor data: no shared cache may keep them."""
    patch_cache_control(response, private=True, no_store=True)
    return response


class LetterForm(WagtailAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["corrects"].widget = forms.HiddenInput()
        pk = (
            self.data.get("corrects") if self.is_bound else self.initial.get("corrects")
        )
        # The view answers 404 for an id that names no letter.
        self.correcting = Letter.objects.filter(pk=pk).first() if pk else None
        if self.correcting:
            # A correction keeps the original's donor and period.
            del self.fields["donor"]
            del self.fields["reconciliation"]
            self.instance.donor = self.correcting.donor
            self.instance.reconciliation = self.correcting.reconciliation

    def clean(self):
        cleaned = super().clean()
        later = self.correcting and self.correcting.correction
        if later:
            # Another tab, or an old link, already corrected this letter.
            self.add_error(
                None,
                f"This letter was already corrected by the letter dated {later.date}. "
                "Correct that letter instead.",
            )
            return cleaned
        donor, reconciliation = (
            (self.correcting.donor, self.correcting.reconciliation)
            if self.correcting
            else (cleaned.get("donor"), cleaned.get("reconciliation"))
        )
        if donor is not None and reconciliation is not None:
            self.check_contributions(donor, reconciliation)
        return cleaned

    def check_contributions(self, donor, reconciliation):
        """Refuse a letter with undecided payments or nothing to acknowledge."""
        blocking = needing_charitable_amount(donor, reconciliation)
        if blocking.exists():
            listed = ", ".join(str(payment) for payment in blocking)
            self.add_error(
                None, f"Record a charitable amount for these payments first: {listed}."
            )
            return
        # Issuing saves exactly these values, so what was checked is what is kept.
        self.issued_at = timezone.now()
        self.values = letter_values(
            donor, reconciliation, self.correcting, self.issued_at
        )
        if not self.values["lines"]:
            self.add_error(None, "This donor has no contributions in this period.")


class CorrectionPanel(Panel):
    """Which letter a correction replaces; shown only when correcting."""

    class BoundPanel(Panel.BoundPanel):
        template_name = "wagtail_crm_letters/correction_panel.html"

        def is_shown(self):
            return self.form.correcting is not None

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            context["correcting"] = self.form.correcting
            return context


class PreviewPanel(Panel):
    """The preview button, with the hidden field naming a corrected letter."""

    def get_form_options(self):
        return {"fields": ["corrects"]}

    class BoundPanel(Panel.BoundPanel):
        template_name = "wagtail_crm_letters/preview_panel.html"


def corrects_label(letter):
    """Name the earlier letter by its date: both share the donor and period."""
    return f"Letter dated {letter.corrects.date}" if letter.corrects else ""


class LetterIndexView(IndexView):
    add_item_label = ISSUE


class LetterCreateView(CreateView):
    inspect_url_name = None
    page_title = ISSUE
    submit_button_label = ISSUE
    success_message = "Issued %(object)s."

    # get and post run after the permission check in dispatch.
    def get(self, request, *args, **kwargs):
        self.require_letter(request.GET.get("corrects"))
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.require_letter(request.POST.get("corrects"))
        return super().post(request, *args, **kwargs)

    @staticmethod
    def require_letter(pk):
        """A correction must name an existing letter."""
        if pk and not (pk.isdecimal() and Letter.objects.filter(pk=pk).exists()):
            raise Http404

    def get_initial(self):
        return {**super().get_initial(), "corrects": self.request.GET.get("corrects")}

    def get_error_message(self):
        if "preview" in self.request.POST:
            return "The letter can't be previewed or issued yet."
        return super().get_error_message()

    def form_valid(self, form):
        if "preview" in self.request.POST:
            response = HttpResponse(
                render_pdf(form.values), content_type="application/pdf"
            )
            response["Content-Disposition"] = 'inline; filename="preview.pdf"'
            return private(response)
        return super().form_valid(form)

    def save_instance(self):
        letter = self.form.instance
        letter.issued_at = self.form.issued_at
        letter.values = self.form.values
        letter.pdf.save(
            "letter.pdf", ContentFile(render_pdf(letter.values)), save=False
        )
        # One History entry, "Issued letter", instead of "Created" as well.
        self.action_class(
            letter,
            user=self.request.user,
            form=self.form,
            sort_order_field=self.sort_order_field,
            log_action=False,
        ).execute(skip_permission_checks=True)
        log(
            instance=letter,
            action=ISSUE_LETTER,
            data={"total": letter.values["total"], "corrects": letter.corrects_id},
        )
        return letter

    def get_success_url(self):
        return reverse(self.inspect_url_name, args=[self.object.pk])

    def get_success_buttons(self):
        return []


class LetterInspectView(InspectView):
    pdf_url_name = None
    add_url_name = None
    inspect_url_name = None

    @cached_property
    def header_buttons(self):
        letter = self.object
        buttons = [
            HeaderButton(
                "Download PDF",
                url=reverse(self.pdf_url_name, args=[letter.pk]),
                icon_name="doc-full",
            )
        ]
        if letter.correction is None and self.permission_policy.user_has_permission(
            self.request.user, "add"
        ):
            buttons.append(
                HeaderButton(
                    "Issue correction",
                    url=reverse(self.add_url_name) + f"?corrects={letter.pk}",
                    icon_name="edit",
                )
            )
        return buttons

    def get_corrects_display_value(self):
        return self.link(self.object.corrects) or "Not a correction"

    def get_correction_display_value(self):
        later = self.object.correction
        if later is None:
            return "Not corrected"
        return format_html("Superseded by {}", self.link(later))

    def get_contributions_display_value(self):
        return format_html_join(
            "",
            "<div>{} {}: {} charitable, {} for goods or services</div>",
            (
                (
                    line["date"],
                    line["transaction_id"],
                    line["amount"],
                    line["goods_or_services"],
                )
                for line in self.object.values["lines"]
            ),
        )

    def get_address_display_value(self):
        return linebreaksbr(self.object.values["address"]) or "No address"

    def link(self, letter):
        if letter is None:
            return None
        return format_html(
            '<a href="{}">the letter dated {}</a>',
            reverse(self.inspect_url_name, args=[letter.pk]),
            letter.date.isoformat(),
        )


class LetterPDFView(PermissionCheckedMixin, View):
    # Without a model the mixin finds no permission policy and lets
    # everyone through; construct_view only passes attributes the class has.
    model = Letter
    permission_required = "view"

    def get(self, request, pk):
        letter = get_object_or_404(Letter, pk=pk)
        response = FileResponse(
            letter.pdf.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"letter-{letter.pk}.pdf",
        )
        return private(response)


class LetterViewSet(ModelViewSet):
    model = Letter
    icon = "mail"
    menu_label = "Letters"
    add_to_admin_menu = True
    url_prefix = "crm/letters"
    url_namespace = "wagtail_crm_letters"
    index_view_class = LetterIndexView
    add_view_class = LetterCreateView
    inspect_view_enabled = True
    inspect_view_class = LetterInspectView
    copy_view_enabled = False
    list_display = (
        "__str__",
        "issued_at",
        Column("corrects", label="Correction of", accessor=corrects_label),
    )
    inspect_view_fields = (
        "donor",
        "address",
        "reconciliation",
        "issued_at",
        "contributions",
        "total",
        "corrects",
        "correction",
    )
    edit_handler = ObjectList(
        [
            CorrectionPanel(heading="Correction"),
            FieldPanel("donor"),
            FieldPanel("reconciliation"),
            PreviewPanel(heading="Preview"),
        ],
        base_form_class=LetterForm,
    )

    def get_inspect_view_kwargs(self, **kwargs):
        return super().get_inspect_view_kwargs(
            pdf_url_name=self.get_url_name("pdf"),
            add_url_name=self.get_url_name("add"),
            **kwargs,
        )

    def get_add_view_kwargs(self, **kwargs):
        return super().get_add_view_kwargs(
            inspect_url_name=self.get_url_name("inspect"), **kwargs
        )

    @property
    def pdf_view(self):
        return self.construct_view(LetterPDFView)

    def get_urlpatterns(self):
        return [
            *super().get_urlpatterns(),
            path("pdf/<int:pk>/", self.pdf_view, name="pdf"),
        ]
