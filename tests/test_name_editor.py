"""Simple staff fields preserve names beyond the editor's supported scope."""

from copy import deepcopy
from itertools import pairwise

import pytest
from django import forms
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


@pytest.mark.parametrize("original_group", ["given", "surname"])
def test_single_name_can_move_between_known_fields(original_group):
    contact = save_contact(
        Contact(
            name={
                "components": [{"kind": original_group, "value": "Original"}],
                "isOrdered": True,
                "defaultSeparator": " ",
            }
        )
    )
    other_field = "surname" if original_group == "given" else "given_name"
    form = ContactForm(
        instance=contact, data=payload(contact, **{other_field: "Updated"})
    )
    assert form.is_valid(), form.errors
    form.save()
    assert contact.display_name == "Updated"
    assert contact.name["components"] == [
        {
            "kind": "surname" if original_group == "given" else "given",
            "value": "Updated",
        }
    ]
    assert contact.history.first().before["display_name"] == "Original"


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
        **{field: form[field].value() or "" for field in form.person_name_fields},
        email="new@example.test",
    )
    if not form.original_parts:
        assert form["full_name"].value() == contact.display_name
        assert "given_name" not in form.fields
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
    form = ContactForm(instance=contact, data=payload(contact, full_name="大明 王"))
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
def test_organization_multiline_name_is_populated_and_preserved(line_break):
    original = {"full": f"Example <Meeting>{line_break}Society"}
    contact = save_contact(Contact(kind="organization", name=original))
    displayed = ContactForm(instance=contact)
    assert displayed["organization_name"].value() == original["full"]
    assert "&lt;Meeting&gt;" in str(displayed["organization_name"])
    assert isinstance(displayed.fields["organization_name"].widget, forms.Textarea)
    form = ContactForm(
        instance=contact,
        data=payload(
            contact,
            kind="organization",
            organization_name=original["full"]
            .replace("\r\n", "\n")
            .replace("\r", "\n"),
            email="new@example.test",
        ),
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
    assert displayed["full_name"].value() == full
    assert "given_name" not in displayed.fields
    assert displayed["organization_name"].value() == full
    form = ContactForm(
        instance=contact,
        data=payload(
            contact, kind=selected_kind, organization_name=full, full_name=full
        ),
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
    assert not form.fields["organization_name"].help_text


@pytest.mark.parametrize("kind", ["person", "organization"])
def test_populated_name_is_escaped_without_preservation_controls(kind):
    name = {"full": "Pat <Morgan>\nSociety"}
    contact = save_contact(Contact(kind=kind, name=name))
    form = ContactForm(instance=contact)
    field = "organization_name" if kind == "organization" else "full_name"
    assert form[field].value() == name["full"]
    html = str(form.as_p())
    assert "&lt;Morgan&gt;" in html
    assert "Current name:" not in html
    assert "blank to keep" not in html
    assert contact.name == name


@pytest.mark.parametrize(
    ("kind", "field"), [("person", "full_name"), ("organization", "organization_name")]
)
def test_empty_existing_name_errors_retain_other_work(
    client, contact_editor, kind, field
):
    contact = save_contact(Contact(kind=kind, name={"full": "Original"}))
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        payload(
            contact,
            kind=kind,
            **{field: "  "},
            email="retained@example.test",
            postal_address="Retained address",
        ),
    )
    assert response.status_code == 200
    form = response.context["form"]
    assert form.errors[field]
    assert form["email"].value() == "retained@example.test"
    assert form["postal_address"].value() == "Retained address"
    contact.refresh_from_db()
    assert contact.name == {"full": "Original"}
    assert contact.history.count() == 1


@pytest.mark.parametrize("line_break", ["\r", "\n", "\r\n"])
def test_known_multiline_name_preserves_then_edits_components_with_history(line_break):
    original = {
        "components": [{"kind": "given", "value": f"王{line_break}小明"}],
        "isOrdered": True,
        "defaultSeparator": " ",
    }
    contact = save_contact(Contact(name=original))
    original = deepcopy(contact.name)
    form = ContactForm(
        instance=contact,
        data=payload(contact, given_name="王\n小明", email="updated@example.test"),
    )
    assert form.is_valid(), form.errors
    form.save()
    contact.refresh_from_db()
    assert contact.name == original
    form = ContactForm(instance=contact, data=payload(contact, given_name="王大明"))
    assert form.is_valid(), form.errors
    form.save()
    assert contact.name["components"] == [{"kind": "given", "value": "王大明"}]
    assert contact.history.first().before["name"] == original


@pytest.mark.parametrize("surname_kind", ["surname", "surname2"])
def test_repeated_recorded_groups_are_populated_and_preserve_unedited_components(
    surname_kind,
):
    contact = save_contact(
        Contact(
            name={
                "components": [
                    {"kind": "given", "value": "Mary"},
                    {"kind": "given", "value": "Beth"},
                    {"kind": "separator", "value": " / "},
                    {"kind": "surname", "value": "Rivera"},
                    {"kind": "separator", "value": "・"},
                    {"kind": surname_kind, "value": "Barrientos"},
                ],
                "isOrdered": True,
                "defaultSeparator": " ",
            }
        )
    )
    original = deepcopy(contact.name)
    displayed = ContactForm(instance=contact)
    assert "full_name" not in displayed.fields
    assert displayed["given_name"].value() == "Mary Beth"
    assert displayed["surname"].value() == "Rivera・Barrientos"
    unchanged = ContactForm(
        instance=contact,
        data=payload(
            contact,
            given_name="Mary Beth",
            surname="Rivera・Barrientos",
            email="new@example.test",
        ),
    )
    assert unchanged.is_valid(), unchanged.errors
    unchanged.save()
    contact.refresh_from_db()
    assert contact.name == original
    edited = ContactForm(
        instance=contact,
        data=payload(contact, given_name="Mary Jane", surname="Rivera・Barrientos"),
    )
    assert edited.is_valid(), edited.errors
    edited.save()
    contact.refresh_from_db()
    assert contact.name["components"] == [
        original["components"][0] | {"value": "Mary Jane"},
        *original["components"][2:],
    ]
    assert contact.name["defaultSeparator"] == " "
    assert contact.display_name == "Mary Jane / Rivera・Barrientos"
    assert contact.history.first().before["name"] == original


def test_surname2_only_is_known_surname_and_edits_keep_recorded_kind():
    contact = save_contact(
        Contact(
            name={
                "components": [{"kind": "surname2", "value": "王"}],
                "isOrdered": True,
                "defaultSeparator": "",
            }
        )
    )
    displayed = ContactForm(instance=contact)
    assert displayed["surname"].value() == "王"
    form = ContactForm(instance=contact, data=payload(contact, surname="李"))
    assert form.is_valid(), form.errors
    form.save()
    assert contact.name["components"] == [{"kind": "surname2", "value": "李"}]


@pytest.mark.parametrize("original_kind", ["given", "surname", "surname2"])
def test_adding_the_other_name_group_uses_default_given_surname_order(original_kind):
    original_value = "Amina" if original_kind == "given" else "Rivera"
    contact = save_contact(
        Contact(
            name={
                "components": [{"kind": original_kind, "value": original_value}],
                "isOrdered": True,
                "defaultSeparator": " ",
            }
        )
    )
    original = deepcopy(contact.name)
    form = ContactForm(
        instance=contact, data=payload(contact, given_name="Amina", surname="Rivera")
    )
    assert form.is_valid(), form.errors
    form.save()
    assert contact.display_name == "Amina Rivera"
    assert {"kind": original_kind, "value": original_value} in contact.name[
        "components"
    ]
    assert contact.history.first().before["name"] == original


@pytest.mark.parametrize("structured_first", [True, False])
def test_stale_edit_retains_submitted_representation_without_writes(
    client, contact_editor, structured_first
):
    structured = {
        "components": [{"kind": "given", "value": "Original"}],
        "isOrdered": True,
        "defaultSeparator": " ",
    }
    full = {"full": "Other stored name"}
    contact = save_contact(Contact(name=structured if structured_first else full))
    revision = contact.revision
    contact.name = full if structured_first else structured
    save_contact(contact)
    current = deepcopy(contact.name)
    history = list(contact.history.values())
    client.force_login(contact_editor)
    values = (
        {"given_name": "Typed given", "surname": "Typed surname"}
        if structured_first
        else {"full_name": "Typed full"}
    )
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        {
            "kind": "person",
            "email": "typed@example.test",
            "expected_revision": revision,
            **values,
        },
    )
    form = response.context["form"]
    assert "This contact changed while you were editing." in str(
        form.non_field_errors()
    )
    for field, value in values.items():
        assert form[field].value() == value
    assert ("full_name" not in form.fields) == structured_first
    contact.refresh_from_db()
    assert contact.name == current
    assert contact.revision == revision + 1
    assert list(contact.history.values()) == history


