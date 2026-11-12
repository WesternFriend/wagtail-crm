"""Staff record how each issued letter was sent, including failures (#10)."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from wagtail.models import ModelLogEntry

from wagtail_crm.contacts.models import Contact
from wagtail_crm.letters.models import Dispatch, DispatchStatus, Letter
from wagtail_crm.payments.models import Payment, Reconciliation

pytestmark = pytest.mark.django_db

ADD_URL = reverse("wagtail_crm_dispatches:add")
LETTERS_URL = reverse("wagtail_crm_letters:index")


@pytest.fixture
def editor(letter_editor):
    client = Client()
    client.force_login(letter_editor)
    return client


@pytest.fixture
def letter(editor):
    avery = Contact.objects.create(given_name="Avery", family_name="Example")
    Payment.objects.create(
        transaction_id="GIFT1",
        occurred_at="2026-03-01T12:00:00Z",
        name="Avery Example",
        type="Donation Payment",
        event_code="T0013",
        status="Completed",
        currency="USD",
        gross="100.00",
        fee="-3.00",
        net="97.00",
        donor=avery,
        charitable_amount="100.00",
    )
    year = Reconciliation.objects.create(
        start=date(2026, 1, 1),
        end=date(2026, 12, 31),
        paypal_count=1,
        paypal_gross="100.00",
        paypal_fees="-3.00",
        paypal_net="97.00",
        paypal_refunds="0",
        accepted_at="2027-01-05T12:00:00Z",
    )
    editor.post(
        reverse("wagtail_crm_letters:add"),
        {"donor": avery.pk, "reconciliation": year.pk, "corrects": ""},
    )
    return Letter.objects.get()


def record(client, letter, **values):
    data = {"channel": "post", "date": "2027-01-10", "outcome": "sent", "note": ""}
    return client.post(f"{ADD_URL}?letter={letter.pk}", {**data, **values}, follow=True)


def listed(client, status):
    response = client.get(LETTERS_URL, {"dispatch": status})
    return list(response.context["object_list"])


def status(letter):
    return Letter.objects.with_dispatch_status().get(pk=letter.pk).dispatch_status


def test_download_then_failed_email_then_sent_post(editor, letter):
    """AC-14."""
    editor.get(reverse("wagtail_crm_letters:pdf", args=[letter.pk]))
    assert status(letter) == DispatchStatus.NOT_SENT
    assert listed(editor, "not_sent") == [letter]

    page = record(
        editor, letter, channel="email", outcome="failed", note="Address bounced"
    )
    assert page.request["PATH_INFO"] == reverse(
        "wagtail_crm_letters:inspect", args=[letter.pk]
    )
    assert status(letter) == DispatchStatus.FAILED
    assert listed(editor, "failed") == [letter]
    assert listed(editor, "not_sent") == []

    page = record(editor, letter, date="2027-01-12")
    content = page.content.decode()
    assert "2027-01-10: Failed by email. Address bounced" in content
    assert "2027-01-12: Sent by post" in content
    assert "Sent" in content
    assert listed(editor, "sent") == [letter]
    assert listed(editor, "failed") == []


def test_sent_wins_over_a_later_failure(editor, letter):
    record(editor, letter, date="2027-01-10")
    record(editor, letter, date="2027-01-20", outcome="failed", note="Returned")
    assert status(letter) == DispatchStatus.SENT


def test_superseded_letter_is_not_owed_a_dispatch(editor, letter):
    editor.post(reverse("wagtail_crm_letters:add"), {"corrects": letter.pk})
    correction = Letter.objects.get(corrects=letter)
    assert listed(editor, "not_sent") == [correction]
    assert status(letter) == DispatchStatus.SUPERSEDED
    # It may have been posted before the correction; that can still be recorded.
    record(editor, letter)
    assert status(letter) == DispatchStatus.SUPERSEDED
    assert letter.dispatches.count() == 1


def test_failure_needs_a_note(editor, letter):
    page = record(editor, letter, outcome="failed")
    assert "Add a note saying what went wrong." in page.content.decode()
    assert not Dispatch.objects.exists()
    with pytest.raises(IntegrityError), transaction.atomic():
        Dispatch.objects.create(letter=letter, channel="post", outcome="failed")


@pytest.mark.parametrize("pk", ["", "invalid", "²", "999"])
def test_dispatch_must_name_a_letter(editor, pk):
    url = f"{ADD_URL}?letter={pk}"
    assert editor.get(url).status_code == 404
    assert editor.post(url, {"channel": "post", "outcome": "sent"}).status_code == 404
    assert not Dispatch.objects.exists()


def test_edit_fixes_a_mistake_but_keeps_the_letter(editor, letter):
    record(editor, letter)
    dispatch = Dispatch.objects.get()
    other = Letter.objects.create(
        donor=letter.donor,
        reconciliation=letter.reconciliation,
        corrects=letter,
        values=letter.values,
        pdf=letter.pdf.name,
    )
    url = reverse("wagtail_crm_dispatches:edit", args=[dispatch.pk])
    response = editor.post(
        url,
        {
            "letter": other.pk,
            "channel": "post",
            "date": "2027-01-10",
            "outcome": "failed",
            "note": "Recorded by mistake",
        },
    )
    assert response.url == reverse("wagtail_crm_letters:inspect", args=[letter.pk])
    dispatch.refresh_from_db()
    assert (dispatch.letter, dispatch.outcome) == (letter, "failed")
    entry = ModelLogEntry.objects.filter(object_id=str(dispatch.pk)).first()
    assert entry.action == "wagtail.edit"


def test_dispatches_cannot_be_deleted_even_by_a_superuser(letter):
    dispatch = Dispatch.objects.create(letter=letter, channel="post", outcome="sent")
    admin = get_user_model().objects.create_superuser(
        "root", password="synthetic-test-password"
    )
    client = Client()
    client.force_login(admin)
    url = reverse("wagtail_crm_dispatches:delete", args=[dispatch.pk])
    assert client.post(url).status_code in (302, 403)
    assert Dispatch.objects.filter(pk=dispatch.pk).exists()


def test_users_without_dispatch_permissions_are_denied(editor, staff_user, letter):
    dispatch = Dispatch.objects.create(letter=letter, channel="post", outcome="sent")
    staff_user.user_permissions.clear()
    staff_user.user_permissions.add(Permission.objects.get(codename="access_admin"))
    outsider = Client()
    outsider.force_login(get_user_model().objects.get(pk=staff_user.pk))
    for url in (
        reverse("wagtail_crm_dispatches:index"),
        f"{ADD_URL}?letter={letter.pk}",
        reverse("wagtail_crm_dispatches:edit", args=[dispatch.pk]),
        reverse("wagtail_crm_dispatches:history", args=[dispatch.pk]),
    ):
        response = outsider.get(url)
        assert response.status_code in (302, 403), url
        assert b"Avery" not in response.content
    response = outsider.post(
        f"{ADD_URL}?letter={letter.pk}", {"channel": "post", "outcome": "sent"}
    )
    assert response.status_code in (302, 403)
    response = outsider.post(
        reverse("wagtail_crm_dispatches:edit", args=[dispatch.pk]),
        {"channel": "email", "outcome": "failed", "note": "x"},
    )
    assert response.status_code in (302, 403)
    dispatch.refresh_from_db()
    assert (Dispatch.objects.count(), dispatch.channel) == (1, "post")


def test_adding_dispatches_alone_shows_no_letters_or_dispatches(staff_user, letter):
    Dispatch.objects.create(letter=letter, channel="post", outcome="sent")
    staff_user.user_permissions.set(
        Permission.objects.filter(codename__in=["access_admin", "add_dispatch"])
    )
    client = Client()
    client.force_login(get_user_model().objects.get(pk=staff_user.pk))
    for url in (
        reverse("wagtail_crm_dispatches:index"),
        f"{ADD_URL}?letter={letter.pk}",
    ):
        response = client.get(url)
        assert response.status_code in (302, 403), url
        assert b"Avery" not in response.content
    response = client.post(
        f"{ADD_URL}?letter={letter.pk}", {"channel": "post", "outcome": "sent"}
    )
    assert response.status_code in (302, 403)
    assert Dispatch.objects.count() == 1
