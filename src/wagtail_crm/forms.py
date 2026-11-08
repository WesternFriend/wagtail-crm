"""Ordinary staff fields with one canonical, internally structured name."""

from copy import deepcopy
from typing import override

from django import forms
from django.utils.html import format_html

from wagtail_crm.contact_profile import render_name
from wagtail_crm.models import Contact
from wagtail_crm.services import save_contact


def simple_parts(name):
    """Read recorded meanings only when both fields can represent them exactly."""
    parts = name.get("components", [])
    values = {}
    for part in parts:
        kind, value = part["kind"], part["value"]
        if kind == "separator":
            continue
        if (
            kind not in {"given", "surname"}
            or kind in values
            or "\n" in value
            or "\r" in value
        ):
            return None
        values[kind] = value
    return values or None


class ContactForm(forms.ModelForm):
    given_name = forms.CharField(
        label="Given name",
        required=False,
        strip=False,
        help_text="Enter a given name, surname, or both.",
    )
    surname = forms.CharField(label="Surname", required=False, strip=False)
    organization_name = forms.CharField(
        label="Organization name",
        required=False,
        strip=False,
        help_text="Enter the organization name.",
    )
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
        fields = (
            "kind",
            "given_name",
            "surname",
            "organization_name",
            "email",
            "postal_address",
            "expected_revision",
        )

    class Media:
        js = ("wagtail_crm/contact_form.js",)

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.original_name = deepcopy(self.instance.name)
        self.original_parts = simple_parts(self.original_name)
        original_full = render_name(self.original_name) if self.original_name else ""
        self.organization_recorded_context = (
            "\r" in original_full or "\n" in original_full
        )
        initial = kwargs.get("initial") or {}
        for field, kind in (("given_name", "given"), ("surname", "surname")):
            if field not in initial and self.original_parts:
                self.initial[field] = self.original_parts.get(kind, "")
        if self.original_name:
            if self.organization_recorded_context:
                self.fields["organization_name"].help_text = format_html(
                    "<strong>Current name: {}</strong> Leave the name field blank to keep it.",
                    original_full,
                )
            elif "organization_name" not in initial:
                self.initial["organization_name"] = original_full
            if not self.original_parts:
                self.fields["given_name"].help_text = format_html(
                    "<strong>Current name: {}</strong> Leave both name fields blank to keep it.",
                    original_full,
                )
        selected_kind = (
            self.data.get(self.add_prefix("kind"))
            if self.is_bound
            else self.initial.get("kind", self.instance.kind)
        )
        inactive = (
            ("given_name", "surname")
            if selected_kind == Contact.Kind.ORGANIZATION
            else ("organization_name",)
        )
        for field in inactive:
            self.fields[field].disabled = True
        self.initial["expected_revision"] = self.instance.revision

    def clean_expected_revision(self):
        value = self.cleaned_data["expected_revision"]
        if self.instance.pk and value is None:
            message = "Reload this contact before saving your changes."
            raise forms.ValidationError(message)
        return value

    def clean(self):
        cleaned = super().clean() or {}
        # Invalid name fields must never be turned into a replacement name.
        if any(
            field in self.errors
            for field in ("given_name", "surname", "organization_name")
        ):
            return cleaned
        if cleaned.get("kind") == Contact.Kind.ORGANIZATION:
            self._clean_organization_name(cleaned)
        else:
            self._clean_person_name(cleaned)
        return cleaned

    def _clean_organization_name(self, cleaned):
        text = cleaned.get("organization_name", "")
        if not text.strip():
            if not self.organization_recorded_context:
                self.add_error("organization_name", "Enter an organization name.")
        elif not self.original_name or text != render_name(self.original_name):
            self.instance.name = {"full": text}

    def _clean_person_name(self, cleaned):
        given, surname = cleaned.get("given_name", ""), cleaned.get("surname", "")
        if not given.strip() and not surname.strip():
            if not self.original_name or self.original_parts:
                self.add_error("given_name", "Enter a given name or surname.")
            return
        values = {
            kind: value
            for kind, value in (("given", given), ("surname", surname))
            if value.strip()
        }
        if self.original_parts == values:
            return
        name = self._updated_name(values)
        name["full"] = render_name(name)
        self.instance.name = name

    def _updated_name(self, values):
        if self.original_parts and set(values) == set(self.original_parts):
            name = deepcopy(self.original_name)
            name.pop("full", None)
            for part in name["components"]:
                if part["kind"] != "separator":
                    part["value"] = values[part["kind"]]
            return name
        return {
            "components": [
                {"kind": kind, "value": value} for kind, value in values.items()
            ],
            "isOrdered": True,
            "defaultSeparator": " ",
        }

    def _update_errors(self, errors):
        # The canonical name is internal; model errors belong to visible inputs.
        if hasattr(errors, "error_dict") and "name" in errors.error_dict:
            field = (
                "organization_name"
                if self.cleaned_data.get("kind") == Contact.Kind.ORGANIZATION
                else "given_name"
            )
            name_errors = errors.error_dict.pop("name")
            if field not in self.errors:
                errors.error_dict[field] = name_errors
        super()._update_errors(errors)  # type: ignore[misc]  # Missing from Django stubs.

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
