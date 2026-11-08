from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from wagtail_crm.models import Contact, ContactHistory
from wagtail_crm.services import save_contact

pytestmark = pytest.mark.django_db


def test_anonymous_visitor_is_sent_to_login(client):
    response = client.get(reverse("wagtail_crm_contacts:index"))
    assert response.status_code == 302
    assert "/admin/login/" in response.url


@pytest.mark.parametrize("action", ["index", "add", "edit", "delete", "inspect"])
def test_admin_access_alone_does_not_grant_contact_access(client, staff_user, action):
    contact = Contact.objects.create(display_name="Private Example")
    kwargs = {"pk": contact.pk} if action in {"edit", "delete", "inspect"} else {}
    client.force_login(staff_user)
    response = client.get(reverse(f"wagtail_crm_contacts:{action}", kwargs=kwargs))
    assert response.status_code == 302
    assert response.url == reverse("wagtailadmin_home")
    assert b"Private Example" not in response.content


def test_view_only_user_cannot_create_contact(client, staff_user):
    staff_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtail_crm", codename="view_contact"
        )
    )
    client.force_login(staff_user)
    assert client.get(reverse("wagtail_crm_contacts:index")).status_code == 200
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {"name": "Unauthorized Example", "kind": "person", "email": ""},
    )
    assert response.status_code == 302
    assert response.url == reverse("wagtailadmin_home")
    assert not Contact.objects.exists()


def test_editor_can_create_contact_without_a_website_account(client, contact_editor):
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {
            "name": "Example Meeting",
            "kind": "organization",
            "email": "clerk@example.invalid",
        },
    )
    assert response.status_code == 302
    contact = Contact.objects.get(display_name="Example Meeting")
    assert contact.kind == Contact.Kind.ORGANIZATION
    assert contact.email == "clerk@example.invalid"


def test_editor_form_rejects_invalid_email(client, contact_editor):
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {"name": "Example", "kind": "person", "email": "not-an-email"},
    )
    assert response.status_code == 200
    assert response.context["form"].errors["email"]
    assert not Contact.objects.exists()


def test_mutation_requires_csrf_even_with_contact_permissions(contact_editor):
    client = Client(enforce_csrf_checks=True)
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {"name": "Example", "kind": "person", "email": ""},
    )
    assert response.status_code == 403
    assert not Contact.objects.exists()


def test_contacts_may_share_an_email_address():
    Contact.objects.create(display_name="Alex Example", email="shared@example.invalid")
    Contact.objects.create(
        display_name="Jordan Example", email="shared@example.invalid"
    )
    assert Contact.objects.count() == 2


def test_staff_form_has_one_plain_name_and_multiline_address(client, contact_editor):
    client.force_login(contact_editor)
    response = client.get(reverse("wagtail_crm_contacts:add"))
    form = response.context["form"]
    assert [field.name for field in form.visible_fields()] == [
        "name",
        "kind",
        "email",
        "postal_address",
    ]
    assert form["name"].value() == ""
    assert form.fields["name"].widget.input_type == "text"
    assert form.fields["postal_address"].widget.__class__.__name__ == "Textarea"
    assert "separator" not in response.content.decode()


def test_create_edit_inspect_and_delete_retain_private_history(client, contact_editor):
    client.force_login(contact_editor)
    address = "Example Meeting\n〒100-8994 東京都千代田区\nJapan"
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {"name": "王小明", "kind": "person", "email": "", "postal_address": address},
    )
    assert response.status_code == 302
    contact = Contact.objects.get()
    uid = contact.uid
    assert contact.postal_address == address
    assert contact.history.get().actor == contact_editor
    assert contact.history.get().after["name"] == {"full": "王小明"}

    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        {
            "name": "王大明",
            "kind": "person",
            "email": "",
            "postal_address": address,
            "expected_revision": contact.revision,
        },
    )
    assert response.status_code == 302
    contact.refresh_from_db()
    assert contact.uid == uid
    assert contact.name == {"full": "王大明"}
    assert contact.history.count() == 2
    change = contact.history.first()
    assert change.before["display_name"] == "王小明"
    assert change.after["display_name"] == "王大明"
    response = client.get(reverse("wagtail_crm_contacts:inspect", args=[contact.pk]))
    assert response.status_code == 200
    assert "Change history" in response.content.decode()
    assert "王小明" in response.content.decode()
    history = list(contact.history.all())

    response = client.post(reverse("wagtail_crm_contacts:delete", args=[contact.pk]))
    assert response.status_code == 302
    assert not Contact.objects.exists()
    deleted = ContactHistory.objects.filter(contact_uid=uid, action="deleted").get()
    assert deleted.actor == contact_editor
    assert deleted.before["name"] == {"full": "王大明"}
    assert deleted.before["postal_address"] == address
    assert deleted.after is None
    for entry in history:
        entry.refresh_from_db()
        assert entry.contact_id is None
        assert entry.contact_uid == uid


