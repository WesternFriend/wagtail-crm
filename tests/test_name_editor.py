"""Simple staff fields preserve names beyond the editor's supported scope."""

from copy import deepcopy

import pytest
from django.urls import reverse

from wagtail_crm.forms import ContactForm
from wagtail_crm.models import Contact, ContactHistory
from wagtail_crm.services import save_contact

pytestmark = pytest.mark.django_db


def payload(contact=None, **changes):
    data = {"given_name": "", "surname": "", "kind": "person", "email": ""}
    if contact:
        data["expected_revision"] = contact.revision
    return data | changes


@pytest.mark.parametrize(
    ("given", "surname", "full"),
    [
        ("Sukarno", "", "Sukarno"),
        ("", "王", "王"),
        ("Mary Beth", "van Berg", "Mary Beth van Berg"),
        ("小明", "王", "小明 王"),
    ],
)
def test_new_person_uses_known_parts_without_parsing(given, surname, full):
    form = ContactForm(data=payload(given_name=given, surname=surname))
    assert form.is_valid(), form.errors
    contact = form.save()
    assert contact.display_name == full
    assert contact.name["components"] == [
        {"kind": kind, "value": value}
        for kind, value in (("given", given), ("surname", surname))
        if value
    ]


def test_blank_new_name_preserves_entered_correspondence(client, contact_editor):
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        payload(
            given_name="  ",
            email="new@example.test",
            postal_address="Tokyo\nJapan",
        ),
    )
    form = response.context["form"]
    assert form.errors["given_name"] == ["Enter a given name or surname."]
    assert form["email"].value() == "new@example.test"
    assert form["postal_address"].value() == "Tokyo\nJapan"
    assert not Contact.objects.exists()
    assert not ContactHistory.objects.exists()


@pytest.mark.parametrize(
    "name",
    [
        {"full": "Mary Beth van Berg"},
        {
            "components": [
                {"kind": "given", "value": "Diego"},
                {"kind": "surname", "value": "Rivera"},
                {"kind": "surname", "value": "Barrientos"},
            ],
            "isOrdered": True,
            "defaultSeparator": " ",
        },
        {
            "components": [
                {"kind": "surname", "value": "王"},
                {"kind": "given", "value": "小明"},
            ],
            "isOrdered": True,
            "defaultSeparator": "",
        },
        {
            "components": [
                {"kind": "surname", "value": "王"},
                {"kind": "separator", "value": " / "},
                {"kind": "given", "value": "小明"},
            ],
            "isOrdered": True,
            "defaultSeparator": "・",
        },
        {
            "components": [{"kind": "given", "value": "Alex\r\nPat"}],
            "isOrdered": True,
            "defaultSeparator": " ",
        },
    ],
)
def test_existing_names_survive_correspondence_edits_exactly(
    client, contact_editor, name
):
    contact = save_contact(Contact(name=deepcopy(name)))
    original = deepcopy(contact.name)
    client.force_login(contact_editor)
    url = reverse("wagtail_crm_contacts:edit", args=[contact.pk])
    form = client.get(url).context["form"]
    data = payload(
        contact,
        given_name=form["given_name"].value() or "",
        surname=form["surname"].value() or "",
        email="new@example.test",
    )
    if not form.original_parts:
        assert "Current name:" in str(form.fields["given_name"].help_text)
    assert client.post(url, data).status_code == 302
    contact.refresh_from_db()
    assert contact.name == original


@pytest.mark.parametrize("separator", ["", " ", "・"])
@pytest.mark.parametrize(
    ("given", "surname", "expected"),
    [("大明", "王", "王 / 大明"), ("小明", "李", "李 / 小明")],
)
def test_simple_known_parts_keep_order_and_separators_when_corrected(
    separator, given, surname, expected
):
    name = {
        "components": [
            {"kind": "surname", "value": "王"},
            {"kind": "separator", "value": " / "},
            {"kind": "given", "value": "小明"},
        ],
        "isOrdered": True,
        "defaultSeparator": separator,
    }
    contact = save_contact(Contact(name=name))
    previous = deepcopy(contact.name)
    form = ContactForm(
        instance=contact, data=payload(contact, given_name=given, surname=surname)
    )
    assert form.is_valid(), form.errors
    form.save()
    contact.refresh_from_db()
    assert contact.display_name == expected
    assert contact.name["components"] == [
        {"kind": "surname", "value": surname},
        {"kind": "separator", "value": " / "},
        {"kind": "given", "value": given},
    ]
    assert contact.name["defaultSeparator"] == separator
    assert contact.history.first().before["name"] == previous


def test_replacement_retains_complex_name_in_history():
    contact = save_contact(Contact(name={"full": "王小明"}))
    form = ContactForm(
        instance=contact, data=payload(contact, given_name="大明", surname="王")
    )
    assert form.is_valid(), form.errors
    form.save()
    assert contact.display_name == "大明 王"
    assert contact.history.first().before["name"] == {"full": "王小明"}


@pytest.mark.parametrize("field", ["given_name", "surname", "organization_name"])
def test_null_characters_rejected_before_mutation(field):
    form = ContactForm(
        data=payload(
            kind="organization" if field == "organization_name" else "person",
            **{field: "A\x00B"},
        )
    )
    assert not form.is_valid()
    assert "Null characters are not allowed." in form.errors[field]
    assert not Contact.objects.exists()