@pytest.mark.parametrize("separator", ["", "・", "\r\n"])
@pytest.mark.parametrize("original_group", ["given", "surname"])
def test_new_group_boundary_uses_space_and_preserves_existing_internal_separator(
    separator, original_group
):
    parts = [
        {"kind": original_group, "value": "A"},
        {"kind": original_group, "value": "B"},
    ]
    contact = save_contact(
        Contact(
            name={"components": parts, "isOrdered": True, "defaultSeparator": separator}
        )
    )
    original = deepcopy(contact.name)
    old_value = f"A{separator}B"
    values = (
        {"given_name": old_value, "surname": "New"}
        if original_group == "given"
        else {"given_name": "New", "surname": old_value}
    )
    form = ContactForm(instance=contact, data=payload(contact, **values))
    assert form.is_valid(), form.errors
    form.save()
    assert contact.display_name == (
        f"{old_value} New" if original_group == "given" else f"New {old_value}"
    )
    assert contact.name["defaultSeparator"] == separator
    assert contact.name["components"] == (
        parts
        + [{"kind": "separator", "value": " "}, {"kind": "surname", "value": "New"}]
        if original_group == "given"
        else [
            {"kind": "given", "value": "New"},
            {"kind": "separator", "value": " "},
            *parts,
        ]
    )
    assert contact.history.first().before["name"] == original


