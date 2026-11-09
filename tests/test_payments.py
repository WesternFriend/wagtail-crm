"""PayPal activity import: expected values are written by hand from the fixtures."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from wagtail_crm.payments.models import Payment
from wagtail_crm.payments.paypal import ActivityFileError, read_activity_csv

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).parent / "fixtures" / "paypal"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def imported(result):
    return [
        (
            p.transaction_id,
            p.occurred_at,
            p.name,
            p.email,
            p.type,
            p.event_code,
            p.status,
            p.currency,
            p.gross,
            p.fee,
            p.net,
            p.reference_transaction_id,
        )
        for p in result.payments
    ]


def test_activity_file_imports_received_usd_payments_and_refunds():
    result = read_activity_csv(fixture("activity.csv"))
    D = Decimal  # noqa: N806
    assert imported(result) == [
        ("1AA00000000000001", datetime(2026, 1, 15, 17, 30, tzinfo=UTC),
         "Avery Example", "avery@example.org", "Donation Payment", "T0013",
         "Completed", "USD", D("100.00"), D("0.00"), D("100.00"), ""),
        ("1AA00000000000002", datetime(2026, 2, 3, 22, 5, 10, tzinfo=UTC),
         "Blake Sample", "blake@example.org", "Donation Payment", "T0013",
         "Completed", "USD", D("50.00"), D("-1.95"), D("48.05"), ""),
        ("1AA00000000000003", datetime(2026, 3, 20, 18, 0, tzinfo=UTC),
         "Casey Patron", "casey@example.org", "Subscription Payment", "T0002",
         "Completed", "USD", D("90.00"), D("-2.91"), D("87.09"), ""),
        ("1AA00000000000004", datetime(2026, 4, 2, 23, 45, tzinfo=UTC),
         "Drew Reader", "drew@example.org", "Website Payment", "T0006",
         "Completed", "USD", D("20.00"), D("-0.88"), D("19.12"), ""),
        ("1AA00000000000005", datetime(2026, 4, 9, 17, 15, tzinfo=UTC),
         "Drew Reader", "drew@example.org", "Payment Refund", "T1107",
         "Completed", "USD", D("-20.00"), D("0.59"), D("-19.41"),
         "1AA00000000000004"),
        ("1AA00000000000012", datetime(2027, 1, 1, 7, 59, 59, tzinfo=UTC),
         "Jordan Major", "jordan@example.org", "Donation Payment", "T0013",
         "Completed", "USD", D("1250.00"), D("-36.55"), D("1213.45"), ""),
    ]  # fmt: skip


def test_byte_order_mark_from_excel_or_paypal_is_ignored():
    with_bom = read_activity_csv("\ufeff" + fixture("activity.csv"))
    assert len(with_bom.payments) == 6


def test_activity_file_lists_every_skipped_row_with_its_reason():
    result = read_activity_csv(fixture("activity.csv"))
    assert [(s.row, s.transaction_id, s.reason) for s in result.skipped] == [
        (7, "1AA00000000000006", "Status Pending is not imported"),
        (8, "1AA00000000000007", "Status Denied is not imported"),
        (9, "1AA00000000000008", "Currency EUR is not supported"),
        (10, "1AA00000000000009", "Malformed Gross: 12,3x"),
        (11, "1AA00000000000001", "Duplicate of row 2"),
        (12, "1AA00000000000010", "Unsupported type: General Withdrawal (T0400)"),
        (13, "1AA00000000000011", "Outgoing payment (T0006)"),
    ]
    assert len(result.payments) + len(result.skipped) == 13


def test_overlapping_file_adds_only_new_transactions():
    Payment.objects.bulk_create(read_activity_csv(fixture("activity.csv")).payments)
    result = read_activity_csv(fixture("activity-overlap.csv"))
    assert [p.transaction_id for p in result.payments] == [
        "1AA00000000000006",
        "1AA00000000000013",
    ]
    assert [(s.transaction_id, s.reason) for s in result.skipped] == [
        ("1AA00000000000001", "Already imported"),
        ("1AA00000000000002", "Already imported"),
    ]


def test_repeated_file_has_nothing_new():
    Payment.objects.bulk_create(read_activity_csv(fixture("activity.csv")).payments)
    result = read_activity_csv(fixture("activity.csv"))
    assert result.payments == []
    # The six imported rows plus the in-file copy of the first one.
    assert sum(s.reason == "Already imported" for s in result.skipped) == 7


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (("TimeZone", "CET"), "Unknown time zone: CET"),
        (("Date", "2026-01-15"), "Malformed date or time: 2026-01-15 09:30:00"),
        (("Fee", "1.234"), "Malformed Fee: 1.234"),
        (("Net", ""), "Malformed Net: (blank)"),
        (("Transaction ID", ""), "Missing transaction ID"),
    ],
)
def test_unreadable_values_skip_the_row(change, reason):
    header, first, *_ = fixture("activity.csv").splitlines()
    columns = header.replace('"', "").split(",")
    values = first.replace('"', "").split(",")
    values[columns.index(change[0])] = change[1]
    text = header + "\n" + ",".join(f'"{v}"' for v in values) + "\n"
    result = read_activity_csv(text)
    assert result.payments == []
    assert [s.reason for s in result.skipped] == [reason]


def test_file_without_paypal_columns_is_rejected():
    with pytest.raises(ActivityFileError, match=r"Missing columns: .*Transaction ID"):
        read_activity_csv("Name,Amount\nAvery,10.00\n")


def test_skipped_row_sharing_an_id_does_not_hide_the_payment():
    header = fixture("activity.csv").splitlines()[0]
    hold = (
        '"03/01/2026","10:00:00","PST","","Hold on Balance","Completed","USD",'
        '"-60.00","0.00","-60.00","","","1AA00000000000020","","","T1503","Debit"'
    )
    gift = (
        '"03/01/2026","10:00:00","PST","Quinn Shared","Donation Payment","Completed",'
        '"USD","60.00","-2.04","57.96","quinn@example.org","giving@example.org",'
        '"1AA00000000000020","","","T0013","Credit"'
    )
    result = read_activity_csv(f"{header}\n{hold}\n{gift}\n")
    assert [p.name for p in result.payments] == ["Quinn Shared"]
    assert [s.reason for s in result.skipped] == [
        "Unsupported type: Hold on Balance (T1503)"
    ]


def test_short_row_is_skipped_with_a_reason():
    header, first, *_ = fixture("activity.csv").splitlines()
    short = ",".join(first.split(",")[:8])  # ends after Gross
    result = read_activity_csv(f"{header}\n{short}\n")
    assert result.payments == []
    assert [s.reason for s in result.skipped] == ["Missing transaction ID"]


def test_amount_beyond_the_stored_precision_is_skipped():
    header, first, *_ = fixture("activity.csv").splitlines()
    huge = first.replace('"100.00","0.00","100.00"', '"10000000000.00","0.00","1.00"')
    result = read_activity_csv(f"{header}\n{huge}\n")
    assert [s.reason for s in result.skipped] == ["Gross is too large: 10000000000.00"]
    largest = first.replace(
        '"100.00","0.00","100.00"', '"9,999,999,999.99","0.00","1.00"'
    )
    assert len(read_activity_csv(f"{header}\n{largest}\n").payments) == 1
