"""Processor-independent contacts and their private decision history."""

import uuid
from copy import deepcopy

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, router

from .contact_profile import UUID_VERSION, render_name


class Contact(models.Model):
    """A person or organization, independent of a website login account."""

    class Kind(models.TextChoices):
        PERSON = "person", "Person"
        ORGANIZATION = "organization", "Organization"

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    revision = models.PositiveIntegerField(default=0, editable=False)
    name = models.JSONField(default=dict, blank=True)
    display_name = models.TextField("name", editable=False, blank=True)
    kind = models.CharField(
        "contact type", max_length=20, choices=Kind.choices, default=Kind.PERSON
    )
    email = models.EmailField(blank=True)
    postal_address = models.TextField(blank=True)

    class Meta:
        ordering = ["display_name", "pk"]

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and not update_fields:
            return None
        self.clean()
        if update_fields is not None and {"name", "display_name"} & set(update_fields):
            kwargs["update_fields"] = set(update_fields) | {"name", "display_name"}
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        original = None
        if self.pk:
            alias = self._state.db or router.db_for_read(type(self), instance=self)
            original = (
                type(self)
                .objects.using(alias)
                .filter(pk=self.pk)
                .values("uid", "name", "display_name")
                .first()
            )
        self._clean_name(original)
        if not isinstance(self.uid, uuid.UUID) or self.uid.version != UUID_VERSION:
            message = "Contact UID must use UUID version 4."
            raise ValidationError({"uid": message})
        if original and self.uid != original["uid"]:
            message = "A contact's stable identifier cannot be changed."
            raise ValidationError({"uid": message})

    def _clean_name(self, original):
        if not self.name and self.display_name:
            self.name = {"full": self.display_name}
        try:
            name = deepcopy(self.name)
            if (
                isinstance(name, dict)
                and "components" in name
                and original
                and "components" in original["name"]
                and name.get("full") == original["name"].get("full")
                and name.get("components") != original["name"].get("components")
            ):
                name.pop("full", None)
            self.display_name = render_name(name)
            if "components" in name:
                name["full"] = self.display_name
            self.name = name
        except ValidationError as exc:
            raise ValidationError({"name": exc.messages}) from exc


class ContactHistory(models.Model):
    """Private snapshots retained even when a contact is deleted."""

    contact = models.ForeignKey(
        Contact, null=True, on_delete=models.SET_NULL, related_name="history"
    )
    contact_uid = models.UUIDField(editable=False, db_index=True)
    before = models.JSONField(null=True)
    after = models.JSONField(null=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    occurred_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20)
    origin = models.CharField(max_length=100)

    class Meta:
        ordering = ["-occurred_at", "-pk"]
        default_permissions = ()
        verbose_name = "contact change"
        verbose_name_plural = "contact changes"

    def __str__(self):
        return f"{self.contact_uid}: {self.action}"
