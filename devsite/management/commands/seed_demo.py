from typing import Any

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from wagtail_crm.contact_profile import render_name
from wagtail_crm.models import Contact, ContactHistory
from wagtail_crm.services import save_contact


class Command(BaseCommand):
    help = "Create synthetic development contacts and a CRM Editors permission group."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            message = "Demo seeding is available only with DEBUG enabled."
            raise CommandError(message)

        contacts: list[tuple[dict[str, Any], str, str]] = [
            (
                {
                    "components": [
                        {"kind": "given", "value": "Alex"},
                        {"kind": "surname", "value": "Example"},
                    ],
                    "isOrdered": True,
                    "defaultSeparator": " ",
                },
                Contact.Kind.PERSON,
                "alex@example.invalid",
            ),
            (
                {
                    "components": [
                        {"kind": "given", "value": "Jordan"},
                        {"kind": "surname", "value": "Sample"},
                    ],
                    "isOrdered": True,
                    "defaultSeparator": " ",
                },
                Contact.Kind.PERSON,
                "jordan@example.invalid",
            ),
            (
                {"full": "Example Friends Meeting"},
                Contact.Kind.ORGANIZATION,
                "clerk@example.invalid",
            ),
        ]
        for name, kind, email in contacts:
            if not Contact.objects.filter(
                display_name=render_name(name), kind=kind, email=email
            ).exists():
                save_contact(
                    Contact(name=name, kind=kind, email=email),
                    origin=ContactHistory.Origin.DEMO,
                )

        editors, _ = Group.objects.get_or_create(name="CRM Editors")
        editors.permissions.add(
            *Permission.objects.filter(content_type__app_label="wagtail_crm"),
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
