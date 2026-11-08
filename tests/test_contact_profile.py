"""Contact semantics and history independent of the staff editing interface."""

from copy import deepcopy
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from django.core.exceptions import ValidationError

from wagtail_crm.contact_profile import decode_contact, encode_contact, render_name
from wagtail_crm.models import Contact, ContactHistory
from wagtail_crm.services import delete_contact, save_contact


@pytest.mark.parametrize(
    "full", ["Prince", "王小明", "María del Carmen García López", "  supplied name  "]
)
def test_unstructured_name_preserves_supplied_text(full):
    assert render_name({"full": full}) == full


@pytest.mark.parametrize(
    ("components", "separator", "expected"),
    [
        (
            [{"kind": "surname", "value": "王"}, {"kind": "given", "value": "小明"}],
            "",
            "王小明",
        ),
        (
            [
                {"kind": "given", "value": "María del Carmen"},
                {"kind": "surname", "value": "García"},
                {"kind": "surname", "value": "López"},
            ],
            " ",
            "María del Carmen García López",
        ),
        (
            [
                {"kind": "surname", "value": "Smith"},
                {"kind": "separator", "value": ", "},
                {"kind": "given", "value": "Alex"},
            ],
            " ",
            "Smith, Alex",
        ),
        (
            [
                {"kind": "surname", "value": "García"},
                {"kind": "separator", "value": " "},
                {"kind": "surname2", "value": "López"},
            ],
            ", ",
            "García López",
        ),
    ],
)
def test_explicit_component_order_and_separators(components, separator, expected):
    assert (
        render_name(
            {"components": components, "isOrdered": True, "defaultSeparator": separator}
        )
        == expected
    )


@pytest.mark.parametrize(
    "name",
    [
        {},
        {"full": ""},
        {"full": "Alex", "unknown": "ignored?"},
        {"components": [{"kind": "given", "value": "Alex"}], "defaultSeparator": " "},
        {"components": [{"kind": "given", "value": "Alex"}], "isOrdered": True},
        {"components": [], "isOrdered": True, "defaultSeparator": " "},
        {
            "components": [{"kind": "nickname", "value": "Alex"}],
            "isOrdered": True,
            "defaultSeparator": " ",
        },
        {
            "components": [
                {"kind": "separator", "value": ", "},
                {"kind": "given", "value": "Alex"},
            ],
            "isOrdered": True,
            "defaultSeparator": " ",
        },
        {
            "full": "Different",
            "components": [{"kind": "given", "value": "Alex"}],
            "isOrdered": True,
            "defaultSeparator": " ",
        },
    ],
)
def test_invalid_name_is_rejected(name):
    with pytest.raises(ValidationError):
        render_name(name)


def make_card():
    return {
        "@type": "Card",
        "version": "1.0",
        "uid": f"urn:uuid:{uuid4()}",
        "kind": "individual",
        "name": {"full": "王小明"},
        "emails": {"correspondence": {"address": "reader@example.test"}},
        "addresses": {"correspondence": {"full": "王小明\n東京都新宿区\n日本"}},
    }


def test_profile_round_trip_keeps_unicode_and_optional_correspondence():
    card = make_card()
    original = deepcopy(card)
    values = decode_contact(card)
    assert isinstance(values["uid"], UUID)
    assert values["kind"] == Contact.Kind.PERSON
    assert encode_contact(Contact(**values)) == card
    assert card == original


def test_organization_without_correspondence_has_no_invented_details():
    card = make_card()
    card["kind"] = "org"
    card["name"] = {"full": "Example Friends Meeting"}
    del card["emails"]
    del card["addresses"]
    values = decode_contact(card)
    assert values["kind"] == Contact.Kind.ORGANIZATION
    assert values["email"] == ""
    assert values["postal_address"] == ""
    assert encode_contact(Contact(**values)) == card


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("version", "2.0"),
        ("kind", "group"),
        ("uid", "not-a-uuid"),
        ("unknown", "unsupported"),
        (
            "emails",
            {
                "correspondence": {"address": "a@example.test"},
                "other": {"address": "b@example.test"},
            },
        ),
        ("emails", {"correspondence": {"address": "a@example.test", "pref": 1}}),
        ("addresses", {"correspondence": {"full": "Somewhere", "country": "US"}}),
    ],
)
def test_unsupported_card_rejected_without_modifying_input(key, value):
    card = make_card()
    card[key] = value
    original = deepcopy(card)
    with pytest.raises(ValidationError):
        decode_contact(card)
    assert card == original


