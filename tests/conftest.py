import pytest
from django.contrib.auth.models import Permission
from django.core.files.storage import FileSystemStorage

from wagtail_crm.letters.models import Letter


@pytest.fixture
def staff_user(django_user_model):
    user = django_user_model.objects.create_user(
        username="reviewer", password="synthetic-test-password", is_staff=True
    )
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtailadmin", codename="access_admin"
        )
    )
    return user


@pytest.fixture
def contact_editor(staff_user):
    staff_user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="wagtail_crm_contacts")
    )
    return staff_user


@pytest.fixture
def payment_editor(staff_user):
    """A CRM Editor's payment permissions, as seeded: view, import and edit."""
    staff_user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="wagtail_crm_payments",
            codename__in=["add_payment", "change_payment", "view_payment"],
        )
    )
    return staff_user


@pytest.fixture(autouse=True)
def letter_storage(monkeypatch, tmp_path):
    """Issued PDFs go to a temporary folder, not the development data.

    Django calls the field's storage callable once, at import, so overriding
    STORAGES in a test would not reach it.
    """
    field = Letter._meta.get_field("pdf")
    monkeypatch.setattr(field, "storage", FileSystemStorage(tmp_path / "letters"))


@pytest.fixture
def letter_editor(staff_user):
    """A CRM Editor's letter permissions, as seeded: issue and view."""
    staff_user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="wagtail_crm_letters",
            codename__in=["add_letter", "view_letter"],
        )
    )
    return staff_user
