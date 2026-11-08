"""Preserve legacy contact text and establish an explicit history baseline."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def preserve_contacts(apps, schema_editor):
    Contact = apps.get_model("wagtail_crm", "Contact")
    ContactHistory = apps.get_model("wagtail_crm", "ContactHistory")
    alias = schema_editor.connection.alias
    for contact in Contact.objects.using(alias).all().iterator():
        contact.uid = uuid.uuid4()
        contact.name = {"full": contact.display_name}
        contact.save(using=alias, update_fields=["uid", "name"])
        ContactHistory.objects.using(alias).create(
            contact=contact,
            contact_uid=contact.uid,
            before=None,
            after={
                "uid": str(contact.uid),
                "name": contact.name,
                "display_name": contact.display_name,
                "kind": contact.kind,
                "email": contact.email,
                "postal_address": contact.postal_address,
            },
            action="baseline",
            origin="migration",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("wagtail_crm", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="contact",
            name="revision",
            field=models.PositiveIntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name="contact",
            name="uid",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="contact",
            name="name",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="contact",
            name="postal_address",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="contact",
            name="display_name",
            field=models.TextField(blank=True, editable=False, verbose_name="name"),
        ),
        migrations.CreateModel(
            name="ContactHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("contact_uid", models.UUIDField(db_index=True, editable=False)),
                ("before", models.JSONField(null=True)),
                ("after", models.JSONField(null=True)),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
                ("action", models.CharField(max_length=20)),
                ("origin", models.CharField(max_length=100)),
                (
                    "actor",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "contact",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="history",
                        to="wagtail_crm.contact",
                    ),
                ),
            ],
            options={"ordering": ["-occurred_at", "-pk"], "default_permissions": ()},
        ),
        migrations.RunPython(preserve_contacts, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="contact",
            name="uid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
