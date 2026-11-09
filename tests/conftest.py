import pytest
from django.contrib.auth.models import Permission


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
