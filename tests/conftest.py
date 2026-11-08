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
