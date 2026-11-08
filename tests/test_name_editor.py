"""Structured names use the same atomic contact operations as supplied names."""

import pytest
from django.urls import reverse

from wagtail_crm.forms import ContactForm
from wagtail_crm.models import Contact
from wagtail_crm.services import save_contact

pytestmark = pytest.mark.django_db


def parts_payload(contact=None, **changes):
    payload = {
        "name_mode": "structured",
        "name_kind": ["given", "surname", "surname"],
        "name_value": ["Diego", "Rivera", "Barrientos"],
        "name_separator": " ",
        "kind": "person",
        "email": "",
    }
    if contact:
        payload["expected_revision"] = contact.revision
    return payload | changes


def test_repeated_parts_edit_and_representation_history(client, contact_editor):
    client.force_login(contact_editor)
    contact = save_contact(Contact(name={"full": "Diego Rivera Barrientos"}))
    url = reverse("wagtail_crm_contacts:edit", args=[contact.pk])
    assert client.post(url, parts_payload(contact)).status_code == 302
    contact.refresh_from_db()
    assert contact.display_name == "Diego Rivera Barrientos"
    assert contact.history.first().before["name"] == {"full": contact.display_name}
    assert len(contact.name["components"]) == 3
    assert (
        client.post(
            url,
            parts_payload(contact, name_value=["Diego Luis", "Rivera", "Barrientos"]),
        ).status_code
        == 302
    )
    contact.refresh_from_db()
    assert contact.display_name == "Diego Luis Rivera Barrientos"
    structured = contact.name
    assert (
        client.post(
            url,
            {
                "name_mode": "supplied",
                "name": contact.display_name,
                "kind": "person",
                "email": "",
                "expected_revision": contact.revision,
            },
        ).status_code
        == 302
    )
    contact.refresh_from_db()
    assert contact.name == {"full": contact.display_name}
    assert contact.history.first().before["name"] == structured


@pytest.mark.parametrize("separator", ["", " ", "・"])
def test_exact_formatting_survives_correspondence_edit(
    client, contact_editor, separator
):
    structured = {
        "components": [
            {"kind": "surname", "value": "王"},
            {"kind": "separator", "value": " / "},
            {"kind": "given", "value": "小明"},
            {"kind": "surname2", "value": "van Berg"},
        ],
        "isOrdered": True,
        "defaultSeparator": separator,
        "full": f"王 / 小明{separator}van Berg",
    }
    contact = save_contact(Contact(name=structured))
    client.force_login(contact_editor)
    url = reverse("wagtail_crm_contacts:edit", args=[contact.pk])
    response = client.get(url)
    assert response.context["form"]["name"].value() == structured
    assert (
        client.post(
            url,
            parts_payload(
                contact,
                name_kind=[p["kind"] for p in structured["components"]],
                name_value=[p["value"] for p in structured["components"]],
                name_separator=separator,
                email="new@example.test",
            ),
        ).status_code
        == 302
    )
    contact.refresh_from_db()
    assert contact.name == structured


@pytest.mark.parametrize(
    ("kinds", "values"),
    [
        (["given"], ["   "]),
        (["given", "separator"], ["Alex", "-"]),
        (["separator", "given"], ["-", "Alex"]),
        (["unsupported"], ["Alex"]),
        ([], []),
        (["given", "surname"], ["Alex"]),
    ],
)
def test_invalid_parts_preserve_work_without_mutation(
    client, contact_editor, kinds, values
):
    contact = save_contact(Contact(name={"full": "Original"}))
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        parts_payload(contact, name_kind=kinds, name_value=values),
    )
    assert response.status_code == 200
    assert response.context["form"].errors["name"]
    assert response.context["form"]["name"].value()["values"] == values
    contact.refresh_from_db()
    assert contact.name == {"full": "Original"}
    assert contact.history.count() == 1


def test_zero_space_surname_first_and_stale_edit(client, contact_editor):
    client.force_login(contact_editor)
    assert (
        client.post(
            reverse("wagtail_crm_contacts:add"),
            parts_payload(
                name_kind=["surname", "given"],
                name_value=["王", "小明"],
                name_separator="",
            ),
        ).status_code
        == 302
    )
    contact = Contact.objects.get()
    assert contact.display_name == "王小明"
    stale = parts_payload(
        contact,
        name_kind=["surname", "given"],
        name_value=["王", "大明"],
        name_separator="",
    )
    contact.email = "newer@example.test"
    save_contact(contact)
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]), stale
    )
    assert response.context["form"].non_field_errors()
    assert response.context["form"]["name"].value()["values"] == ["王", "大明"]
    contact.refresh_from_db()
    assert contact.display_name == "王小明"
    assert contact.history.count() == 2


def test_unknown_entry_mode_is_rejected():
    from django.http import QueryDict

    data = QueryDict("name_mode=unexpected&name=Example&kind=person")
    assert not ContactForm(data=data).is_valid()


def test_form_accepts_plain_dictionary_component_lists():
    form = ContactForm(data=parts_payload())
    assert form.is_valid(), form.errors
    assert form.save().display_name == "Diego Rivera Barrientos"


def test_form_accepts_plain_dictionary_single_component():
    form = ContactForm(data=parts_payload(name_kind="given", name_value="Sukarno"))
    assert form.is_valid(), form.errors
    assert form.save().display_name == "Sukarno"


@pytest.mark.parametrize(
    "changes",
    [
        {"name_mode": "supplied", "name": "A\x00B"},
        {"name_value": ["A\x00B", "Rivera", "Barrientos"]},
        {"name_separator": "\x00"},
        {
            "name_kind": ["given", "separator", "surname"],
            "name_value": ["A", "\x00", "B"],
        },
    ],
)
def test_null_characters_are_field_errors_before_write(changes):
    form = ContactForm(data=parts_payload(**changes))
    assert not form.is_valid()
    assert "Null characters are not allowed." in form.errors["name"]
    assert not Contact.objects.exists()


def test_widget_errors_and_disabled_attrs_reach_visible_controls():
    form = ContactForm(data=parts_payload(name_value=["", "Rivera", "Barrientos"]))
    assert not form.is_valid()
    html = str(form["name"])
    assert 'id="id_name" tabindex="-1"' in html
    assert 'aria-invalid="true"' in html
    assert 'aria-describedby="id_name_error"' in html
    assert "requires JavaScript" in html
    form.fields["name"].disabled = True
    assert "data-part-value disabled" in str(form["name"])


@pytest.mark.parametrize(
    "payload",
    [
        "{",
        "[]",
        "null",
        "{}",
        '{"mode": "structured"}',
        '{"mode":"structured","full":0,"separator":" ","kinds":[],"values":[]}',
        '{"mode":"structured","full":"","separator":" ","kinds":["given"],"values":[]}',
        '{"mode":"structured","full":"","separator":" ","kinds":[],"values":[null]}',
    ],
)
def test_untrusted_transport_rejects_invalid_payloads(payload):
    form = ContactForm(data=parts_payload(name_payload=payload))
    assert not form.is_valid()
    assert form.errors["name"]
    assert "data-contact-name" in str(form["name"])
    assert not Contact.objects.exists()
