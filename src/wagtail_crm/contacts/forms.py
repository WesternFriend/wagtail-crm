"""Ordinary Wagtail contact fields, with no inferred name structure."""

from django import forms

from .models import Contact


class ContactForm(forms.ModelForm):
    name = forms.CharField(required=False, strip=False, max_length=255)

    class Meta:
        model = Contact
        fields = (
            "kind",
            "given_name",
            "family_name",
            "name",
            "email",
            "postal_address",
        )
        widgets = {"postal_address": forms.Textarea(attrs={"rows": 4})}

    class Media:
        js = ("wagtail_crm_contacts/contact_form.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unsplit_name = bool(
            self.instance.name
            and not (self.instance.given_name or self.instance.family_name)
        )
        if self.unsplit_name:
            del self.fields["given_name"]
            del self.fields["family_name"]
        kind = (
            self.data.get(self.add_prefix("kind"))
            if self.is_bound
            else self.initial.get("kind", self.instance.kind)
        )
        for field in ("given_name", "family_name"):
            if field in self.fields:
                self.fields[field].disabled = kind == Contact.Kind.ORGANIZATION
        self.fields["name"].disabled = (
            kind == Contact.Kind.PERSON and not self.unsplit_name
        )

    def clean(self):
        cleaned = super().clean() or {}
        if cleaned.get("kind") == Contact.Kind.ORGANIZATION or self.unsplit_name:
            cleaned["given_name"] = cleaned["family_name"] = ""
        else:
            cleaned["name"] = ""
        if cleaned.get("kind") == Contact.Kind.ORGANIZATION:
            if not cleaned.get("name", "").strip():
                self.add_error("name", "Enter an organization name.")
        elif self.unsplit_name:
            if not cleaned.get("name", "").strip():
                self.add_error("name", "Enter a name.")
        elif not (
            cleaned.get("given_name", "").strip()
            or cleaned.get("family_name", "").strip()
        ):
            self.add_error("given_name", "Enter a given name or family name.")
        return cleaned
