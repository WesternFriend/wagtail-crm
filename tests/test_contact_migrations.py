"""Upgrade real legacy rows on the isolated pytest database."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_contact_profile_migration_preserves_legacy_values_and_baseline():
    before = [("wagtail_crm", "0001_initial")]
    after = [("wagtail_crm", "0002_contact_profile")]
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate(before)
        old_apps = executor.loader.project_state(before).apps
        old_contact = old_apps.get_model("wagtail_crm", "Contact")
        rows = [
            old_contact.objects.create(
                display_name="王小明", kind="person", email="shared@example.test"
            ),
            old_contact.objects.create(
                display_name="  Example Friends Meeting  ",
                kind="organization",
                email="shared@example.test",
            ),
            old_contact.objects.create(
                display_name="Prince", kind="person", email="old invalid email"
            ),
        ]
        expected = {row.pk: (row.display_name, row.kind, row.email) for row in rows}

        executor = MigrationExecutor(connection)
        executor.migrate(after)
        apps = executor.loader.project_state(after).apps
        contact_model = apps.get_model("wagtail_crm", "Contact")
        history_model = apps.get_model("wagtail_crm", "ContactHistory")
        contacts = list(contact_model.objects.order_by("pk"))
        assert {contact.pk for contact in contacts} == set(expected)
        assert len({contact.uid for contact in contacts}) == len(expected)
        for contact in contacts:
            name, kind, email = expected[contact.pk]
            assert contact.display_name == name
            assert contact.name == {"full": name}
            assert contact.kind == kind
            assert contact.email == email
            assert contact.postal_address == ""
            assert contact.revision == 0
            baseline = history_model.objects.get(contact_id=contact.pk)
            assert baseline.action == "baseline"
            assert baseline.origin == "migration"
            assert baseline.actor_id is None
            assert baseline.contact_uid == contact.uid
            assert not baseline.before
            assert baseline.after == {
                "uid": str(contact.uid),
                "name": {"full": name},
                "display_name": name,
                "kind": kind,
                "email": email,
                "postal_address": "",
            }
    finally:
        # pytest cleanup and subsequent tests must always see the current schema.
        MigrationExecutor(connection).migrate(latest)


@pytest.mark.django_db(transaction=True)
def test_contact_type_label_migration_preserves_contacts_and_history():
    from wagtail_crm.models import Contact
    from wagtail_crm.services import save_contact

    contact = save_contact(Contact(name={"full": "Pat Morgan"}))
    expected = (contact.pk, contact.uid, contact.name, contact.kind)
    snapshot = contact.history.get().after
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    before = [("wagtail_crm", "0002_contact_profile")]
    try:
        executor.migrate(before)
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        apps = executor.loader.project_state(latest).apps
        migrated_model = apps.get_model("wagtail_crm", "Contact")
        migrated = migrated_model.objects.get(pk=contact.pk)
        assert migrated_model._meta.get_field("kind").verbose_name == "contact type"
        assert (migrated.pk, migrated.uid, migrated.name, migrated.kind) == expected
        assert migrated.history.get().after == snapshot
    finally:
        MigrationExecutor(connection).migrate(latest)
