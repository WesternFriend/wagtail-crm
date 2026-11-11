"""Staff issue a donor's acknowledgment letter for a reconciled period (#9)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse
from wagtail.models import ModelLogEntry
from wagtail.users.models import UserProfile

from wagtail_crm.contacts.models import Contact
from wagtail_crm.letters.models import DUPLICATE_ORIGINAL, Letter
from wagtail_crm.payments.models import Payment, Reconciliation

pytestmark = pytest.mark.django_db

ADD_URL = reverse("wagtail_crm_letters:add")
INDEX_URL = reverse("wagtail_crm_letters:index")


def payment(
    transaction_id, gross="100.00", occurred_at="2026-03-01T12:00:00Z", **values
):
    refund = Decimal(gross) < 0
    return Payment.objects.create(
        transaction_id=transaction_id,
        occurred_at=occurred_at,
        name="Avery Example",
        type="Payment Refund" if refund else "Donation Payment",
        event_code="T1107" if refund else "T0013",
        status="Completed",
        currency="USD",
        gross=gross,
        fee="0.00",
        net=gross,
        **values,
    )


def reconciliation(*, accepted=True):
    return Reconciliation.objects.create(
        start=date(2026, 1, 1),
        end=date(2026, 12, 31),
        paypal_count=0,
        paypal_gross=0,
        paypal_fees=0,
        paypal_net=0,
        paypal_refunds=0,
        accepted_at="2027-01-05T12:00:00Z" if accepted else None,
    )


@pytest.fixture
def editor(letter_editor):
    client = Client()
    client.force_login(letter_editor)
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
    return reconciliation()


def issue(client, donor=None, period=None, corrects=None, **extra):
    data = {"corrects": corrects.pk if corrects else ""}
    if donor:
        data["donor"] = donor.pk
    if period:
        data["reconciliation"] = period.pk
    return client.post(ADD_URL, {**data, **extra}, follow=not extra)


def pdf_text(content):
    """The letter's words: pages are stored uncompressed."""
    return content.decode("latin-1")


def test_preview_shows_the_letter_and_saves_nothing(editor, avery, year):
    payment("GIFT1", donor=avery, charitable_amount="60.00")
    payment(
        "GIFT2",
        donor=avery,
        charitable_amount="40.00",
        occurred_at="2026-06-01T12:00:00Z",
    )
    response = issue(editor, avery, year, preview="1")
    assert response["Content-Type"] == "application/pdf"
    assert "no-store" in response["Cache-Control"]
    text = pdf_text(response.content)
    for shown in (
        "Avery Example",
        "1 Example Street",
        "Springfield",
        "GIFT1",
        "60.00",
        "GIFT2",
        "40.00",
        "100.00",
    ):
        assert shown in text
    assert not Letter.objects.exists()


def test_issued_letter_keeps_its_pdf_and_values_after_edits(
    editor, letter_editor, avery, year
):
    gift = payment("GIFT1", donor=avery, charitable_amount="60.00")
    response = issue(editor, avery, year)
    assert "Issued Avery Example" in response.content.decode()
    letter = Letter.objects.get()
    values = letter.values
    pdf = letter.pdf.read()
    assert values["lines"] == [
        {
            "date": "2026-03-01",
            "transaction_id": "GIFT1",
            "gross": "100.00",
            "amount": "60.00",
            "goods_or_services": "40.00",
        }
    ]
    assert values["total"] == "60.00"
    entry = ModelLogEntry.objects.get(action="wagtail_crm_letters.issue")
    assert (entry.user, entry.data["total"]) == (letter_editor, "60.00")

    # AC-12: edit the address and one payment after issuing.
    avery.postal_address = "9 New Road"
    avery.save()
    gift.charitable_amount = Decimal("10.00")
    gift.save()
    letter = Letter.objects.get()
    assert letter.values == values
    assert letter.pdf.read() == pdf
    downloaded = editor.get(reverse("wagtail_crm_letters:pdf", args=[letter.pk]))
    assert b"".join(downloaded.streaming_content) == pdf


def test_correction_links_to_the_original_and_both_pdfs_stay(editor, avery, year):
    gift = payment("GIFT1", donor=avery, charitable_amount="60.00")
    issue(editor, avery, year)
    original = Letter.objects.get()
    gift.charitable_amount = Decimal("50.00")
    gift.save()
    issue(editor, corrects=original)
    correction = Letter.objects.exclude(pk=original.pk).get()
    assert (correction.corrects, correction.donor, correction.reconciliation) == (
        original,
        avery,
        year,
    )
    assert correction.values["total"] == "50.00"
    assert original.values["total"] == "60.00"
    for letter in (original, correction):
        response = editor.get(reverse("wagtail_crm_letters:pdf", args=[letter.pk]))
        assert response.status_code == 200
    page = editor.get(reverse("wagtail_crm_letters:inspect", args=[original.pk]))
    content = page.content.decode()
    assert "Superseded by" in content
    assert "Issue correction" not in content


def test_correction_keeps_the_original_donor_and_period(editor, avery, year):
    payment("GIFT1", donor=avery, charitable_amount="60.00")
    blake = Contact.objects.create(given_name="Blake")
    payment("GIFT2", donor=blake, charitable_amount="5.00")
    issue(editor, avery, year)
    original = Letter.objects.get()
    issue(editor, blake, year, corrects=original)
    correction = Letter.objects.get(corrects=original)
    assert correction.donor == avery


def test_a_letter_is_corrected_only_once(editor, avery, year):
    payment("GIFT1", donor=avery, charitable_amount="60.00")
    issue(editor, avery, year)
    original = Letter.objects.get()
    issue(editor, corrects=original)
    issue(editor, corrects=original)
    assert Letter.objects.count() == 2


