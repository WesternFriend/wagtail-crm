"""Contact records owned by the contacts domain."""

import uuid

from django.db import models


class Contact(models.Model):
    class Kind(models.TextChoices):
        PERSON = "person", "Person"
        ORGANIZATION = "organization", "Organization"

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    kind = models.CharField(
        "contact type", max_length=20, choices=Kind.choices, default=Kind.PERSON
    )
    given_name = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255, blank=True)
    display_name = models.CharField("name", max_length=511, editable=False, blank=True)
    email = models.EmailField(blank=True)
    postal_address = models.TextField(blank=True)

    class Meta:
        ordering = ["display_name", "pk"]

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        self.display_name = self.name or " ".join(
            part for part in (self.given_name, self.family_name) if part
        )
        if kwargs.get("update_fields"):
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"display_name"}
        return super().save(*args, **kwargs)
