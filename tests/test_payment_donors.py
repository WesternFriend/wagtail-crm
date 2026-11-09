"""Staff link a payment to a donor and record how much of it is charitable."""

from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from wagtail.models import ModelLogEntry

from wagtail_crm.contacts.models import Contact
from wagtail_crm.payments.models import REFUND_NOT_LINKED, Payment

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).parent / "fixtures" / "paypal"
IMPORT_URL = reverse("wagtail_crm_payments:add")
INDEX_URL = reverse("wagtail_crm_payments:index")


def payment(transaction_id="GIFT1", gross="100.00", fee="-3.00", **values):
    return Payment.objects.create(
        transaction_id=transaction_id,
        occurred_at="2026-03-01T12:00:00Z",
        name="Avery Example",
        email="avery@example.org",
        type="Donation Payment",
        event_code="T0013" if Decimal(gross) > 0 else "T1107",
        status="Completed",
        currency="USD",
        gross=gross,
        fee=fee,
        net=Decimal(gross) + Decimal(fee),
        **values,
    )


def edit(client, item, donor="", amount=""):
    return client.post(
        reverse("wagtail_crm_payments:edit", args=[item.pk]),
        {"donor": donor.pk if donor else "", "charitable_amount": amount},
        follow=True,
    )


@pytest.fixture
def editor(payment_editor):
    client = Client()
    client.force_login(payment_editor)
    return client


@pytest.fixture
def avery():
    return Contact.objects.create(given_name="Avery", family_name="Example")


def test_fee_does_not_reduce_the_charitable_amount(editor, avery):
    gift = payment()
    response = edit(editor, gift, avery, "100.00")
    gift.refresh_from_db()
    assert (gift.donor, gift.charitable_amount) == (avery, Decimal("100.00"))
    assert gift.non_charitable_amount == 0
    listing = response.content.decode()
    assert "Avery Example" in listing
    assert "100.00" in listing


@pytest.mark.parametrize(
    ("charitable", "remainder"), [("30.00", "60.00"), ("0", "90.00")]
)
def test_non_charitable_remainder_is_gross_minus_charitable(charitable, remainder):
    subscription = payment(gross="90.00", fee="-2.91", charitable_amount=charitable)
    subscription.refresh_from_db()
    assert subscription.non_charitable_amount == Decimal(remainder)


@pytest.mark.parametrize(
    ("amount", "message"),
    [
        ("100.01", "Enter no more than the gross amount, 100.00."),
        ("-1", "Enter 0 or more."),
    ],
)
def test_out_of_range_amount_is_refused_and_kept_on_screen(
    editor, avery, amount, message
):
    gift = payment()
    response = edit(editor, gift, avery, amount)
    content = response.content.decode()
    assert message in content
    assert f'value="{amount}"' in content
    gift.refresh_from_db()
    assert (gift.donor, gift.charitable_amount) == (None, None)


def test_blank_amount_needs_one_and_zero_does_not(editor, avery):
    blank = payment("BLANK")
    zero = payment("ZERO")
    edit(editor, blank, avery, "")
    edit(editor, zero, avery, "0")
    blank.refresh_from_db()
    zero.refresh_from_db()
    assert blank.charitable_amount is None
    assert zero.charitable_amount == 0
    needs = editor.get(INDEX_URL, {"needs_charitable_amount": "true"})
    assert list(needs.context["object_list"]) == [blank]


def test_needs_donor_lists_received_payments_without_one(editor, avery):
    linked = payment("LINKED", donor=avery)
    unlinked = payment("UNLINKED")
    payment("REFUND", gross="-20.00", fee="0.59")
    needs = editor.get(INDEX_URL, {"needs_donor": "true"})
    assert list(needs.context["object_list"]) == [unlinked]
    done = editor.get(INDEX_URL, {"needs_donor": "false"})
    assert list(done.context["object_list"]) == [linked]


def test_refund_is_not_linked_to_a_donor(editor, avery):
    refund = payment("REFUND", gross="-20.00", fee="0.59")
    response = edit(editor, refund, avery, "0")
    assert REFUND_NOT_LINKED.replace("'", "&#x27;") in response.content.decode()
    refund.refresh_from_db()
    assert (refund.donor, refund.charitable_amount) == (None, None)
    needs = editor.get(INDEX_URL, {"needs_charitable_amount": "true"})
    assert refund not in needs.context["object_list"]


