"""Staff import PayPal activity through Wagtail; permissions are Wagtail's own."""

from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from wagtail.users.models import UserProfile

from wagtail_crm.payments.models import Payment

pytestmark = pytest.mark.django_db

FIXTURES = Path(__file__).parent / "fixtures" / "paypal"
IMPORT_URL = reverse("wagtail_crm_payments:add")
INDEX_URL = reverse("wagtail_crm_payments:index")


def upload(client, name="activity.csv"):
    data = (FIXTURES / name).read_bytes()
    return client.post(IMPORT_URL, {"file": SimpleUploadedFile(name, data)})


def confirm(client, preview):
    return client.post(
        IMPORT_URL, {"confirm": "", "digest": preview.context["digest"]}, follow=True
    )


@pytest.fixture
def editor(payment_editor):
    client = Client()
    client.force_login(payment_editor)
    return client


def test_empty_list_points_to_the_import(editor):
    content = editor.get(INDEX_URL).content.decode()
    assert "Import a PayPal CSV" in content
    assert "Why not" not in content


def test_preview_saves_nothing_and_lists_skipped_rows(editor):
    response = upload(editor)
    assert response.status_code == 200
    assert Payment.objects.count() == 0
    content = response.content.decode()
    assert "6 to import, 7 skipped" in content
    assert "Currency EUR is not supported" in content
    assert "Outgoing payment (T0006)" in content


def test_confirm_imports_and_shows_the_payments_list(editor):
    response = confirm(editor, upload(editor))
    assert response.redirect_chain[-1][0] == INDEX_URL
    assert "Imported 6 payments." in response.content.decode()
    assert Payment.objects.count() == 6
    assert "Jordan Major" in response.content.decode()
    assert "wagtail_crm_payments_import" not in editor.session


def test_repeated_file_offers_nothing_to_confirm(editor):
    confirm(editor, upload(editor))
    response = upload(editor)
    assert "Nothing new to import" in response.content.decode()
    assert 'name="confirm"' not in response.content.decode()
    assert "wagtail_crm_payments_import" not in editor.session


def test_overlapping_file_adds_only_new_payments(editor):
    confirm(editor, upload(editor))
    confirm(editor, upload(editor, "activity-overlap.csv"))
    assert Payment.objects.count() == 8


def test_cancel_discards_the_preview(editor):
    preview = upload(editor)
    response = editor.post(
        IMPORT_URL, {"cancel": "", "digest": preview.context["digest"]}
    )
    assert response.url == INDEX_URL
    assert "wagtail_crm_payments_import" not in editor.session
    assert Payment.objects.count() == 0


def test_older_tab_neither_imports_nor_discards_the_newer_preview(editor):
    first = upload(editor)
    newer = upload(editor, "activity-overlap.csv")
    response = confirm(editor, first)
    assert "This preview is out of date" in response.content.decode()
    editor.post(IMPORT_URL, {"cancel": "", "digest": first.context["digest"]})
    assert Payment.objects.count() == 0
    confirm(editor, newer)
    assert Payment.objects.count() == 4


def test_failed_import_leaves_nothing_imported(editor, monkeypatch):
    preview = upload(editor)
    real_bulk_create = Payment.objects.bulk_create

    def clash(payments, **kwargs):
        # One payment is written, then the batch hits the unique transaction ID,
        # as when someone else imports the same payment concurrently.
        real_bulk_create(payments[:1])
        return real_bulk_create(payments, **kwargs)

    monkeypatch.setattr(Payment.objects, "bulk_create", clash)
    response = confirm(editor, preview)
    assert "Nothing was imported" in response.content.decode()
    assert Payment.objects.count() == 0


def test_file_that_is_not_paypal_activity_is_rejected(editor):
    response = editor.post(
        IMPORT_URL, {"file": SimpleUploadedFile("x.csv", b"Name,Amount\nA,1\n")}
    )
    assert "Missing columns" in response.content.decode()
    response = editor.post(
        IMPORT_URL, {"file": SimpleUploadedFile("x.csv", b"\xff\xfe\x00")}
    )
    assert "Save the file as a UTF-8 CSV" in response.content.decode()


def test_inspect_shows_source_facts(editor):
    confirm(editor, upload(editor))
    refund = Payment.objects.get(transaction_id="1AA00000000000005")
    inspect = editor.get(reverse("wagtail_crm_payments:inspect", args=[refund.pk]))
    assert "1AA00000000000004" in inspect.content.decode()


@pytest.mark.parametrize(
    "url",
    [
        INDEX_URL,
        IMPORT_URL,
        reverse("wagtail_crm_payments:inspect", args=[1]),
        reverse("wagtail_crm_payments:edit", args=[1]),
        reverse("wagtail_crm_payments:delete", args=[1]),
    ],
)
def test_staff_without_payment_permissions_are_denied(staff_user, url):
    Payment.objects.bulk_create(
        [
            Payment(
                pk=1,
                transaction_id="X1",
                occurred_at="2026-01-01T00:00:00Z",
                type="Donation Payment",
                event_code="T0013",
                status="Completed",
                currency="USD",
                gross=1,
                fee=0,
                net=1,
            )
        ]
    )
    client = Client()
    client.force_login(staff_user)
    for method in (client.get, client.post):
        response = method(url)
        assert response.status_code in (302, 403)
        if response.status_code == 302:
            assert response.url.startswith(reverse("wagtailadmin_home"))
    assert Payment.objects.count() == 1


def test_editor_cannot_delete_payments(editor):
    confirm(editor, upload(editor))
    url = reverse("wagtail_crm_payments:delete", args=[Payment.objects.first().pk])
    assert editor.post(url).status_code in (302, 403)
    assert Payment.objects.count() == 6


def test_dates_follow_each_staff_members_wagtail_time_zone(editor, payment_editor):
    # Stored in UTC; shown in the zone from Account → Preferences.
    profile = UserProfile.get_for_user(payment_editor)
    profile.current_time_zone = "America/Los_Angeles"
    profile.save()
    preview = upload(editor).content.decode()
    assert "Dec. 31, 2026, 11:59 p.m." in preview
    listing = confirm(editor, upload(editor)).content.decode()
    assert "Dec. 31, 2026, 11:59 p.m." in listing
    assert "Jan. 1, 2027" not in listing
    gift = Payment.objects.get(transaction_id="1AA00000000000012")
    assert gift.occurred_at.isoformat() == "2027-01-01T07:59:59+00:00"
