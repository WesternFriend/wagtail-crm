"""Read a PayPal Activity Download CSV into unsaved payments.

Columns follow https://developer.paypal.com/reports/activity-download/.
"""

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

from django.utils.text import capfirst

from .models import Payment

EVENT_CODE = "Transaction Event Code"
BALANCE_IMPACT = "Balance Impact"

REQUIRED_COLUMNS = (
    "Date",
    "Time",
    "TimeZone",
    "Name",
    "Type",
    "Status",
    "Currency",
    "Gross",
    "Fee",
    "Net",
    "From Email Address",
    "To Email Address",
    "Transaction ID",
    "Reference Txn ID",
    EVENT_CODE,
    BALANCE_IMPACT,
)

# Abbreviations a US PayPal account's export uses; others are skipped with a reason.
TIME_ZONES = {
    name: timezone(timedelta(hours=hours), name)
    for name, hours in {
        "UTC": 0,
        "GMT": 0,
        "EST": -5,
        "EDT": -4,
        "CST": -6,
        "CDT": -5,
        "MST": -7,
        "MDT": -6,
        "PST": -8,
        "PDT": -7,
    }.items()
}

AMOUNT = re.compile(r"-?(\d{1,3}(,\d{3})+|\d+)(\.\d{1,2})?")
# Payment amounts are DecimalField(max_digits=12, decimal_places=2).
AMOUNT_LIMIT = Decimal("1e10")


class ActivityFileError(ValueError):
    """The upload is not a readable PayPal activity CSV."""


@dataclass(frozen=True)
class SkippedRow:
    row: int
    transaction_id: str
    name: str
    reason: str


@dataclass
class ActivityFile:
    payments: list[Payment] = field(default_factory=list)
    skipped: list[SkippedRow] = field(default_factory=list)


def read_activity_csv(text: str) -> ActivityFile:
    """Return the payments to import and the rows skipped, each with a reason."""
    reader = csv.DictReader(io.StringIO(text.removeprefix("\ufeff"), newline=""))
    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or ())]
    if missing:
        msg = "This is not a PayPal activity CSV. Missing columns: " + ", ".join(
            missing
        )
        raise ActivityFileError(msg)
    try:
        rows = list(enumerate(reader, start=2))
    except csv.Error as error:
        msg = f"The CSV could not be read: {error}"
        raise ActivityFileError(msg) from error

    existing = set(Payment.objects.values_list("transaction_id", flat=True))
    result = ActivityFile()
    first_seen: dict[str, int] = {}
    for number, cells in rows:
        # A short row leaves missing cells as None; extra cells are ignored.
        row = {key: value or "" for key, value in cells.items() if key is not None}
        transaction_id = row["Transaction ID"].strip()
        if not transaction_id:
            outcome: Payment | str = "Missing transaction ID"
        elif transaction_id in first_seen:
            outcome = f"Duplicate of row {first_seen[transaction_id]}"
        elif transaction_id in existing:
            outcome = "Already imported"
        else:
            outcome = _payment(row, transaction_id)
        if isinstance(outcome, Payment):
            # Only imported rows count: PayPal reuses an ID on related rows,
            # such as holds, that are skipped as unsupported.
            first_seen[transaction_id] = number
            result.payments.append(outcome)
        else:
            result.skipped.append(
                SkippedRow(number, transaction_id, row["Name"].strip(), outcome)
            )
    return result


def _unsupported(row: dict[str, str]) -> str | None:
    """Return why a row is not an imported kind of payment, if it is not."""
    status = row["Status"].strip()
    if status != "Completed":
        return f"Status {status or '(blank)'} is not imported"
    code = row[EVENT_CODE].strip()
    impact = row[BALANCE_IMPACT].strip()
    if code.startswith("T00") and impact == "Debit":
        return f"Outgoing payment ({code})"
    received = code.startswith("T00") and impact == "Credit"
    refunded = code.startswith("T11") and impact == "Debit"
    if not (received or refunded):
        return f"Unsupported type: {row['Type'].strip()} ({code or 'no code'})"
    currency = row["Currency"].strip()
    if currency != "USD":
        return f"Currency {currency or '(blank)'} is not supported"
    return None


def _payment(row: dict[str, str], transaction_id: str) -> Payment | str:
    """Return the payment for a row, or the reason it is skipped."""
    reason = _unsupported(row)
    if reason:
        return reason

    amounts = _amounts(row)
    if isinstance(amounts, str):
        return amounts

    zone = TIME_ZONES.get(row["TimeZone"].strip())
    if zone is None:
        return f"Unknown time zone: {row['TimeZone'].strip() or '(blank)'}"
    stamp = f"{row['Date'].strip()} {row['Time'].strip()}"
    try:
        # Parse aware (Ruff DTZ007), then apply the row's zone below.
        occurred_at = datetime.strptime(f"{stamp} +0000", "%m/%d/%Y %H:%M:%S %z")
    except ValueError:
        return f"Malformed date or time: {stamp}"

    received = row[BALANCE_IMPACT].strip() == "Credit"
    payment = Payment(
        transaction_id=transaction_id,
        occurred_at=occurred_at.replace(tzinfo=zone).astimezone(UTC),
        name=row["Name"].strip(),
        # The other party: the sender of money received, the recipient of a refund.
        email=row["From Email Address" if received else "To Email Address"].strip(),
        type=row["Type"].strip(),
        event_code=row[EVENT_CODE].strip(),
        status=row["Status"].strip(),
        currency=row["Currency"].strip(),
        gross=amounts["Gross"],
        fee=amounts["Fee"],
        net=amounts["Net"],
        reference_transaction_id=row["Reference Txn ID"].strip(),
    )
    return _too_long(payment) or payment


def _amounts(row: dict[str, str]) -> dict[str, Decimal] | str:
    """Parse Gross, Fee and Net, or return why the row is skipped."""
    amounts = {}
    for column in ("Gross", "Fee", "Net"):
        value = row[column].strip()
        if not AMOUNT.fullmatch(value):
            return f"Malformed {column}: {value or '(blank)'}"
        amount = Decimal(value.replace(",", ""))
        if abs(amount) >= AMOUNT_LIMIT:
            return f"{column} is too large: {value}"
        amounts[column] = amount
    # Money received is positive and refunds negative; a positive refund
    # would increase the gift it adjusts.
    impact = row[BALANCE_IMPACT].strip()
    if (amounts["Gross"] > 0) != (impact == "Credit"):
        return f"Gross {row['Gross'].strip()} does not match {impact}"
    return amounts


def _too_long(payment: Payment) -> str | None:
    """Name a text value that would not fit its database column."""
    for model_field in Payment._meta.concrete_fields:
        value = getattr(payment, model_field.attname)
        limit = getattr(model_field, "max_length", None)
        if isinstance(value, str) and limit and len(value) > limit:
            return f"{capfirst(model_field.verbose_name)} is too long"
    return None
