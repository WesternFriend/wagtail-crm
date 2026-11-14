"""Every CRM admin URL refuses a user without CRM permissions alike (#31).

URLs come from the resolver, so a new view is covered without editing this
file. For a signed-in admin user with no CRM permissions, an existing and a
missing record get the same refusal, no donor name appears, and a POST
adds, edits or deletes nothing.
"""

import pytest
from django.test import Client
from django.urls import URLPattern, URLResolver, get_resolver, reverse

from wagtail_crm.contacts.models import Contact
from wagtail_crm.letters.models import Dispatch, Letter
from wagtail_crm.payments.models import Payment, Reconciliation, Source

pytestmark = pytest.mark.django_db

NAME = "Zebulon"
MISSING = 1000  # added to a real pk
MINIMUM_URLS = 51  # today's count: a resolver change must not test nothing

# The record each namespace's pk-taking URLs point at.
RECORD = {
    "wagtail_crm_contacts": "contact",
    "wagtail_crm_contact_chooser": "contact",
    "wagtail_crm_payments": "payment",
    "wagtail_crm_reconciliations": "reconciliation",
    "wagtail_crm_letters": "letter",
    "wagtail_crm_dispatches": "dispatch",
}

# Query parameters views read, and the record each names.
QUERY = {
    "wagtail_crm_dispatches:add": {"letter": "letter"},
    "wagtail_crm_letters:add": {
        "corrects": "letter",
        "donor": "contact",
        "reconciliation": "reconciliation",
    },
    "wagtail_crm_letters:due": {"reconciliation": "reconciliation"},
    "wagtail_crm_contact_chooser:chosen_multiple": {"id": "contact"},
}

# URL name: why an existing and a missing record may be refused differently.
# None today: CRMViewSet makes Wagtail's object views refuse first.
EXEMPT: dict[str, str] = {}

# Enough plausible fields that a view which acted before refusing would save.
POST_DATA = {
    "kind": "person",
    "given_name": "Mallory",
    "family_name": "Sample",
    "charitable_amount": "1.00",
    "received": "2026-02-01",
    "check_number": "4242",
    "amount": "5.00",
    "channel": "post",
    "outcome": "sent",
    "date": "2027-01-03",
    "start": "2025-01-01",
    "end": "2025-12-31",
    "paypal_count": "0",
    "paypal_gross": "0",
    "paypal_fees": "0",
    "paypal_net": "0",
    "paypal_refunds": "0",
    "accept": "on",
}


def crm_urls():
    """(URL name, converter names) for every pattern in a CRM namespace."""
    found = []

    def walk(resolver, namespace):
        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                walk(pattern, pattern.namespace or namespace)
            elif isinstance(pattern, URLPattern) and namespace.startswith(
                "wagtail_crm_"
            ):
                converters = pattern.pattern.converters
                found.append((f"{namespace}:{pattern.name}", dict(converters)))

    walk(get_resolver(), "")
    return found


URLS = crm_urls()


@pytest.fixture
def records():
    contact = Contact.objects.create(given_name=NAME, family_name="Probe")
    common = {
        "occurred_at": "2026-03-01T12:00:00Z",
        "status": "Completed",
        "currency": "USD",
        "fee": "0.00",
        "donor": contact,
    }
    payment = Payment.objects.create(
        transaction_id="SWEEP1",
        name=f"{NAME} Probe",
        type="Donation Payment",
        event_code="T0013",
        gross="300.00",
        net="300.00",
        charitable_amount="300.00",
        **common,
    )
    Payment.objects.create(
        source=Source.CHECK,
        transaction_id="1001",
        type="Check",
        event_code="",
        gross="50.00",
        net="50.00",
        charitable_amount="50.00",
        **common,
    )
    reconciliation = Reconciliation.objects.create(
        start="2026-01-01",
        end="2026-12-31",
        paypal_count=1,
        paypal_gross="300.00",
        paypal_fees="0.00",
        paypal_net="300.00",
        paypal_refunds="0.00",
        accepted_at="2027-01-05T12:00:00Z",
    )
    reconciliation.refresh_from_db()  # dates as dates, for str()
    letter = Letter.objects.create(
        donor=contact,
        reconciliation=reconciliation,
        values={"name": f"{NAME} Probe", "lines": [], "total": "350.00"},
        pdf="letter.pdf",
    )
    dispatch = Dispatch.objects.create(
        letter=letter, channel="post", outcome="failed", note=f"{NAME} moved"
    )
    return {
        "contact": contact,
        "payment": payment,
        "reconciliation": reconciliation,
        "letter": letter,
        "dispatch": dispatch,
    }


@pytest.fixture
def outsider(staff_user):
    """Signed in to the admin, with no CRM permissions."""
    client = Client(raise_request_exception=False)
    client.force_login(staff_user)
    return client


def snapshot():
    """Every CRM row, so a POST that edits as well as one that adds shows up."""
    return [
        list(model.objects.order_by("pk").values())
        for model in (Contact, Payment, Reconciliation, Letter, Dispatch)
    ]


def requests(name, converters, records):
    """(path, query) for an existing record, then a missing one."""
    namespace = name.split(":")[0]
    for offset in (0, MISSING):
        args = []
        for converter_name in converters:
            if converter_name != "pk":
                pytest.fail(f"Add a value for the {converter_name!r} URL argument.")
            if namespace not in RECORD:
                pytest.fail(f"Add a record for the {namespace!r} namespace.")
            args.append(records[RECORD[namespace]].pk + offset)
        query = {
            param: records[record].pk + offset
            for param, record in QUERY.get(name, {}).items()
        }
        yield reverse(name, args=args), query


def test_the_sweep_finds_every_crm_url():
    assert len(URLS) >= MINIMUM_URLS
    names = {name for name, _ in URLS}
    assert set(EXEMPT) <= names, "Remove exemptions for URLs that are gone."
    assert set(QUERY) <= names, "Remove query cases for URLs that are gone."


def assert_refused_alike(send, name, converters, records):
    """Existing and missing records get the same refusal and show no name."""
    statuses = []
    for path, query in requests(name, converters, records):
        response = send(path, query)
        assert response.status_code not in (404, 500) or name in EXEMPT, path
        assert NAME not in response.content.decode(), path
        statuses.append(response.status_code)
    if converters or name in QUERY:
        assert name in EXEMPT or statuses[0] == statuses[1], statuses
    if name not in EXEMPT:
        assert statuses[0] in (302, 403), statuses


@pytest.mark.parametrize(("name", "converters"), URLS, ids=[n for n, _ in URLS])
def test_crm_url_refuses_alike_and_reveals_nothing(outsider, records, name, converters):
    assert_refused_alike(outsider.get, name, converters, records)

    def post(path, query):
        data = {
            **POST_DATA,
            **query,
            "donor": records["contact"].pk,
            "reconciliation": records["reconciliation"].pk,
        }
        return outsider.post(path, data, query_params=query)

    before = snapshot()
    assert_refused_alike(post, name, converters, records)
    assert snapshot() == before