def test_second_original_for_the_same_period_is_refused(editor, avery, year):
    payment("GIFT1", donor=avery, charitable_amount="60.00")
    issue(editor, avery, year)
    response = issue(editor, avery, year)
    assert DUPLICATE_ORIGINAL in response.content.decode()
    assert Letter.objects.count() == 1


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        ("unaccepted", "Select a valid choice"),
        ("needs_amount", "Record a charitable amount for these payments first: GIFT2"),
        ("nothing", "This donor has no contributions in this period."),
        ("outside", "This donor has no contributions in this period."),
    ],
)
def test_issuing_is_refused(editor, avery, setup, message):
    period = reconciliation(accepted=setup != "unaccepted")
    if setup in ("unaccepted", "needs_amount"):
        payment("GIFT1", donor=avery, charitable_amount="60.00")
    if setup == "needs_amount":
        payment("GIFT2", donor=avery)
    if setup == "outside":
        payment(
            "GIFT3",
            donor=avery,
            charitable_amount="60.00",
            occurred_at="2027-01-01T00:00:00Z",
        )
    response = issue(editor, avery, period)
    assert message in response.content.decode()
    assert not Letter.objects.exists()


def test_refund_reduces_the_letter_and_never_below_zero(editor, avery, year):
    payment("GIFT1", donor=avery, charitable_amount="60.00")
    payment("REFUND1", gross="-20.00", reference_transaction_id="GIFT1")
    payment("GIFT2", donor=avery, charitable_amount="10.00", gross="30.00")
    payment("REFUND2", gross="-30.00", reference_transaction_id="GIFT2")
    issue(editor, avery, year)
    values = Letter.objects.get().values
    assert [(line["transaction_id"], line["amount"]) for line in values["lines"]] == [
        ("GIFT1", "40.00")
    ]
    assert values["total"] == "40.00"


def test_issued_letters_cannot_be_edited_or_deleted_even_by_a_superuser(avery, year):
    payment("GIFT1", donor=avery, charitable_amount="60.00")
    admin = get_user_model().objects.create_superuser(
        "root", password="synthetic-test-password"
    )
    client = Client()
    client.force_login(admin)
    issue(client, avery, year)
    letter = Letter.objects.get()
    for name in ("edit", "delete"):
        url = reverse(f"wagtail_crm_letters:{name}", args=[letter.pk])
        assert client.get(url).status_code in (302, 403)
        assert client.post(url).status_code in (302, 403)
    letter.refresh_from_db()
    assert Letter.objects.count() == 1
    listing = client.get(INDEX_URL).content.decode()
    assert reverse("wagtail_crm_letters:inspect", args=[letter.pk]) in listing
    assert reverse("wagtail_crm_letters:edit", args=[letter.pk]) not in listing


def test_users_without_letter_permissions_are_denied(editor, staff_user, avery, year):
    payment("GIFT1", donor=avery, charitable_amount="60.00")
    issue(editor, avery, year)
    letter = Letter.objects.get()
    staff_user.user_permissions.clear()
    staff_user.user_permissions.add(Permission.objects.get(codename="access_admin"))
    outsider = Client()
    outsider.force_login(get_user_model().objects.get(pk=staff_user.pk))
    urls = [
        INDEX_URL,
        ADD_URL,
        reverse("wagtail_crm_letters:inspect", args=[letter.pk]),
        reverse("wagtail_crm_letters:pdf", args=[letter.pk]),
        reverse("wagtail_crm_letters:history", args=[letter.pk]),
    ]
    for url in urls:
        response = outsider.get(url)
        assert response.status_code in (302, 403), url
        assert b"Avery" not in response.content
    for extra in ({"preview": "1"}, {}):
        response = outsider.post(
            ADD_URL, {"donor": avery.pk, "reconciliation": year.pk, **extra}
        )
        assert response.status_code in (302, 403)
        assert b"%PDF" not in response.content
    assert Letter.objects.count() == 1


def test_letter_date_is_the_utc_issue_day(editor, avery, year, letter_editor):
    # 11:30 p.m. Pacific on Dec 31 is Jan 1 in UTC; the letter shows Jan 1.
    profile = UserProfile.get_for_user(letter_editor)
    profile.current_time_zone = "America/Los_Angeles"
    profile.save()
    payment("GIFT1", donor=avery, charitable_amount="60.00")
    issued = datetime(2027, 1, 1, 7, 30, tzinfo=UTC)
    with mock.patch("wagtail_crm.letters.views.timezone") as clock:
        clock.now.return_value = issued
        issue(editor, avery, year)
    letter = Letter.objects.get()
    assert letter.values["date"] == letter.date.isoformat() == "2027-01-01"
    assert "2027-01-01" in pdf_text(letter.pdf.read())


def test_mixed_payments_total_their_charitable_parts(editor, avery, year):
    """AC-02: a gift, a patron payment and a purchase."""
    payment("GIFT1", donor=avery, charitable_amount="100.00")
    payment("PATRON1", gross="90.00", donor=avery, charitable_amount="45.00")
    payment("PURCHASE1", gross="20.00", donor=avery, charitable_amount="0")
    issue(editor, avery, year)
    values = Letter.objects.get().values
    lines = [
        (line["transaction_id"], line["amount"], line["goods_or_services"])
        for line in values["lines"]
    ]
    assert lines == [("GIFT1", "100.00", "0.00"), ("PATRON1", "45.00", "45.00")]
    assert values["total"] == "145.00"