@pytest.mark.django_db
def test_shared_email_does_not_merge_independent_contacts():
    first = save_contact(Contact(name={"full": "Prince"}, email="shared@example.test"))
    second = save_contact(Contact(name={"full": "王小明"}, email="shared@example.test"))
    assert first.pk != second.pk
    assert first.uid != second.uid
    assert Contact.objects.filter(email="shared@example.test").count() == 2


@pytest.mark.django_db
def test_component_edit_derives_name_and_retains_prior_structure(staff_user):
    contact = save_contact(
        Contact(
            name={
                "components": [
                    {"kind": "given", "value": "Alex"},
                    {"kind": "surname", "value": "Example"},
                ],
                "isOrdered": True,
                "defaultSeparator": " ",
            }
        ),
        actor=staff_user,
    )
    original = deepcopy(contact.name)
    contact.name["components"][0]["value"] = "Jordan"
    save_contact(contact, actor=staff_user)
    contact.refresh_from_db()
    assert contact.display_name == "Jordan Example"
    history = contact.history.get(action="updated")
    assert history.before["name"] == original
    assert history.after["display_name"] == "Jordan Example"
    assert history.actor == staff_user
    assert history.origin == "staff"
    assert history.occurred_at is not None

    contact.name = {"full": "Jordan supplied name"}
    save_contact(contact, actor=staff_user)
    assert contact.history.filter(action="updated").count() == 2
    assert (
        contact.history.order_by("pk").last().before["name"]["components"][0]["value"]
        == "Jordan"
    )


@pytest.mark.django_db
def test_service_history_noop_and_deletion_keep_independent_identity(staff_user):
    contact = save_contact(Contact(display_name="Legacy caller"), actor=staff_user)
    identity = contact.uid
    assert contact.name == {"full": "Legacy caller"}
    created = contact.history.get()
    assert created.action == "created"
    assert not created.before
    assert created.after["uid"] == str(identity)
    save_contact(contact, actor=staff_user)
    assert contact.history.count() == 1
    delete_contact(contact, actor=staff_user)
    history = ContactHistory.objects.filter(contact_uid=identity)
    assert history.count() == 2
    assert not history.exclude(contact=None).exists()
    deleted = history.get(action="deleted")
    assert deleted.before["display_name"] == "Legacy caller"
    assert not deleted.after


@pytest.mark.django_db
def test_audit_failure_rolls_back_contact_update():
    contact = save_contact(Contact(name={"full": "Original"}))
    contact.name = {"full": "Changed"}
    with (
        patch.object(
            ContactHistory,
            "save",
            side_effect=RuntimeError("audit unavailable"),
        ),
        pytest.raises(RuntimeError, match="audit unavailable"),
    ):
        save_contact(contact)
    contact.refresh_from_db()
    assert contact.display_name == "Original"
    assert contact.history.count() == 1


@pytest.mark.django_db
def test_uid_cannot_be_reassigned():
    contact = save_contact(Contact(name={"full": "Stable identity"}))
    original_uid = contact.uid
    contact.uid = uuid4()
    with pytest.raises(ValidationError):
        contact.save()
    contact.refresh_from_db()
    assert contact.uid == original_uid


@pytest.mark.django_db
def test_encoding_invalid_legacy_email_does_not_repair_stored_record():
    contact = save_contact(Contact(name={"full": "Legacy email"}))
    Contact.objects.filter(pk=contact.pk).update(email="invalid legacy email")
    contact.refresh_from_db()
    original_history_count = contact.history.count()
    with pytest.raises(ValidationError):
        encode_contact(contact)
    contact.refresh_from_db()
    assert contact.email == "invalid legacy email"
    assert contact.history.count() == original_history_count


