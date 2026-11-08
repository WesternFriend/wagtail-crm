"""Validated, atomic writes for supported contact-management entry points."""

from __future__ import annotations

from copy import copy, deepcopy
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import router, transaction

from .models import Contact, ContactHistory

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


def snapshot_contact(contact: Contact) -> dict:
    """Return a detached snapshot, including the exact displayed name."""
    return {
        "uid": str(contact.uid),
        "name": deepcopy(contact.name),
        "display_name": contact.display_name,
        "kind": contact.kind,
        "email": contact.email,
        "postal_address": contact.postal_address,
    }


def _current_contact(contact: Contact, alias: str, expected_revision: int) -> Contact:
    current = (
        Contact.objects.using(alias).select_for_update().filter(pk=contact.pk).first()
    )
    if current is None:
        message = (
            "This contact has been deleted. Return to Contacts and reload the list."
        )
        raise ValidationError(message)
    if current.revision != expected_revision:
        message = "This contact changed while you were working. Reload it and review the latest details before continuing."
        raise ValidationError(message)
    return current


def save_contact(
    contact: Contact,
    *,
    expected_revision: int | None = None,
    actor: AbstractBaseUser | None = None,
    origin: str = ContactHistory.Origin.STAFF,
) -> Contact:
    """Validate and save, rejecting stale edits and rolling back failed history writes."""
    alias = router.db_for_write(Contact, instance=contact)
    original_pk, original_revision = contact.pk, contact.revision
    original_state = copy(contact._state)  # noqa: SLF001 -- Django does not restore instance state on rollback.
    revision = contact.revision if expected_revision is None else expected_revision
    try:
        with transaction.atomic(using=alias):
            previous = (
                _current_contact(contact, alias, revision) if contact.pk else None
            )
            before = snapshot_contact(previous) if previous else None
            contact.full_clean()
            after = snapshot_contact(contact)
            if before == after:
                return contact
            contact.revision = previous.revision + 1 if previous else 1
            contact.save(using=alias)
            ContactHistory.objects.using(alias).create(
                contact=contact,
                contact_uid=contact.uid,
                before=before,
                after=after,
                actor_id=actor.pk if actor else None,
                action=ContactHistory.Action.UPDATED
                if previous
                else ContactHistory.Action.CREATED,
                origin=origin,
            )
    except BaseException:
        contact.pk, contact.revision = original_pk, original_revision
        contact._state = original_state  # noqa: SLF001 -- Restore retryable Django instance state after rollback.
        raise
    return contact


def delete_contact(
    contact: Contact,
    *,
    expected_revision: int | None = None,
    actor: AbstractBaseUser | None = None,
    origin: str = ContactHistory.Origin.STAFF,
) -> None:
    """Preserve the last contact state before an authorized, non-stale deletion."""
    alias = router.db_for_write(Contact, instance=contact)
    revision = contact.revision if expected_revision is None else expected_revision
    with transaction.atomic(using=alias):
        current = _current_contact(contact, alias, revision)
        ContactHistory.objects.using(alias).create(
            contact=current,
            contact_uid=current.uid,
            before=snapshot_contact(current),
            after=None,
            actor_id=actor.pk if actor else None,
            action=ContactHistory.Action.DELETED,
            origin=origin,
        )
        current.delete(using=alias)
    contact.pk = None
