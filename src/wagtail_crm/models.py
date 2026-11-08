from django.db import models


class Contact(models.Model):
    """A person or organization, independent of a website login account."""

    class Kind(models.TextChoices):
        PERSON = "person", "Person"
        ORGANIZATION = "organization", "Organization"

    display_name = models.CharField(max_length=255)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.PERSON)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["display_name", "pk"]

    def __str__(self):
        return self.display_name
