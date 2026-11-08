import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from wagtail_crm.models import Contact

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
        {"display_name": "Unauthorized Example", "kind": "person", "email": ""},
    )
    assert response.status_code == 302
    assert response.url == reverse("wagtailadmin_home")
    assert not Contact.objects.exists()


def test_editor_can_create_contact_without_a_website_account(client, contact_editor):
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {
            "display_name": "Example Meeting",
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
        {"display_name": "Example", "kind": "person", "email": "not-an-email"},
    )
    assert response.status_code == 200
    assert response.context["form"].errors["email"]
    assert not Contact.objects.exists()


def test_mutation_requires_csrf_even_with_contact_permissions(contact_editor):
    client = Client(enforce_csrf_checks=True)
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {"display_name": "Example", "kind": "person", "email": ""},
    )
    assert response.status_code == 403
    assert not Contact.objects.exists()


def test_contacts_may_share_an_email_address():
    Contact.objects.create(display_name="Alex Example", email="shared@example.invalid")
    Contact.objects.create(
        display_name="Jordan Example", email="shared@example.invalid"
    )
    assert Contact.objects.count() == 2