def test_plain_name_editor_retains_unchanged_structure_then_preserves_previous_value(
    client, contact_editor
):
    structured = {
        "components": [
            {"kind": "surname", "value": "王"},
            {"kind": "given", "value": "小明"},
        ],
        "isOrdered": True,
        "defaultSeparator": "",
    }
    contact = save_contact(Contact(name=structured), actor=contact_editor)
    client.force_login(contact_editor)
    url = reverse("wagtail_crm_contacts:edit", args=[contact.pk])
    payload = {
        "name": "王小明",
        "kind": "person",
        "email": "new@example.test",
        "expected_revision": contact.revision,
    }
    assert client.post(url, payload).status_code == 302
    contact.refresh_from_db()
    assert contact.name["components"] == structured["components"]
    payload["name"] = "王大明"
    payload["expected_revision"] = contact.revision
    assert client.post(url, payload).status_code == 302
    contact.refresh_from_db()
    assert contact.name == {"full": "王大明"}
    assert (
        contact.history.first().before["name"]["components"] == structured["components"]
    )


def test_view_only_can_inspect_history_but_not_mutate(client, staff_user):
    staff_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtail_crm", codename="view_contact"
        )
    )
    contact = save_contact(Contact(name={"full": "Private Example"}))
    client.force_login(staff_user)
    response = client.get(reverse("wagtail_crm_contacts:inspect", args=[contact.pk]))
    assert response.status_code == 200
    assert "Private Example" in response.content.decode()
    assert "Change history" in response.content.decode()
    for action in ("edit", "delete"):
        response = client.post(
            reverse(f"wagtail_crm_contacts:{action}", args=[contact.pk])
        )
        assert response.status_code == 302
        assert response.url == reverse("wagtailadmin_home")
    assert contact.history.count() == 1
    assert Contact.objects.filter(pk=contact.pk).exists()


def test_inspect_escapes_contact_and_history_text(client, contact_editor):
    text = "Example <script>alert('synthetic')</script>"
    contact = save_contact(Contact(name={"full": text}, postal_address=text))
    client.force_login(contact_editor)
    response = client.get(reverse("wagtail_crm_contacts:inspect", args=[contact.pk]))
    html = response.content.decode()
    assert response.status_code == 200
    assert "&lt;script&gt;" in html
    assert "<script>alert('synthetic')</script>" not in html


def test_search_uses_updated_name_projection(client, contact_editor):
    contact = save_contact(Contact(name={"full": "Original Example"}))
    contact.name = {"full": "Changed Example"}
    save_contact(contact)
    client.force_login(contact_editor)
    response = client.get(reverse("wagtail_crm_contacts:index"), {"q": "Changed"})
    assert response.status_code == 200
    assert "Changed Example" in response.content.decode()


def test_blank_name_and_invalid_email_do_not_write_history(client, contact_editor):
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {"name": "   ", "kind": "person", "email": "bad"},
    )
    assert response.status_code == 200
    assert response.context["form"].errors["name"]
    assert not Contact.objects.exists()


def test_correspondence_only_edit_records_exact_previous_values(client, contact_editor):
    contact = save_contact(
        Contact(
            name={"full": "Example"},
            email="old@example.test",
            postal_address="Old\nAddress",
        )
    )
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        {
            "name": "Example",
            "kind": "person",
            "email": "new@example.test",
            "postal_address": "New\n住所",
            "expected_revision": contact.revision,
        },
    )
    assert response.status_code == 302
    change = contact.history.first()
    assert change.before["email"] == "old@example.test"
    assert change.after["email"] == "new@example.test"
    assert change.before["postal_address"] == "Old\nAddress"
    assert change.after["postal_address"] == "New\n住所"