def test_organization_requires_its_name_and_uses_one_plain_field():
    form = ContactForm(
        data=payload(kind="organization", organization_name="Example Meeting")
    )
    assert form.is_valid(), form.errors
    assert form.save().name == {"full": "Example Meeting"}
    invalid = ContactForm(data=payload(kind="organization", given_name="Ignored"))
    assert not invalid.is_valid()
    assert invalid.errors["organization_name"] == ["Enter an organization name."]


def test_removing_a_known_component_is_a_recorded_replacement():
    contact = save_contact(
        Contact(
            name={
                "components": [
                    {"kind": "given", "value": "Alex"},
                    {"kind": "surname", "value": "Example"},
                ],
                "isOrdered": True,
                "defaultSeparator": "・",
            }
        )
    )
    form = ContactForm(instance=contact, data=payload(contact, given_name="Alex"))
    assert form.is_valid(), form.errors
    form.save()
    assert contact.display_name == "Alex"
    assert len(contact.history.first().before["name"]["components"]) == 2


@pytest.mark.parametrize("line_break", ["\r", "\n", "\r\n"])
def test_organization_multiline_name_remains_recorded_context(line_break):
    original = {"full": f"Example <Meeting>{line_break}Society"}
    contact = save_contact(Contact(kind="organization", name=original))
    displayed = ContactForm(instance=contact)
    assert not displayed["organization_name"].value()
    assert "Current name:" in str(displayed.fields["organization_name"].help_text)
    assert "&lt;Meeting&gt;" in str(displayed.fields["organization_name"].help_text)
    form = ContactForm(
        instance=contact,
        data=payload(contact, kind="organization", email="new@example.test"),
    )
    assert form.is_valid(), form.errors
    form.save()
    contact.refresh_from_db()
    assert contact.name == original
    replacement = ContactForm(
        instance=contact,
        data=payload(
            contact, kind="organization", organization_name="Replacement Meeting"
        ),
    )
    assert replacement.is_valid(), replacement.errors
    replacement.save()
    contact.refresh_from_db()
    assert contact.name == {"full": "Replacement Meeting"}
    assert contact.history.first().before["name"] == original


@pytest.mark.parametrize(
    ("original_kind", "selected_kind"),
    [("organization", "person"), ("person", "organization")],
)
@pytest.mark.parametrize("full", ["Example <Name>", "Example <Name>\r\nSociety"])
def test_kind_transitions_preserve_unsplit_recorded_name(
    original_kind, selected_kind, full
):
    original = {"full": full}
    contact = save_contact(Contact(kind=original_kind, name=original))
    displayed = ContactForm(instance=contact)
    assert not displayed["given_name"].value()
    assert not displayed["surname"].value()
    assert "Current name:" in str(displayed.fields["given_name"].help_text)
    assert "&lt;Name&gt;" in str(displayed.fields["given_name"].help_text)
    organization_name = displayed["organization_name"].value() or ""
    if "\n" in full:
        assert not organization_name
        assert "Current name:" in str(displayed.fields["organization_name"].help_text)
    else:
        assert organization_name == full
    form = ContactForm(
        instance=contact,
        data=payload(contact, kind=selected_kind, organization_name=organization_name),
    )
    assert form.is_valid(), form.errors
    form.save()
    contact.refresh_from_db()
    assert contact.name == original
    assert contact.kind == selected_kind
    assert contact.history.first().before["name"] == original
    assert contact.history.first().before["kind"] == original_kind


@pytest.mark.parametrize(
    ("kind", "fields"),
    [
        ("person", {"given_name": "Alex", "organization_name": "A\x00B"}),
        (
            "organization",
            {
                "organization_name": "Example Meeting",
                "given_name": "A\x00B",
                "surname": "C\x00D",
            },
        ),
    ],
)
def test_inactive_name_fields_ignore_posted_nulls(kind, fields):
    form = ContactForm(data=payload(kind=kind, **fields))
    assert form.is_valid(), form.errors
    assert form.save().display_name == (
        "Alex" if kind == "person" else "Example Meeting"
    )


def test_person_known_parts_survive_unchanged_organization_transition():
    contact = save_contact(
        Contact(
            name={
                "components": [
                    {"kind": "surname", "value": "王"},
                    {"kind": "given", "value": "小明"},
                ],
                "isOrdered": True,
                "defaultSeparator": "",
            }
        )
    )
    original = deepcopy(contact.name)
    displayed = ContactForm(instance=contact)
    assert displayed["organization_name"].value() == "王小明"
    form = ContactForm(
        instance=contact,
        data=payload(contact, kind="organization", organization_name="王小明"),
    )
    assert form.is_valid(), form.errors
    form.save()
    contact.refresh_from_db()
    assert contact.name == original
    assert contact.kind == "organization"


def test_new_name_fields_explain_requirements():
    form = ContactForm()
    assert (
        form.fields["given_name"].help_text == "Enter a given name, surname, or both."
    )
    assert form.fields["organization_name"].help_text == "Enter the organization name."


@pytest.mark.parametrize("kind", ["person", "organization"])
def test_current_recorded_name_is_emphasized_and_escaped(kind):
    name = {"full": "Pat <Morgan>\nSociety"}
    contact = save_contact(Contact(kind=kind, name=name))
    form = ContactForm(instance=contact)
    field = "organization_name" if kind == "organization" else "given_name"
    help_text = str(form.fields[field].help_text)
    assert "<strong>Current name: Pat &lt;Morgan&gt;\nSociety</strong>" in help_text
    assert "blank to keep it." in help_text
    assert contact.name == name
