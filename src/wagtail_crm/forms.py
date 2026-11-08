"""Small staff form: names are entered once, and addresses remain multiline."""

from typing import override

from django import forms

from wagtail_crm.contact_profile import render_name
from wagtail_crm.models import Contact
from wagtail_crm.services import save_contact


class ContactForm(forms.ModelForm):
    name = forms.CharField(label="Name", strip=False)
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
            self.initial["name"] = (
                self.instance.display_name
                if self.instance.pk or not self.instance.name
                else render_name(self.instance.name)
            )
        self.initial["expected_revision"] = self.instance.revision

    def clean_expected_revision(self):
        value = self.cleaned_data["expected_revision"]
        if self.instance.pk and value is None:
            message = "Reload this contact before saving your changes."
            raise forms.ValidationError(message)
        return value

    def clean_name(self):
        value = self.cleaned_data["name"]
        if not value.strip():
            message = "Enter a name."
            raise forms.ValidationError(message)
        # An unchanged rendering must not erase known name components. A new
        # supplied name remains unstructured; prior structure stays in history.
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
