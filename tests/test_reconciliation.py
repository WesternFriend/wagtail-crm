"""Staff reconcile a period's totals against PayPal's report (AC-10)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse
from wagtail.models import ModelLogEntry
from wagtail.users.models import UserProfile

from wagtail_crm.payments.models import Payment, Reconciliation, period_is_accepted

pytestmark = pytest.mark.django_db

ADD_URL = reverse("wagtail_crm_reconciliations:add")
YEAR = {"start": "2026-01-01", "end": "2026-12-31"}
MATCHING = {
    "paypal_count": "1",
    "paypal_gross": "100.00",
    "paypal_fees": "-3.00",
    "paypal_net": "97.00",
    "paypal_refunds": "-20.00",
}


def payment(transaction_id, occurred_at, gross="100.00", **values):
    refund = Decimal(gross) < 0
    defaults = {
        "name": "Avery Example",
        "type": "Payment Refund" if refund else "Donation Payment",
        "event_code": "T1107" if refund else "T0013",
        "status": "Completed",
        "currency": "USD",
        "gross": gross,
        "fee": "0.59" if refund else "-3.00",
        "net": Decimal(gross) + Decimal("0.59" if refund else "-3.00"),
    }
    return Payment.objects.create(
        transaction_id=transaction_id,
        occurred_at=occurred_at,
        **{**defaults, **values},
    )


@pytest.fixture
def editor(payment_editor):
    payment_editor.user_permissions.add(
        *Permission.objects.filter(
            codename__in=[
                "add_reconciliation",
                "change_reconciliation",
                "view_reconciliation",
            ]
        )
    )
    client = Client()
    client.force_login(payment_editor)
    return client


@pytest.fixture
def year():
    # A reviewed gift, its refund, and payments just outside the period.
    payment("GIFT", "2026-03-01T12:00:00Z", charitable_amount="100.00")
    payment(
        "REFUND",
        "2026-04-01T12:00:00Z",
        gross="-20.00",
        reference_transaction_id="GIFT",
    )
    payment("BEFORE", "2025-12-31T23:59:59Z")
    # 11:30 p.m. Pacific on Dec 31 2026 is Jan 1 2027 in UTC.
    payment("PST_NEW_YEAR", "2027-01-01T07:30:00Z")


def create(client, **values):
    return client.post(ADD_URL, {**YEAR, **MATCHING, **values}, follow=True)


def edit(client, reconciliation, **values):
    data = {**YEAR, **MATCHING, **values}
    return client.post(
        reverse("wagtail_crm_reconciliations:edit", args=[reconciliation.pk]),
        data,
        follow=True,
    )


def test_matching_period_can_be_accepted_and_history_shows_it(
    editor, payment_editor, year
):
    create(editor)
    reconciliation = Reconciliation.objects.get()
    page = editor.get(
        reverse("wagtail_crm_reconciliations:edit", args=[reconciliation.pk])
    ).content.decode()
    assert "Jan 1 2026 00:00 to Dec 31 2026 23:59 UTC" in page
    edit(editor, reconciliation, accept="on")
    reconciliation.refresh_from_db()
    assert reconciliation.accepted_at is not None
    entry = ModelLogEntry.objects.get(
        object_id=str(reconciliation.pk),
        action="wagtail_crm_payments.accept_reconciliation",
    )
    assert entry.user == payment_editor
    assert entry.data["crm"]["gross"] == "100.00"
    assert entry.data["paypal"]["refunds"] == "-20.00"
    history = editor.get(
        reverse("wagtail_crm_reconciliations:history", args=[reconciliation.pk])
    ).content.decode()
    assert "Accepted reconciliation" in history


def test_mismatch_shows_the_difference(editor, year):
    create(editor, paypal_gross="110.00")
    reconciliation = Reconciliation.objects.get()
    page = editor.get(
        reverse("wagtail_crm_reconciliations:edit", args=[reconciliation.pk])
    ).content.decode()
    assert "<strong>-10.00</strong>" in page


@pytest.mark.parametrize("blocker", ["blank amount", "unmatched refund"])
def test_open_review_work_blocks_acceptance(editor, year, blocker):
    if blocker == "blank amount":
        payment("BLANK", "2026-05-01T12:00:00Z")
    else:
        payment(
            "ORPHAN",
            "2026-06-01T12:00:00Z",
            gross="-5.00",
            reference_transaction_id="MISSING",
        )
    create(editor)
    reconciliation = Reconciliation.objects.get()
    response = edit(editor, reconciliation, accept="on")
    assert "Resolve these payments in the period first" in response.content.decode()
    reconciliation.refresh_from_db()
    assert reconciliation.accepted_at is None


def test_period_runs_on_utc_days(year):
    totals = Reconciliation(
        start=date(2026, 1, 1), end=date(2026, 12, 31)
    ).payments.totals()
    assert totals["count"] == 1
    next_year = Reconciliation(start=date(2027, 1, 1), end=date(2027, 12, 31))
    assert set(next_year.payments.values_list("transaction_id", flat=True)) == {
        "PST_NEW_YEAR"
    }


def test_accepted_reconciliation_cannot_be_changed(editor, year):
    create(editor)
    reconciliation = Reconciliation.objects.get()
    edit(editor, reconciliation, accept="on")
    response = edit(editor, reconciliation, paypal_gross="1.00")
    assert "This reconciliation is accepted." in response.content.decode()
    reconciliation.refresh_from_db()
    assert reconciliation.paypal_gross == Decimal("100.00")
    page = editor.get(
        reverse("wagtail_crm_reconciliations:edit", args=[reconciliation.pk])
    )
    assert page.status_code == 200
    assert "can no longer be changed" in page.content.decode()


def test_one_reconciliation_per_period(editor, year):
    create(editor)
    response = create(editor)
    assert "A reconciliation for this period exists." in response.content.decode()
    assert Reconciliation.objects.count() == 1


def test_period_is_accepted_for_letters(editor, year):
    create(editor)
    reconciliation = Reconciliation.objects.get()
    assert not period_is_accepted(date(2026, 1, 1), date(2026, 12, 31))
    edit(editor, reconciliation, accept="on")
    assert period_is_accepted(date(2026, 1, 1), date(2026, 12, 31))
    assert period_is_accepted(date(2026, 3, 1), date(2026, 3, 31))
    assert not period_is_accepted(date(2026, 12, 1), date(2027, 1, 31))


def test_panel_lists_only_blockers_inside_the_period(editor, year):
    payment("BLANK_2026", "2026-05-01T12:00:00Z")
    payment("BLANK_2027", "2027-05-01T12:00:00Z")
    create(editor)
    reconciliation = Reconciliation.objects.get()
    page = editor.get(
        reverse("wagtail_crm_reconciliations:edit", args=[reconciliation.pk])
    ).content.decode()
    inside = Payment.objects.get(transaction_id="BLANK_2026")
    assert reverse("wagtail_crm_payments:edit", args=[inside.pk]) in page
    assert "BLANK_2027" not in page
    assert (
        "Payments without a charitable amount to resolve before accepting (1):" in page
    )


def test_period_is_shown_in_utc_for_every_staff_member(editor, payment_editor, year):
    profile = UserProfile.get_for_user(payment_editor)
    profile.current_time_zone = "America/Los_Angeles"
    profile.save()
    create(editor)
    url = reverse(
        "wagtail_crm_reconciliations:edit", args=[Reconciliation.objects.get().pk]
    )
    page = editor.get(url).content.decode()
    assert "Jan 1 2026 00:00 to Dec 31 2026 23:59 UTC" in page
