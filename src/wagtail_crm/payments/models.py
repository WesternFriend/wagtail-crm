"""Payments imported from a processor's activity export."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.admin.decorators import display
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from wagtail_crm.contacts.models import Contact

# PayPal event codes T11xx are refunds and reversals; the importer takes them
# only as debits. A refund names its original payment in reference_transaction_id;
# the link is looked up, not stored, so import order does not matter.
REFUND_EVENT_CODE = "T11"
CENT = Decimal("0.01")
IS_REFUND = models.Q(event_code__startswith=REFUND_EVENT_CODE)
REFUND_NOT_LINKED = (
    "A refund isn't linked to a donor. It is matched to its original payment."
)


def refunds_of(transaction_id):
    """Refunds of a payment; an OuterRef gives a correlated subquery."""
    return Payment.objects.filter(IS_REFUND, reference_transaction_id=transaction_id)


def refunded_total(transaction_id):
    """Sum of refund gross (negative) for a payment, or None if none."""
    return (
        refunds_of(transaction_id)
        .order_by()
        .values("reference_transaction_id")
        .annotate(total=models.Sum("gross"))
        .values("total")
    )


class PaymentQuerySet(models.QuerySet):
    def exclude_refunds(self):
        """The counterpart of Payment.is_refund."""
        return self.exclude(IS_REFUND)

    def refunds(self):
        return self.filter(IS_REFUND)

    def unmatched_refunds(self):
        """Refunds whose original payment has not been imported."""
        originals = Payment.objects.filter(
            transaction_id=models.OuterRef("reference_transaction_id")
        )
        return self.refunds().exclude(models.Exists(originals))

    def with_refunded(self):
        """Annotate `refunded`: the summed refund gross, or None if none."""
        return self.annotate(
            refunded=models.Subquery(
                refunded_total(models.OuterRef("transaction_id")),
                output_field=models.DecimalField(max_digits=12, decimal_places=2),
            )
        )

    def in_period(self, start, end):
        """Rows dated within a reconciliation period (UTC, end exclusive)."""
        return self.filter(occurred_at__gte=start, occurred_at__lt=end)

    def totals(self):
        """Received-payment and refund totals, with PayPal's signs."""
        received = self.exclude_refunds().aggregate(
            count=models.Count("pk"),
            gross=models.Sum("gross"),
            fees=models.Sum("fee"),
            net=models.Sum("net"),
        )
        refunds = self.refunds().aggregate(refunds=models.Sum("gross"))
        amounts = {**received, **refunds}
        return {
            key: value if key == "count" else (value or Decimal(0)).quantize(CENT)
            for key, value in amounts.items()
        }

    def needing_charitable_amount(self):
        return self.exclude_refunds().filter(charitable_amount__isnull=True)


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
        "reference transaction ID",
        max_length=64,
        blank=True,
        editable=False,
        db_index=True,
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

    @property
    def refunds(self):
        return refunds_of(self.transaction_id)

    @property
    def refunded_payment(self):
        """For a refund, its original payment if imported."""
        if not self.is_refund:
            return None
        return Payment.objects.filter(
            transaction_id=self.reference_transaction_id
        ).first()

    @property
    def refunded_amount(self):
        """Summed refund gross, from the list annotation when present."""
        if not hasattr(self, "refunded"):
            self.refunded = (
                Payment.objects.with_refunded()
                .values_list("refunded", flat=True)
                .get(pk=self.pk)
            )
        # SQLite's Sum drops trailing zeros; show cents like the other amounts.
        return None if self.refunded is None else self.refunded.quantize(CENT)

    @property
    @display(description="adjusted charitable amount")
    def adjusted_charitable_amount(self):
        """The charitable amount reduced by refunds, never below 0."""
        if self.charitable_amount is None:
            return None
        return max(
            self.charitable_amount + (self.refunded_amount or 0), Decimal("0.00")
        )

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


def previous_year_start():
    return date(timezone.now().year - 1, 1, 1)


def previous_year_end():
    return date(timezone.now().year - 1, 12, 31)


def money(label, help_text):
    return models.DecimalField(
        label, max_digits=12, decimal_places=2, help_text=help_text
    )


class Reconciliation(models.Model):
    """Staff compare a period's imported totals with PayPal's own report.

    Periods run from UTC midnight on `start` to UTC midnight after `end`;
    time zones only change how dates are displayed. The CRM side is computed
    live; the PayPal side is what staff entered.
    """

    start = models.DateField(default=previous_year_start)
    end = models.DateField(
        default=previous_year_end, help_text="Included in the period."
    )
    paypal_count = models.PositiveIntegerField(
        "PayPal count", help_text="Completed USD payments received."
    )
    paypal_gross = money("PayPal gross", "Completed USD payments received.")
    paypal_fees = money("PayPal fees", "As PayPal shows them, usually negative.")
    paypal_net = money("PayPal net", "Completed USD payments received.")
    paypal_refunds = money(
        "PayPal refunds", "Refund gross as PayPal shows it, usually negative."
    )
    accepted_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-start", "-end"]
        constraints = [
            models.UniqueConstraint(
                fields=["start", "end"],
                name="reconciliation_one_per_period",
                violation_error_message="A reconciliation for this period exists.",
            ),
            models.CheckConstraint(
                condition=models.Q(end__gte=models.F("start")),
                name="reconciliation_end_after_start",
                violation_error_message="The end date must not be before the start.",
            ),
        ]

    def __str__(self):
        return f"{self.start.isoformat()} to {self.end.isoformat()}"

    @property
    def period_range(self):
        """The UTC instants bounding the period: [start 00:00, end + 1 day 00:00)."""
        start = datetime.combine(self.start, time.min, tzinfo=UTC)
        end = datetime.combine(self.end + timedelta(days=1), time.min, tzinfo=UTC)
        return start, end

    @property
    def payments(self):
        return Payment.objects.in_period(*self.period_range)

    def paypal_totals(self):
        return {
            "count": self.paypal_count,
            "gross": self.paypal_gross,
            "fees": self.paypal_fees,
            "net": self.paypal_net,
            "refunds": self.paypal_refunds,
        }

    def blockers(self):
        """What must be resolved before staff can accept the period."""
        payments = self.payments
        return {
            "payments without a charitable amount": (
                payments.needing_charitable_amount()
            ),
            "unmatched refunds": payments.unmatched_refunds(),
        }


def period_is_accepted(start, end):
    """Whether an accepted reconciliation covers the dates (for letters, #9)."""
    return Reconciliation.objects.filter(
        accepted_at__isnull=False, start__lte=start, end__gte=end
    ).exists()
