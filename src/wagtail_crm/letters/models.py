"""Acknowledgment letters issued to donors for an accepted reconciliation."""

import uuid
from datetime import UTC
from decimal import Decimal

from django.contrib.admin.decorators import display
from django.core.files.storage import storages
from django.db import models
from django.utils import timezone
from wagtail.permission_policies import ModelPermissionPolicy

from wagtail_crm.contacts.models import Contact
from wagtail_crm.payments.models import Reconciliation

DUPLICATE_ORIGINAL = (
    "This donor already has a letter for this period. Issue a correction instead."
)


def letter_storage():
    """Private storage for issued PDFs; never served from MEDIA_URL."""
    return storages["letters"]


def letter_path(letter, filename):
    return f"{uuid.uuid4().hex}.pdf"


class DispatchStatus(models.TextChoices):
    NOT_SENT = "not_sent", "Not sent"
    FAILED = "failed", "Sending failed"
    SENT = "sent", "Sent"
    SUPERSEDED = "superseded", "Superseded"


class LetterQuerySet(models.QuerySet):
    def with_dispatch_status(self):
        """Annotate `dispatch_status`, the one place it is worked out.

        A superseded letter is owed nothing, whatever was recorded; any sent
        dispatch makes a letter sent, even after a later failed attempt.
        """
        dispatches = Dispatch.objects.filter(letter=models.OuterRef("pk"))
        return self.annotate(
            dispatch_status=models.Case(
                models.When(
                    models.Exists(
                        Letter.objects.filter(corrects=models.OuterRef("pk"))
                    ),
                    then=models.Value(DispatchStatus.SUPERSEDED),
                ),
                models.When(
                    models.Exists(dispatches.filter(outcome=Dispatch.Outcome.SENT)),
                    then=models.Value(DispatchStatus.SENT),
                ),
                models.When(
                    models.Exists(dispatches.filter(outcome=Dispatch.Outcome.FAILED)),
                    then=models.Value(DispatchStatus.FAILED),
                ),
                default=models.Value(DispatchStatus.NOT_SENT),
                output_field=models.CharField(),
            )
        )


class Letter(models.Model):
    donor = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="letters")
    reconciliation = models.ForeignKey(
        Reconciliation,
        on_delete=models.PROTECT,
        related_name="letters",
        limit_choices_to={"accepted_at__isnull": False},
        verbose_name="period",
        help_text="Only accepted reconciliations can have letters.",
    )
    corrects = models.OneToOneField(
        "self",
        verbose_name="correction of",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="corrected_by",
    )
    issued_at = models.DateTimeField(default=timezone.now, editable=False)
    # What the PDF shows, kept as issued: later edits to the contact or its
    # payments do not change it.
    values = models.JSONField(editable=False)
    pdf = models.FileField(
        "PDF", storage=letter_storage, upload_to=letter_path, editable=False
    )

    objects = LetterQuerySet.as_manager()

    class Meta:
        ordering = ["-issued_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["donor", "reconciliation"],
                condition=models.Q(corrects__isnull=True),
                name="letter_one_original_per_period",
                violation_error_message=DUPLICATE_ORIGINAL,
            ),
        ]

    def __str__(self):
        return f"{self.values['name']}, {self.reconciliation}"

    # As issued, for the inspect view; the PDF shows the same values.
    @property
    def address(self):
        return self.values["address"]

    @property
    def contributions(self):
        return self.values["lines"]

    @property
    def total(self):
        return self.values["total"]

    @property
    @display(description="dispatch")
    def dispatch(self):
        """The dispatch status label, from with_dispatch_status()."""
        if not hasattr(self, "dispatch_status"):
            self.dispatch_status = (
                Letter.objects.with_dispatch_status()
                .values_list("dispatch_status", flat=True)
                .get(pk=self.pk)
            )
        return DispatchStatus(self.dispatch_status).label

    @property
    @display(description="dispatches")
    def dispatch_records(self):
        return self.dispatches.all()

    @property
    @display(description="corrected by")
    def correction(self):
        """The later letter that corrects this one, if any."""
        return getattr(self, "corrected_by", None)

    @property
    def date(self):
        """The letter's date: issued_at's UTC day, like the period."""
        return self.issued_at.astimezone(UTC).date()


class RefusingPermissionPolicy(ModelPermissionPolicy):
    """Model permissions, except actions refused to everyone, superusers too."""

    def __init__(self, model, refused, **kwargs):
        super().__init__(model, **kwargs)
        self.refused = frozenset(refused)

    def user_has_permission(self, user, action):
        # Checked before has_perm, which is always true for superusers.
        if action in self.refused:
            return False
        return super().user_has_permission(user, action)

    def users_with_any_permission(self, actions):
        actions = [action for action in actions if action not in self.refused]
        if not actions:
            return super().users_with_any_permission([]).none()
        return super().users_with_any_permission(actions)


def contributions(donor, reconciliation):
    """The donor's received payments in the period, with refunds netted in."""
    return (
        reconciliation.payments.exclude_refunds()
        .filter(donor=donor, charitable_amount__isnull=False)
        .with_refunded()
        .order_by("occurred_at", "pk")
    )


def needing_charitable_amount(donor, reconciliation):
    """The donor's rows that block issuing, as reconciliation blockers do."""
    return reconciliation.payments.needing_charitable_amount().filter(donor=donor)


def letter_values(donor, reconciliation, corrects=None, issued_at=None):
    """Everything the PDF shows, as strings, so it can be stored as issued."""
    issued_at = issued_at or timezone.now()
    lines = [
        {
            "date": payment.occurred_at.astimezone(UTC).date().isoformat(),
            "transaction_id": (
                f"Check {payment.transaction_id}"
                if payment.is_check
                else payment.transaction_id
            ),
            "gross": str(payment.gross),
            "amount": str(payment.adjusted_charitable_amount),
            "goods_or_services": str(payment.non_charitable_amount),
        }
        for payment in contributions(donor, reconciliation)
        if payment.adjusted_charitable_amount > 0
    ]
    return {
        "name": donor.display_name,
        "address": donor.postal_address,
        "date": issued_at.astimezone(UTC).date().isoformat(),
        "start": reconciliation.start.isoformat(),
        "end": reconciliation.end.isoformat(),
        "lines": lines,
        "total": str(sum((Decimal(line["amount"]) for line in lines), Decimal("0.00"))),
        "corrects": corrects.values["date"] if corrects else None,
    }


def utc_today():
    """Today in UTC, the same basis as periods and letter dates."""
    return timezone.now().astimezone(UTC).date()


class Dispatch(models.Model):
    """A staff record of one attempt to send a letter; the app sends nothing."""

    class Channel(models.TextChoices):
        POST = "post", "Post"
        EMAIL = "email", "Email"

    class Outcome(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    letter = models.ForeignKey(
        Letter, on_delete=models.PROTECT, related_name="dispatches"
    )
    channel = models.CharField(max_length=8, choices=Channel)
    date = models.DateField(default=utc_today, help_text="In UTC.")
    outcome = models.CharField(max_length=8, choices=Outcome)
    note = models.TextField(blank=True, help_text="Required when sending failed.")

    class Meta:
        ordering = ["-date", "-pk"]
        verbose_name_plural = "dispatches"
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(outcome="failed") | ~models.Q(note=""),
                name="dispatch_failure_has_note",
                violation_error_message="Add a note saying what went wrong.",
            ),
        ]

    def __str__(self):
        return f"{self.get_channel_display()} {self.date}: {self.get_outcome_display()}"
