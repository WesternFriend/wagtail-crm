"""Payments imported from a processor's activity export."""

from django.db import models


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

    class Meta:
        ordering = ["-occurred_at", "-pk"]

    def __str__(self):
        return f"{self.transaction_id} {self.name}".strip()