def test_edit_page_shows_the_paypal_facts(editor):
    gift = payment()
    content = editor.get(reverse("wagtail_crm_payments:edit", args=[gift.pk]))
    assert set(content.context["form"].fields) == {"donor", "charitable_amount"}
    page = content.content.decode()
    for fact in ("Avery Example", "avery@example.org", "100.00", "-3.00", "97.00"):
        assert fact in page


def test_contact_with_payments_cannot_be_deleted(contact_editor, editor, avery):
    assert contact_editor.has_perm("wagtail_crm_contacts.delete_contact")
    edit(editor, payment(), avery, "100.00")
    url = reverse("wagtail_crm_contacts:delete", args=[avery.pk])
    page = editor.get(url)
    assert page.context["is_protected"]
    assert "prevent it from being deleted" in page.content.decode()
    # Wagtail answers PermissionDenied in the admin by returning to the dashboard.
    refused = editor.post(url)
    assert (refused.status_code, refused.url) == (302, reverse("wagtailadmin_home"))
    assert Contact.objects.filter(pk=avery.pk).exists()


def test_reimport_keeps_donor_links_and_amounts(editor, avery):
    data = (FIXTURES / "activity.csv").read_bytes()
    preview = editor.post(IMPORT_URL, {"file": SimpleUploadedFile("a.csv", data)})
    editor.post(IMPORT_URL, {"confirm": "", "digest": preview.context["digest"]})
    gift = Payment.objects.get(transaction_id="1AA00000000000001")
    edit(editor, gift, avery, "60.00")
    # The overlapping file repeats this gift alongside new payments.
    overlap = (FIXTURES / "activity-overlap.csv").read_bytes()
    preview = editor.post(IMPORT_URL, {"file": SimpleUploadedFile("b.csv", overlap)})
    editor.post(IMPORT_URL, {"confirm": "", "digest": preview.context["digest"]})
    assert Payment.objects.count() == 8
    gift.refresh_from_db()
    assert (gift.donor, gift.charitable_amount) == (avery, Decimal("60.00"))


def test_contact_chooser_searches_by_name_and_email(editor, contact_editor, avery):
    Contact.objects.create(given_name="Blake", email="blake@example.org")
    url = reverse("wagtail_crm_contact_chooser:choose_results")
    by_name = editor.get(url, {"q": "aver"})
    assert list(by_name.context["results"]) == [avery]
    by_email = editor.get(url, {"q": "blake@"})
    assert [str(c) for c in by_email.context["results"]] == ["Blake"]


@pytest.mark.parametrize(
    "values",
    [
        {"charitable_amount": "100.01"},
        {"charitable_amount": "-1"},
        {"gross": "-20.00", "fee": "0.59", "charitable_amount": "0"},
    ],
)
def test_database_refuses_invalid_decisions_from_any_writer(values):
    with pytest.raises(IntegrityError), transaction.atomic():
        payment(**values)


def test_refund_donor_is_refused_by_the_database(avery):
    refund = Payment.objects.filter(pk=payment(gross="-20.00", fee="0.59").pk)
    with pytest.raises(IntegrityError), transaction.atomic():
        refund.update(donor=avery)


def test_clean_without_a_gross_amount_does_not_crash():
    Payment(event_code="T0013", charitable_amount=Decimal(5)).clean()


@pytest.mark.parametrize("name", ["choose", "choose_results", "chosen"])
def test_contact_chooser_needs_contact_access(staff_user, avery, name):
    client = Client()
    client.force_login(staff_user)
    args = [avery.pk] if name == "chosen" else []
    response = client.get(reverse(f"wagtail_crm_contact_chooser:{name}", args=args))
    assert response.status_code in (302, 403)
    assert "Avery" not in response.content.decode()


def test_contact_created_in_the_chooser_has_history(editor, contact_editor):
    editor.post(
        reverse("wagtail_crm_contact_chooser:create"),
        {"kind": "person", "given_name": "Robin", "family_name": "New"},
    )
    robin = Contact.objects.get(display_name="Robin New")
    entry = ModelLogEntry.objects.get(object_id=str(robin.pk))
    assert (entry.action, entry.user) == ("wagtail.create", contact_editor)
