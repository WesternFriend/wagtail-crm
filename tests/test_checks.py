"""Staff record mailed checks; they count on letters like PayPal payments (#25)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from wagtail.models import ModelLogEntry

from wagtail_crm.contacts.models import Contact
from wagtail_crm.payments.models import Payment, Reconciliation, Source
from wagtail_crm.payments.views import comparison

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).parent / "fixtures" / "paypal"
CHECK_URL = reverse("wagtail_crm_payments:add_check")
INDEX_URL = reverse("wagtail_crm_payments:index")
IMPORT_URL = reverse("wagtail_crm_payments:add")


@pytest.fixture
def editor(payment_editor, letter_editor):
    payment_editor.user_permissions.add(
        *Permission.objects.filter(codename__endswith="_reconciliation")
    )
    client = Client()
    client.force_login(payment_editor)
    return client


@pytest.fixture
def avery():
    return Contact.objects.create(
        given_name="Avery",
        family_name="Example",
        postal_address="1 Example Street\nSpringfield",
    )


@pytest.fixture
def year():
    return Reconciliation.objects.create(
        start=date(2026, 1, 1),
        end=date(2026, 12, 31),
        paypal_count=0,
        paypal_gross="0",
        paypal_fees="0",
        paypal_net="0",
        paypal_refunds="0",
        accepted_at="2027-01-05T12:00:00Z",
    )


def record(client, contact, **values):
    data = {
        "received": "2026-03-02",
        "check_number": "1001",
        "amount": "75.00",
        "donor": contact.pk,
        "charitable_amount": "75.00",
    }
    return client.post(CHECK_URL, {**data, **values})


def import_file(client, name):
    data = (FIXTURES / name).read_bytes()
    preview = client.post(IMPORT_URL, {"file": SimpleUploadedFile(name, data)})
    client.post(IMPORT_URL, {"confirm": "", "digest": preview.context["digest"]})


def paypal_payment(transaction_id, **values):
    return Payment.objects.create(
        transaction_id=transaction_id,
        occurred_at="2026-03-01T12:00:00Z",
        name="Avery Example",
        type="Donation Payment",
        event_code="T0013",
        status="Completed",
        currency="USD",
        gross="100.00",
        fee="-3.00",
        net="97.00",
        **values,
    )


def test_recorded_check_counts_on_the_donors_letter(editor, avery, year):
    assert record(editor, avery).status_code == 302
    check = Payment.objects.get()
    assert check.source == Source.CHECK
    assert str(check) == "Check 1001"
    assert check.occurred_at == datetime(2026, 3, 2, 12, tzinfo=UTC)
    assert (check.gross, check.fee, check.net) == (
        Decimal("75.00"),
        Decimal("0.00"),
        Decimal("75.00"),
    )
    assert check.currency == "USD"
    assert not check.is_refund
    assert ModelLogEntry.objects.filter(
        object_id=str(check.pk), action="wagtail.create"
    ).exists()

    preview = editor.post(
        reverse("wagtail_crm_letters:add"),
        {"donor": avery.pk, "reconciliation": year.pk, "corrects": "", "preview": "1"},
    )
    text = preview.content.decode("latin-1")
    assert "Check 1001" in text
    assert "2026-03-02" in text
    assert "75.00" in text


def test_charitable_amount_above_the_check_is_refused_and_kept(editor, avery):
    response = record(editor, avery, charitable_amount="80.00")
    assert response.status_code == 200
    form = response.context["form"]
    assert "charitable_amount" in form.errors
    assert form["check_number"].value() == "1001"
    assert form["amount"].value() == "75.00"
    assert not Payment.objects.exists()


@pytest.mark.parametrize("missing", ["donor", "charitable_amount", "check_number"])
def test_a_check_needs_its_donor_number_and_charitable_amount(editor, avery, missing):
    response = record(editor, avery, **{missing: ""})
    assert missing in response.context["form"].errors
    assert not Payment.objects.exists()


def test_donors_may_share_a_check_number(editor, avery):
    blake = Contact.objects.create(given_name="Blake", family_name="Sample")
    record(editor, avery)
    record(editor, blake)
    assert Payment.objects.checks().count() == 2


def test_editing_a_check_corrects_it_and_history_shows_it(editor, avery):
    record(editor, avery)
    check = Payment.objects.get()
    url = reverse("wagtail_crm_payments:edit", args=[check.pk])
    page = editor.get(url)
    assert page.context["form"]["check_number"].value() == "1001"
    assert page.context["form"]["received"].value() == date(2026, 3, 2)
    response = editor.post(
        url,
        {
            "received": "2026-03-03",
            "check_number": "1002",
            "amount": "70.00",
            "donor": avery.pk,
            "charitable_amount": "70.00",
        },
    )
    assert response.status_code == 302
    check.refresh_from_db()
    assert (check.transaction_id, check.gross, check.net) == (
        "1002",
        Decimal("70.00"),
        Decimal("70.00"),
    )
    assert check.occurred_at == datetime(2026, 3, 3, 12, tzinfo=UTC)
    assert ModelLogEntry.objects.filter(
        object_id=str(check.pk), action="wagtail.edit"
    ).exists()


def test_paypal_values_stay_read_only(editor, avery):
    payment = paypal_payment("PAYPAL1")
    response = editor.post(
        reverse("wagtail_crm_payments:edit", args=[payment.pk]),
        {
            "donor": avery.pk,
            "charitable_amount": "100.00",
            "gross": "1.00",
            "amount": "1.00",
            "transaction_id": "CHANGED",
            "check_number": "CHANGED",
            "occurred_at": "2020-01-01T00:00:00Z",
            "received": "2020-01-01",
        },
    )
    assert response.status_code == 302
    payment.refresh_from_db()
    assert payment.source == Source.PAYPAL
    assert payment.transaction_id == "PAYPAL1"
    assert payment.gross == Decimal("100.00")
    assert payment.occurred_at == datetime(2026, 3, 1, 12, tzinfo=UTC)
    assert payment.event_code == "T0013"


def test_check_number_equal_to_a_paypal_id_does_not_block_the_import(editor, avery):
    record(editor, avery, check_number="1AA00000000000001")
    import_file(editor, "activity.csv")
    assert Payment.objects.paypal().filter(transaction_id="1AA00000000000001").exists()


def test_paypal_refund_never_reduces_a_check(editor, avery, year):
    # refunds.csv refunds 1AA00000000000002, which is not imported here.
    record(editor, avery, check_number="1AA00000000000002")
    import_file(editor, "refunds.csv")
    check = Payment.objects.checks().get()
    assert check.refunded_amount is None
    assert check.adjusted_charitable_amount == Decimal("75.00")
    assert list(check.refunds) == []
    unmatched = Payment.objects.unmatched_refunds()
    assert unmatched.filter(reference_transaction_id="1AA00000000000002").exists()
    for refund in unmatched:
        assert refund.refunded_payment is None


def test_reconciliation_compares_paypal_rows_and_lists_checks(editor, avery, year):
    paypal_payment("PAYPAL1", donor=avery, charitable_amount="100.00")
    record(editor, avery)
    year.refresh_from_db()
    crm, _ = comparison(year)
    assert crm["count"] == 1
    assert crm["gross"] == Decimal("100.00")
    assert year.check_totals() == {"count": 1, "gross": Decimal("75.00")}
    content = editor.get(
        reverse("wagtail_crm_reconciliations:edit", args=[year.pk])
    ).content.decode()
    assert (
        "Mailed checks in this period, not in PayPal's report: 1, gross 75.00"
        in content
    )
    assert "Check 1001" in content


def test_payment_list_finds_checks_by_number_and_source(editor, avery):
    paypal_payment("PAYPAL1")
    record(editor, avery)
    listed = editor.get(INDEX_URL, {"q": "1001"}).context["object_list"]
    assert [str(p) for p in listed] == ["Check 1001"]
    listed = editor.get(INDEX_URL, {"source": "check"}).context["object_list"]
    assert [str(p) for p in listed] == ["Check 1001"]
    content = editor.get(INDEX_URL).content.decode()
    assert f'href="{CHECK_URL}"' in content
    assert f'action="{CHECK_URL}"' in editor.get(CHECK_URL).content.decode()
    assert "Record check" in content
    assert "Transaction ID or check number" in content
    assert "<td>1001</td>" in content.replace(" ", "").replace("\n", "")
    assert "Import PayPal CSV" in content


def test_inspect_labels_the_check_number_and_hides_paypal_facts(editor, avery):
    record(editor, avery)
    check = Payment.objects.get()
    content = editor.get(
        reverse("wagtail_crm_payments:inspect", args=[check.pk])
    ).content.decode()
    assert "Check number" in content
    assert "Transaction ID" not in content
    assert "Fee" not in content


def test_users_without_payment_permissions_cannot_record_checks(staff_user, avery):
    client = Client()
    client.force_login(staff_user)
    assert client.get(CHECK_URL).status_code in (302, 403)
    assert record(client, avery).status_code in (302, 403)
    assert not Payment.objects.exists()


def test_edit_refuses_missing_and_existing_checks_alike(editor, staff_user, avery):
    record(editor, avery)
    check = Payment.objects.get()
    outsider = Client()
    outsider.force_login(staff_user)
    staff_user.user_permissions.set(Permission.objects.filter(codename="access_admin"))
    for pk in (check.pk, check.pk + 1000):
        response = outsider.get(reverse("wagtail_crm_payments:edit", args=[pk]))
        assert response.status_code in (302, 403), pk
