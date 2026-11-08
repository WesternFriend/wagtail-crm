"""Small staff form: names are entered once, and addresses remain multiline."""

from typing import override

from django import forms
from django.core.validators import ProhibitNullCharactersValidator

from wagtail_crm.contact_profile import render_name
from wagtail_crm.models import Contact
from wagtail_crm.services import save_contact
from wagtail_crm.widgets import ContactNameWidget


class ContactNameField(forms.Field):
    widget = ContactNameWidget

    def validate(self, value):
        super().validate(value)
        check = ProhibitNullCharactersValidator()
        if isinstance(value, dict):
            texts = [value.get("full", ""), value.get("defaultSeparator", "")]
            texts.extend(part["value"] for part in value.get("components", []))
            for text in texts:
                check(text)
        else:
            check(value)

    def to_python(self, value):
        if isinstance(value, dict) and "mode" in value:
            if value["mode"] == "supplied":
                return {"full": value["full"]}
            if value["mode"] != "structured" or len(value["kinds"]) != len(
                value["values"]
            ):
                message = "Invalid name parts."
                raise forms.ValidationError(message)
            return {
                "components": [
                    {"kind": kind, "value": text}
                    for kind, text in zip(value["kinds"], value["values"], strict=True)
                ],
                "isOrdered": True,
                "defaultSeparator": value["separator"],
            }
        return value


class ContactForm(forms.ModelForm):
    name = ContactNameField(label="Name")
    expected_revision = forms.IntegerField(
        required=False, min_value=0, widget=forms.HiddenInput
    )
    postal_address = forms.CharField(
        label="Postal address",
        required=False,
        strip=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    class Meta:
        model = Contact
        fields = ("name", "kind", "email", "postal_address", "expected_revision")

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        if "name" not in (kwargs.get("initial") or {}):
            self.initial["name"] = self.instance.name or ""
        self.initial["expected_revision"] = self.instance.revision

    def clean_expected_revision(self):
        value = self.cleaned_data["expected_revision"]
        if self.instance.pk and value is None:
            message = "Reload this contact before saving your changes."
            raise forms.ValidationError(message)
        return value

    def clean_name(self):
        value = self.cleaned_data["name"]
        if isinstance(value, dict):
            full = render_name(value)
            if "components" in value and "full" in self.instance.name:
                value["full"] = full
            return value
        if not isinstance(value, str) or not value.strip():
            message = "Enter a name."
            raise forms.ValidationError(message)
        # Compatibility for existing callers without the explicit format control.
        if self.instance.name and value == render_name(self.instance.name):
            return self.instance.name
        return {"full": value}

    @override
    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            save_contact(
                instance,
                actor=self.actor,
                expected_revision=self.cleaned_data["expected_revision"],
            )
            self.save_m2m()
        return instance
