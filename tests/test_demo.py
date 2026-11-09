import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError

from wagtail_crm.contacts.models import Contact

pytestmark = pytest.mark.django_db


def test_demo_seed_is_repeatable_and_does_not_create_logins(
    settings, django_user_model
):
    settings.DEBUG = True
    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)
    assert Contact.objects.count() == 3
    assert not django_user_model.objects.exists()
    group = Group.objects.get(name="CRM Editors")
    assert group.permissions.filter(codename="access_admin").exists()
    assert group.permissions.filter(codename="change_contact").exists()
    assert group.permissions.filter(codename="add_payment").exists()
    assert not group.permissions.filter(codename="change_payment").exists()
    assert not group.permissions.filter(codename="change_user").exists()


def test_demo_seed_is_disabled_outside_debug(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="only with DEBUG"):
        call_command("seed_demo")
    assert not Contact.objects.exists()


def test_seed_does_not_overwrite_staff_edits(settings):
    settings.DEBUG = True
    contact = Contact.objects.create(
        given_name="Edited", family_name="Contact", email="alex@example.invalid"
    )
    call_command("seed_demo", verbosity=0)
    contact.refresh_from_db()
    assert contact.given_name == "Edited"
    assert contact.family_name == "Contact"
