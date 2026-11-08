"""Staff tasks and standard Wagtail permissions/activity."""

import pytest
from django.test import Client
from django.urls import reverse
from wagtail.models import ModelLogEntry

from wagtail_crm.contacts.forms import ContactForm
from wagtail_crm.contacts.models import Contact

pytestmark = pytest.mark.django_db


def person(**changes):
    return {
        "kind": "person",
        "given_name": "Alex",
        "family_name": "Example",
        "email": "",
    } | changes


@pytest.mark.parametrize(
    ("given", "family", "display"),
    [
        ("Prince", "", "Prince"),
        ("", "王", "王"),
        ("María del Carmen", "García López", "María del Carmen García López"),
    ],
)
def test_person_names_are_entered_once_and_reopen_populated(given, family, display):
    form = ContactForm(data=person(given_name=given, family_name=family))
    assert form.is_valid(), form.errors
    contact = form.save()
    assert contact.display_name == display
    assert ContactForm(instance=contact)["given_name"].value() == given
    assert ContactForm(instance=contact)["family_name"].value() == family
    assert contact.uid is not None
    assert Contact._meta.app_label == "wagtail_crm_contacts"


def test_unsplit_name_is_editable_and_never_guessed_apart():
    contact = Contact.objects.create(name="  Pat Morgan  ")
    form = ContactForm(instance=contact)
    assert form["name"].value() == "  Pat Morgan  "
    assert "given_name" not in form.fields
    form = ContactForm(
        instance=contact,
        data={"kind": "person", "name": "  Pat Morgan  ", "email": "pat@example.test"},
    )
    assert form.is_valid(), form.errors
    form.save()
    contact.refresh_from_db()
    assert contact.name == contact.display_name == "  Pat Morgan  "
    assert not contact.given_name
    assert not contact.family_name
    form = ContactForm(instance=contact, data={"kind": "person", "name": "Pat Updated"})
    assert form.is_valid(), form.errors
    form.save()
    assert contact.display_name == "Pat Updated"


@pytest.mark.parametrize(
    ("data", "field"),
    [
        (person(given_name="", family_name=""), "given_name"),
        ({"kind": "organization", "name": ""}, "name"),
        (person(email="invalid@local"), "email"),
    ],
)
def test_validation_retains_entered_work(data, field):
    form = ContactForm(data=data | {"postal_address": "Example Street\nFinland"})
    assert not form.is_valid()
    assert field in form.errors
    assert form["postal_address"].value() == "Example Street\nFinland"
    assert not Contact.objects.exists()


def test_type_change_uses_organization_name_without_person_fields():
    contact = Contact.objects.create(given_name="Alex", family_name="Example")
    form = ContactForm(
        instance=contact,
        data={
            "kind": "organization",
            "name": "Example Meeting",
            "given_name": "Ignored",
            "family_name": "Ignored",
        },
    )
    assert form.is_valid(), form.errors
    form.save()
    contact.refresh_from_db()
    assert contact.display_name == "Example Meeting"
    assert not contact.given_name
    assert not contact.family_name


def test_model_partial_save_keeps_display_name_derived(django_assert_num_queries):
    contact = Contact.objects.create(given_name="Before")
    contact.given_name = "After"
    with django_assert_num_queries(1):
        contact.save(update_fields=["given_name"])
    contact.refresh_from_db()
    assert contact.display_name == "After"


@pytest.mark.parametrize(
    "action",
    ["index", "add", "edit", "delete", "inspect", "history", "history_results"],
)
def test_staff_without_contact_permissions_cannot_access_data(
    client, staff_user, action
):
    contact = Contact.objects.create(name="Private Example")
    client.force_login(staff_user)
    args = [contact.pk] if action not in {"index", "add"} else []
    response = client.get(reverse(f"wagtail_crm_contacts:{action}", args=args))
    assert response.status_code == 302
    assert "Private Example" not in response.content.decode()
    assert "Contacts" not in client.get(reverse("wagtailadmin_home")).content.decode()


def test_unauthorized_posts_do_not_mutate_contacts(client, staff_user):
    contact = Contact.objects.create(name="Private Example")
    client.force_login(staff_user)
    for action, args in (("add", []), ("edit", [contact.pk]), ("delete", [contact.pk])):
        response = client.post(
            reverse(f"wagtail_crm_contacts:{action}", args=args), person()
        )
        assert response.status_code == 302
    contact.refresh_from_db()
    assert contact.name == "Private Example"
    assert Contact.objects.count() == 1