@pytest.mark.parametrize("surname_kind", ["surname", "surname2"])
def test_changed_grouped_surname_preserves_given_and_boundary(surname_kind):
    parts = [
        {"kind": "given", "value": "Mary"},
        {"kind": "given", "value": "Beth"},
        {"kind": "separator", "value": " / "},
        {"kind": "surname", "value": "Rivera"},
        {"kind": "separator", "value": "・"},
        {"kind": surname_kind, "value": "Barrientos"},
    ]
    contact = save_contact(
        Contact(name={"components": parts, "isOrdered": True, "defaultSeparator": " "})
    )
    original = deepcopy(contact.name)
    form = ContactForm(
        instance=contact,
        data=payload(contact, given_name="Mary Beth", surname="New surname"),
    )
    assert form.is_valid(), form.errors
    form.save()
    assert contact.name["components"] == [
        *parts[:3],
        {"kind": "surname", "value": "New surname"},
    ]
    assert contact.display_name == "Mary Beth / New surname"
    assert contact.history.first().before["name"] == original


@pytest.mark.parametrize(
    ("given", "surname", "expected"),
    [
        ("X", "S・T", "X・S・T"),
        ("G・H", "Y", "G・Y・H"),
        ("X", "Y", "X・Y"),
        ("", "S・T", "S・T"),
        ("G・H", "", "G・H"),
    ],
)
def test_interleaved_group_edits_and_removals_have_valid_order(
    given, surname, expected
):
    parts = [
        {"kind": "given", "value": "G"},
        {"kind": "separator", "value": "・"},
        {"kind": "surname", "value": "S"},
        {"kind": "separator", "value": "・"},
        {"kind": "given", "value": "H"},
        {"kind": "separator", "value": "・"},
        {"kind": "surname2", "value": "T"},
    ]
    contact = save_contact(
        Contact(name={"components": parts, "isOrdered": True, "defaultSeparator": "・"})
    )
    original = deepcopy(contact.name)
    form = ContactForm(
        instance=contact, data=payload(contact, given_name=given, surname=surname)
    )
    assert form.is_valid(), form.errors
    form.save()
    assert contact.display_name == expected
    components = contact.name["components"]
    assert components[0]["kind"] != "separator"
    assert components[-1]["kind"] != "separator"
    assert all(
        left["kind"] != "separator" or right["kind"] != "separator"
        for left, right in pairwise(components)
    )
    assert contact.history.first().before["name"] == original


def test_full_only_name_null_rejected_without_any_write():
    contact = save_contact(Contact(name={"full": "Original"}))
    original = deepcopy(contact.name)
    revision = contact.revision
    history = list(contact.history.values())
    form = ContactForm(instance=contact, data=payload(contact, full_name="A\x00B"))
    assert not form.is_valid()
    assert "Null characters are not allowed." in form.errors["full_name"]
    contact.refresh_from_db()
    assert contact.name == original
    assert contact.revision == revision
    assert list(contact.history.values()) == history
