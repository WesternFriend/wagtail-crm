"""Staff see which donors are due a letter for a period and issue each (#26)."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from tests.test_letters import ADD_URL, INDEX_URL, issue, payment, reconciliation
from wagtail_crm.contacts.models import Contact
from wagtail_crm.letters.models import Letter, donors_due, letter_values
from wagtail_crm.payments.models import Source

pytestmark = pytest.mark.django_db

DUE_URL = reverse("wagtail_crm_letters:due")


@pytest.fixture
def editor(letter_editor):
    client = Client()
    client.force_login(letter_editor)
    return client


@pytest.fixture
def avery():
    return Contact.objects.create(given_name="Avery", family_name="Example")


@pytest.fixture
def year():
    return reconciliation()


@pytest.fixture
def blake():
    return Contact.objects.create(given_name="Blake", family_name="Sample")


def due(period):
    return {donor.display_name: total for donor, total in donors_due(period)}


def test_list_totals_match_the_letter(avery, blake, year):
    # Avery: a PayPal gift partly refunded, plus a mailed check.
    payment("P1", gross="200.00", donor=avery, charitable_amount="200.00")
    payment("R1", gross="-50.00", reference_transaction_id="P1")
    payment(
        "1001",
        gross="100.00",
        donor=avery,
        charitable_amount="100.00",
        source=Source.CHECK,
    )
    # Blake: a refund larger than one gift's charitable part, not the total.
    payment("P2", donor=blake, charitable_amount="30.00")
    payment("R2", gross="-80.00", reference_transaction_id="P2")
    payment("P3", gross="300.00", donor=blake, charitable_amount="300.00")

    totals = due(year)
    assert totals == {"Avery Example": Decimal("250.00"), "Blake Sample": 300}
    for donor in (avery, blake):
        assert letter_values(donor, year)["total"] == str(totals[donor.display_name])


@pytest.mark.parametrize(
    ("amount", "listed"), [("99.99", False), ("100.00", True), ("100.01", True)]
)
def test_donors_meeting_the_threshold_are_listed(settings, avery, year, amount, listed):
    settings.WAGTAIL_CRM_LETTER_THRESHOLD = 100  # an int, as staff may write it
    payment("P1", gross=amount, donor=avery, charitable_amount=amount)
    assert ("Avery Example" in due(year)) is listed


def test_donors_with_a_letter_leave_the_list(editor, avery, blake, year):
    payment("P1", gross="300.00", donor=avery, charitable_amount="300.00")
    payment("P2", gross="300.00", donor=blake, charitable_amount="300.00")
    issue(editor, avery, year)
    assert list(due(year)) == ["Blake Sample"]

    # A correction never makes the donor due again.
    original = Letter.objects.get()
    issue(editor, corrects=original)
    assert Letter.objects.count() == 2
    assert list(due(year)) == ["Blake Sample"]


def test_page_lists_due_donors_with_links_to_issue(editor, avery, year):
    payment("P1", gross="300.00", donor=avery, charitable_amount="300.00")
    content = editor.get(DUE_URL).content.decode()
    assert "Donors with $250.00 or more in charitable gifts for 2026-01-01" in content
    assert "Avery Example" in content
    assert "300.00" in content
    link = f"{ADD_URL}?donor={avery.pk}&amp;reconciliation={year.pk}"
    assert link in content
    assert f'href="{DUE_URL}"' in editor.get(INDEX_URL).content.decode()


def test_only_accepted_periods_are_offered(editor, avery):
    open_period = reconciliation(accepted=False)
    open_period.start = open_period.start.replace(year=2025)
    open_period.end = open_period.end.replace(year=2025)
    open_period.save()
    payment("P1", gross="300.00", donor=avery, charitable_amount="300.00")
    content = editor.get(DUE_URL).content.decode()
    assert "No period is accepted yet" in content
    assert "Avery Example" not in content

    accepted = reconciliation()
    response = editor.get(DUE_URL, {"reconciliation": open_period.pk})
    assert response.context["period"] == accepted
    assert response.context["form"].fields["reconciliation"].queryset.get() == (
        accepted
    )


def test_issue_link_fills_the_form_and_issues(editor, avery, year):
    payment("P1", gross="300.00", donor=avery, charitable_amount="300.00")
    page = editor.get(ADD_URL, {"donor": avery.pk, "reconciliation": year.pk})
    form = page.context["form"]
    assert form["donor"].value() == str(avery.pk)
    assert form["reconciliation"].value() == str(year.pk)
    issue(editor, avery, year)
    assert Letter.objects.get().donor == avery
    assert due(year) == {}


@pytest.mark.parametrize("donor_id", ["999999", "abc", ""])
def test_unknown_ids_leave_the_fields_empty(editor, year, donor_id):
    response = editor.get(ADD_URL, {"donor": donor_id, "reconciliation": "x"})
    assert response.status_code == 200
    assert "selected>" not in response.content.decode().split('name="donor"')[1][:200]


def test_a_tampered_donor_gets_the_forms_errors(editor, avery, blake, year):
    payment("P1", gross="300.00", donor=avery, charitable_amount="300.00")
    editor.get(ADD_URL, {"donor": blake.pk, "reconciliation": year.pk})
    response = issue(editor, blake, year, issue_letter="1")
    assert response.status_code == 200
    assert response.context["form"].errors
    assert not Letter.objects.exists()


def test_viewers_without_letter_add_see_no_issue_links(staff_user, avery, year):
    staff_user.user_permissions.add(Permission.objects.get(codename="view_letter"))
    viewer = Client()
    viewer.force_login(staff_user)
    payment("P1", gross="300.00", donor=avery, charitable_amount="300.00")
    content = viewer.get(DUE_URL).content.decode()
    assert "Avery Example" in content
    assert "?donor=" not in content


def test_users_without_letter_view_cannot_open_the_list(staff_user):
    client = Client()
    client.force_login(staff_user)
    assert client.get(DUE_URL).status_code in (302, 403)