def test_anonymous_and_csrf_protection(client, contact_editor):
    assert "/admin/login/" in client.get(reverse("wagtail_crm_contacts:index")).url
    protected = Client(enforce_csrf_checks=True)
    protected.force_login(contact_editor)
    assert (
        protected.post(reverse("wagtail_crm_contacts:add"), person()).status_code == 403
    )
    assert not Contact.objects.exists()


def test_stock_actions_history_search_and_deleted_activity(client, contact_editor):
    client.force_login(contact_editor)
    response = client.post(reverse("wagtail_crm_contacts:add"), person())
    assert response.status_code == 302
    contact = Contact.objects.get()
    uid = contact.uid
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        person(family_name="Updated", postal_address="Helsinki\nFinland"),
    )
    assert response.status_code == 302
    contact.refresh_from_db()
    assert contact.display_name == "Alex Updated"
    assert contact.uid == uid
    assert (
        "Alex Updated"
        in client.get(
            reverse("wagtail_crm_contacts:index"), {"q": "Updated"}
        ).content.decode()
    )
    assert (
        "Alex Updated"
        not in client.get(
            reverse("wagtail_crm_contacts:index"), {"q": "No match"}
        ).content.decode()
    )
    response = client.get(reverse("wagtail_crm_contacts:inspect", args=[contact.pk]))
    assert "Helsinki<br>Finland" in response.content.decode()
    history = client.get(reverse("wagtail_crm_contacts:history", args=[contact.pk]))
    assert history.status_code == 200
    assert "reviewer" in history.content.decode()
    entries = ModelLogEntry.objects.filter(
        content_type__app_label="wagtail_crm_contacts", object_id=str(contact.pk)
    )
    assert list(entries.order_by("id").values_list("action", flat=True)) == [
        "wagtail.create",
        "wagtail.edit",
    ]
    assert entries.filter(user=contact_editor).count() == 2
    assert (
        client.post(
            reverse("wagtail_crm_contacts:delete", args=[contact.pk])
        ).status_code
        == 302
    )
    assert not Contact.objects.exists()
    assert entries.filter(action="wagtail.delete", deleted=True).exists()
    assert (
        "Alex Updated"
        in client.get(reverse("wagtailadmin_reports:site_history")).content.decode()
    )
    assert entries.count() == 3


def test_organization_and_existing_name_validation(client, contact_editor):
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {"kind": "organization", "name": "Example Meeting"},
    )
    assert response.status_code == 302
    contact = Contact.objects.get()
    assert contact.name == "Example Meeting"
    assert contact.kind == "organization"
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        {"kind": "organization", "name": "", "email": "kept@example.test"},
    )
    assert response.status_code == 200
    assert response.context["form"].errors["name"] == ["Enter an organization name."]
    assert response.context["form"]["email"].value() == "kept@example.test"
    contact.refresh_from_db()
    assert contact.name == "Example Meeting"


def test_view_only_user_can_inspect_but_cannot_write(client, staff_user):
    from django.contrib.auth.models import Permission

    staff_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtail_crm_contacts", codename="view_contact"
        )
    )
    contact = Contact.objects.create(name="View Example")
    client.force_login(staff_user)
    assert (
        client.get(
            reverse("wagtail_crm_contacts:inspect", args=[contact.pk])
        ).status_code
        == 200
    )
    assert (
        client.post(
            reverse("wagtail_crm_contacts:edit", args=[contact.pk]), person()
        ).status_code
        == 302
    )
    contact.refresh_from_db()
    assert contact.name == "View Example"


def test_site_history_and_exports_do_not_disclose_deleted_contacts(
    client, contact_editor, django_user_model
):
    from django.contrib.auth.models import Permission

    client.force_login(contact_editor)
    client.post(
        reverse("wagtail_crm_contacts:add"),
        {"kind": "organization", "name": "Private Deleted Activity"},
    )
    contact = Contact.objects.get()
    client.post(reverse("wagtail_crm_contacts:delete", args=[contact.pk]))
    assert ModelLogEntry.objects.filter(label="Private Deleted Activity").count() == 2
    denied = django_user_model.objects.create_user("report-denied", is_staff=True)
    denied.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtailadmin", codename="access_admin"
        )
    )
    denied_client = Client()
    denied_client.force_login(denied)
    for route in ("site_history", "site_history_results"):
        for query in ({}, {"export": "csv"}):
            response = denied_client.get(
                reverse(f"wagtailadmin_reports:{route}"), query
            )
            assert response.status_code == 200
            content = (
                b"".join(response.streaming_content)
                if response.streaming
                else response.content
            )
            assert b"Private Deleted Activity" not in content