def test_stale_form_preserves_newer_contact_and_shows_entered_work(
    client, contact_editor
):
    contact = save_contact(Contact(name={"full": "Example"}))
    original_revision = contact.revision
    contact.email = "newer@example.test"
    save_contact(contact)
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        {
            "name": "Attempted edit",
            "kind": "person",
            "email": "",
            "expected_revision": original_revision,
        },
    )
    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert response.context["form"]["name"].value() == "Attempted edit"
    contact.refresh_from_db()
    assert contact.display_name == "Example"
    assert contact.email == "newer@example.test"
    assert contact.history.count() == 2


def test_edit_requires_its_hidden_revision(client, contact_editor):
    contact = save_contact(Contact(name={"full": "Example"}))
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        {"name": "Changed", "kind": "person", "email": ""},
    )
    assert response.status_code == 200
    assert response.context["form"].errors["expected_revision"]
    contact.refresh_from_db()
    assert contact.display_name == "Example"


def test_form_respects_explicit_initial_name_and_unsaved_structure():
    from wagtail_crm.forms import ContactForm

    contact = Contact(
        name={
            "components": [{"kind": "given", "value": "Alex"}],
            "isOrdered": True,
            "defaultSeparator": " ",
        }
    )
    assert ContactForm(instance=contact)["name"].value() == "Alex"
    assert (
        ContactForm(instance=contact, initial={"name": "Initial"})["name"].value()
        == "Initial"
    )


def test_inspect_shows_kind_changes_and_pages_history(client, contact_editor):
    contact = save_contact(Contact(name={"full": "Example"}))
    contact.kind = Contact.Kind.ORGANIZATION
    save_contact(contact)
    client.force_login(contact_editor)
    url = reverse("wagtail_crm_contacts:inspect", args=[contact.pk])
    html = client.get(url).content.decode()
    assert "Previous kind" in html
    assert "Person" in html
    assert "Recorded kind" in html
    assert "Organization" in html
    for number in range(20):
        contact.email = f"example{number}@example.test"
        save_contact(contact)
    response = client.get(url)
    assert len(response.context["contact_history"]) == 20
    assert response.context["contact_history"].has_next()
    response = client.get(url, {"history_page": 2})
    assert len(response.context["contact_history"]) == 2


def test_inspect_explains_structural_changes_with_same_rendering(
    client, contact_editor
):
    contact = save_contact(Contact(name={"full": "Alex Example"}))
    contact.name = {
        "components": [
            {"kind": "given", "value": "Alex"},
            {"kind": "surname", "value": "Example"},
        ],
        "isOrdered": True,
        "defaultSeparator": " ",
    }
    save_contact(contact)
    client.force_login(contact_editor)
    response = client.get(reverse("wagtail_crm_contacts:inspect", args=[contact.pk]))
    assert (
        "Name structure changed; the displayed name is unchanged."
        in response.content.decode()
    )


def test_changed_contact_during_delete_returns_a_message(client, contact_editor):
    contact = save_contact(Contact(name={"full": "Example"}))
    client.force_login(contact_editor)
    with patch(
        "wagtail_crm.views.delete_contact",
        side_effect=ValidationError("This contact changed. Reload it before deleting."),
    ):
        response = client.post(
            reverse("wagtail_crm_contacts:delete", args=[contact.pk]), follow=True
        )
    assert response.status_code == 200
    assert "Reload it before deleting." in response.content.decode()
    assert Contact.objects.filter(pk=contact.pk).exists()


def test_create_service_validation_error_stays_on_form(client, contact_editor):
    client.force_login(contact_editor)
    with patch(
        "wagtail_crm.forms.save_contact",
        side_effect=ValidationError("The contact could not be saved. Review the name."),
    ):
        response = client.post(
            reverse("wagtail_crm_contacts:add"),
            {"name": "Example", "kind": "person", "email": ""},
        )
    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert response.context["form"]["name"].value() == "Example"
    assert not Contact.objects.exists()
