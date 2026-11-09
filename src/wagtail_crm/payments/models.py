"""Payments imported from a processor's activity export."""

from django.contrib.admin.decorators import display
from django.core.exceptions import ValidationError
from django.db import models

from wagtail_crm.contacts.models import Contact

# PayPal event codes T11xx are refunds and reversals; the importer takes them
# only as debits. Refunds are matched to their original payment later (#7).
REFUND_EVENT_CODE = "T11"
IS_REFUND = models.Q(event_code__startswith=REFUND_EVENT_CODE)
REFUND_NOT_LINKED = (
    "A refund isn't linked to a donor. It is matched to its original payment."
)


class PaymentQuerySet(models.QuerySet):
    def exclude_refunds(self):
        """The counterpart of Payment.is_refund."""
        return self.exclude(IS_REFUND)


class Payment(models.Model):
    # Imported source facts are not editable through any form.
    transaction_id = models.CharField(
        "transaction ID", max_length=64, unique=True, editable=False
    )
    occurred_at = models.DateTimeField("date", editable=False)
    name = models.CharField(max_length=255, blank=True, editable=False)
    email = models.EmailField(blank=True, editable=False)
    type = models.CharField(max_length=255, editable=False)
    event_code = models.CharField(max_length=8, editable=False)
    status = models.CharField(max_length=32, editable=False)
    currency = models.CharField(max_length=3, editable=False)
    gross = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    fee = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    net = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    reference_transaction_id = models.CharField(
        "reference transaction ID", max_length=64, blank=True, editable=False
    )

    # Staff decisions. A contact with payments cannot be deleted.
    donor = models.ForeignKey(
        Contact,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    charitable_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="The part of the gross amount that is a gift. "
        "Enter 0 if none of it is.",
    )

    objects = PaymentQuerySet.as_manager()

    class Meta:
        ordering = ["-occurred_at", "-pk"]
        # clean() gives staff the field errors; these hold on every write.
        constraints = [
            models.CheckConstraint(
                condition=~IS_REFUND
                | models.Q(donor__isnull=True, charitable_amount__isnull=True),
                name="payment_refund_not_linked",
                violation_error_message=REFUND_NOT_LINKED,
            ),
            models.CheckConstraint(
                condition=models.Q(charitable_amount__isnull=True)
                | models.Q(
                    charitable_amount__gte=0,
                    charitable_amount__lte=models.F("gross"),
                ),
                name="payment_charitable_amount_within_gross",
                violation_error_message="The charitable amount must be from 0 "
                "to the gross amount.",
            ),
        ]

    def __str__(self):
        return f"{self.transaction_id} {self.name}".strip()

    @property
    def is_refund(self):
        return self.event_code.startswith(REFUND_EVENT_CODE)

    @property
    @display(description="non-charitable amount")
    def non_charitable_amount(self):
        if self.charitable_amount is None:
            return None
        return self.gross - self.charitable_amount

    def clean(self):
        super().clean()
        amount = self.charitable_amount
        if self.is_refund:
            errors = {}
            if self.donor_id is not None:
                errors["donor"] = REFUND_NOT_LINKED
            if amount is not None:
                errors["charitable_amount"] = REFUND_NOT_LINKED
            if errors:
                raise ValidationError(errors)
        elif amount is not None and amount < 0:
            raise ValidationError({"charitable_amount": "Enter 0 or more."})
        elif amount is not None and self.gross is not None and amount > self.gross:
            raise ValidationError(
                {
                    "charitable_amount": "Enter no more than the gross amount, "
                    f"{self.gross}."
                }
            )
