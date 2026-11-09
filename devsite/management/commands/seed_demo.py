from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from wagtail_crm.contacts.models import Contact


class Command(BaseCommand):
    help = "Create synthetic development contacts and a CRM Editors permission group."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            message = "Demo seeding is available only with DEBUG enabled."
            raise CommandError(message)
        for values in (
            {
                "given_name": "Alex",
                "family_name": "Example",
                "email": "alex@example.invalid",
            },
            {
                "given_name": "Jordan",
                "family_name": "Sample",
                "email": "jordan@example.invalid",
            },
            {
                "kind": Contact.Kind.ORGANIZATION,
                "name": "Example Friends Meeting",
                "email": "clerk@example.invalid",
            },
        ):
            Contact.objects.get_or_create(email=values["email"], defaults=values)
        editors, _ = Group.objects.get_or_create(name="CRM Editors")
        editors.permissions.add(
            *Permission.objects.filter(content_type__app_label="wagtail_crm_contacts"),
            Permission.objects.get(
                content_type__app_label="wagtailadmin", codename="access_admin"
            ),
        )
        self.stdout.write(
            self.style.SUCCESS("Synthetic contacts and CRM Editors group are ready.")
        )
        self.stdout.write(
            "Create your local login with: mise exec -- uv run --locked python manage.py createsuperuser"
        )
