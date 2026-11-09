"""Staff see refunds next to the payments they refund (AC-08)."""

from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from wagtail_crm.payments.models import Payment

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).parent / "fixtures" / "paypal"
IMPORT_URL = reverse("wagtail_crm_payments:add")
INDEX_URL = reverse("wagtail_crm_payments:index")


def import_file(client, name):
    data = (FIXTURES / name).read_bytes()
    preview = client.post(IMPORT_URL, {"file": SimpleUploadedFile(name, data)})
    client.post(IMPORT_URL, {"confirm": "", "digest": preview.context["digest"]})


def unmatched(client):
    response = client.get(INDEX_URL, {"unmatched_refund": "true"})
    return {p.transaction_id for p in response.context["object_list"]}


def by_id(transaction_id):
    return Payment.objects.get(transaction_id=transaction_id)


def set_charitable(transaction_id, amount):
    Payment.objects.filter(transaction_id=transaction_id).update(
        charitable_amount=amount
    )


@pytest.fixture
def editor(payment_editor):
    client = Client()
    client.force_login(payment_editor)
    return client


@pytest.fixture
def imported(editor):
    import_file(editor, "activity.csv")
    import_file(editor, "refunds.csv")
    return editor


def test_payment_shows_its_refund_and_adjusted_amount(imported):
    set_charitable("1AA00000000000004", "20.00")
    website = by_id("1AA00000000000004")
    page = imported.get(reverse("wagtail_crm_payments:edit", args=[website.pk]))
    content = page.content.decode()
    refund = by_id("1AA00000000000005")
    assert reverse("wagtail_crm_payments:edit", args=[refund.pk]) in content
    assert "-20.00" in content
    assert "Adjusted charitable amount: 0.00" in content


def test_refund_page_links_to_its_original(imported):
    refund = by_id("1AA00000000000005")
    content = imported.get(
        reverse("wagtail_crm_payments:edit", args=[refund.pk])
    ).content.decode()
    original = by_id("1AA00000000000004")
    assert "Refund of" in content
    assert reverse("wagtail_crm_payments:edit", args=[original.pk]) in content


def test_unmatched_refund_is_listed_for_review(imported):
    assert unmatched(imported) == {"1RR00000000000004"}
    orphan = by_id("1RR00000000000004")
    content = imported.get(
        reverse("wagtail_crm_payments:inspect", args=[orphan.pk])
    ).content.decode()
    assert "1AA00000000000099 is not imported" in content


def test_refund_imported_before_its_payment_links_later(editor):
    import_file(editor, "refunds.csv")
    assert unmatched(editor) == {
        "1RR00000000000001",
        "1RR00000000000002",
        "1RR00000000000003",
        "1RR00000000000004",
    }
    import_file(editor, "activity.csv")
    assert unmatched(editor) == {"1RR00000000000004"}


@pytest.mark.parametrize(
    ("transaction_id", "charitable", "adjusted"),
    [
        ("1AA00000000000002", "50.00", "25.00"),  # two refunds, summed
        ("1AA00000000000003", "30.00", "0"),  # larger refund floors at 0
        ("1AA00000000000003", None, None),  # blank stays blank
        ("1AA00000000000001", "100.00", "100.00"),  # no refund
    ],
)
def test_adjusted_amount(imported, transaction_id, charitable, adjusted):
    set_charitable(transaction_id, charitable)
    listed = Payment.objects.with_refunded().get(transaction_id=transaction_id)
    alone = by_id(transaction_id)
    expected = None if adjusted is None else Decimal(adjusted)
    assert listed.adjusted_charitable_amount == expected
    assert alone.adjusted_charitable_amount == expected
    assert listed.refunded_amount == alone.refunded_amount


def test_refunded_payment_still_needs_a_charitable_amount(imported):
    response = imported.get(INDEX_URL, {"needs_charitable_amount": "true"})
    ids = {p.transaction_id for p in response.context["object_list"]}
    assert "1AA00000000000002" in ids


def test_refunded_column_is_blank_without_refunds(imported):
    rows = {
        p.transaction_id: p.refunded_amount
        for p in imported.get(INDEX_URL).context["object_list"]
    }
    assert str(rows["1AA00000000000002"]) == "-25.00"
    assert rows["1AA00000000000001"] is None


def test_list_query_count_does_not_grow_with_payments(editor):
    def count_queries():
        with CaptureQueriesContext(connection) as queries:
            assert editor.get(INDEX_URL).status_code == 200
        return len(queries.captured_queries)

    import_file(editor, "refunds.csv")
    editor.get(INDEX_URL)
    few = count_queries()
    import_file(editor, "activity.csv")
    assert Payment.objects.count() == 10
    assert count_queries() == few


def test_inspect_links_to_inspect_pages(imported):
    website = by_id("1AA00000000000004")
    refund = by_id("1AA00000000000005")
    inspect = reverse("wagtail_crm_payments:inspect", args=[website.pk])
    content = imported.get(inspect).content.decode()
    assert reverse("wagtail_crm_payments:inspect", args=[refund.pk]) in content
    assert reverse("wagtail_crm_payments:edit", args=[refund.pk]) not in content
