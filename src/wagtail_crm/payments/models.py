"""Payments imported from a processor's activity export."""

from django.contrib.admin.decorators import display
from django.core.exceptions import ValidationError
from django.db import models

from wagtail_crm.contacts.models import Contact

# Refunds are matched to their original payment in a later slice (#7).
REFUND_NOT_LINKED = (
    "A refund isn't linked to a donor. It is matched to its original payment."
)


class PaymentQuerySet(models.QuerySet):
    def exclude_refunds(self):
        """The counterpart of Payment.is_refund."""
        return self.exclude(gross__lt=0)


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

    def __str__(self):
        return f"{self.transaction_id} {self.name}".strip()

    @property
    def is_refund(self):
        return self.gross < 0

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
        elif amount is not None and amount > self.gross:
            raise ValidationError(
                {
                    "charitable_amount": "Enter no more than the gross amount, "
                    f"{self.gross}."
                }
            )