@pytest.mark.django_db
@pytest.mark.parametrize("operation", ["create", "delete"])
def test_audit_failure_rolls_back_creation_and_deletion(operation):
    contact = Contact(name={"full": "Atomic contact"})
    if operation == "delete":
        save_contact(contact)
    operation_function = save_contact if operation == "create" else delete_contact
    original_count = Contact.objects.count()
    original_history_count = ContactHistory.objects.count()
    with (
        patch.object(
            ContactHistory,
            "save",
            side_effect=RuntimeError("audit unavailable"),
        ),
        pytest.raises(RuntimeError, match="audit unavailable"),
    ):
        operation_function(contact)
    assert Contact.objects.count() == original_count
    assert ContactHistory.objects.count() == original_history_count


@pytest.mark.django_db
@pytest.mark.parametrize("operation", [save_contact, delete_contact])
def test_stale_instance_cannot_replace_or_delete_a_newer_decision(operation):
    contact = save_contact(Contact(name={"full": "Original"}))
    stale = Contact.objects.get(pk=contact.pk)
    contact.name = {"full": "Reviewed newer name"}
    save_contact(contact)
    stale.email = "later@example.test"
    with pytest.raises(ValidationError):
        operation(stale)
    contact.refresh_from_db()
    assert contact.display_name == "Reviewed newer name"
    assert contact.email == ""
    assert contact.history.count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize("operation", [save_contact, delete_contact])
def test_deleted_instance_cannot_be_recreated_or_deleted_again(operation):
    contact = save_contact(Contact(name={"full": "Deleted"}))
    stale = Contact.objects.get(pk=contact.pk)
    identity = contact.uid
    delete_contact(contact)
    with pytest.raises(ValidationError):
        operation(stale)
    assert not Contact.objects.filter(uid=identity).exists()
    assert ContactHistory.objects.filter(contact_uid=identity).count() == 2


@pytest.mark.django_db
def test_failed_create_history_can_retry_the_same_instance():
    contact = Contact(name={"full": "Retryable creation"})
    identity = contact.uid
    with (
        patch.object(
            ContactHistory,
            "save",
            side_effect=RuntimeError("audit unavailable"),
        ),
        pytest.raises(RuntimeError, match="audit unavailable"),
    ):
        save_contact(contact)
    assert not Contact.objects.filter(uid=identity).exists()
    save_contact(contact)
    contact.refresh_from_db()
    assert contact.uid == identity
    assert contact.display_name == "Retryable creation"
    assert contact.history.get().action == "created"


@pytest.mark.django_db
def test_partial_email_save_preserves_a_newer_canonical_name():
    contact = save_contact(Contact(name={"full": "Original"}))
    stale = Contact.objects.get(pk=contact.pk)
    contact.name = {"full": "Newer canonical name"}
    save_contact(contact)
    stale.email = "correspondence@example.test"
    stale.save(update_fields=["email"])
    contact.refresh_from_db()
    assert contact.name == {"full": "Newer canonical name"}
    assert contact.display_name == "Newer canonical name"
    assert contact.email == "correspondence@example.test"


@pytest.mark.django_db
def test_empty_update_fields_is_a_complete_noop():
    contact = save_contact(Contact(name={"full": "Original"}))
    contact.name = {"full": "Not saved"}
    contact.email = "unsaved@example.test"
    contact.save(update_fields=[])
    contact.refresh_from_db()
    assert contact.name == {"full": "Original"}
    assert contact.display_name == "Original"
    assert contact.email == ""
    assert contact.history.count() == 1


@pytest.mark.django_db
def test_new_conflicting_structured_full_is_rejected():
    contact = Contact(
        name={
            "full": "Contradiction",
            "components": [{"kind": "given", "value": "Alex"}],
            "isOrdered": True,
            "defaultSeparator": " ",
        }
    )
    with pytest.raises(ValidationError):
        save_contact(contact)
    assert not Contact.objects.exists()
    assert not ContactHistory.objects.exists()


@pytest.mark.django_db
def test_explicit_stale_revision_is_rejected_without_history():
    contact = save_contact(Contact(name={"full": "Original"}))
    revision = contact.revision
    contact.email = "first@example.test"
    save_contact(contact, expected_revision=revision)
    contact.email = "second@example.test"
    with pytest.raises(ValidationError):
        save_contact(contact, expected_revision=revision)
    contact.refresh_from_db()
    assert contact.email == "first@example.test"
    assert contact.history.count() == 2
