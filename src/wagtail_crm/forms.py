"""Ordinary staff fields with one canonical, internally structured name."""

from copy import deepcopy
from itertools import pairwise
from typing import override

from django import forms

from wagtail_crm.contact_profile import render_name
from wagtail_crm.models import Contact
from wagtail_crm.services import save_contact


def normalized(value):
    """Compare ordinary textarea submissions without changing stored line endings."""
    return value.replace("\r\n", "\n").replace("\r", "\n")


def component_group(kind):
    return "surname" if kind == "surname2" else kind


def simple_parts(name):
    """Group only explicitly recorded meanings, never words from full text."""
    parts = name.get("components", [])
    values = {}
    for group in ("given", "surname"):
        selected = [
            index
            for index, part in enumerate(parts)
            if component_group(part["kind"]) == group
        ]
        if not selected:
            continue
        text = parts[selected[0]]["value"]
        for previous, current in pairwise(selected):
            separator = name["defaultSeparator"]
            if current == previous + 2 and parts[previous + 1]["kind"] == "separator":
                separator = parts[previous + 1]["value"]
            text += separator + parts[current]["value"]
        values[group] = text
    return values or None


class ContactForm(forms.ModelForm):
    given_name = forms.CharField(
        label="Given name",
        required=False,
        strip=False,
        help_text="Enter a given name, surname, or both.",
    )
    surname = forms.CharField(label="Surname", required=False, strip=False)
    full_name = forms.CharField(label="Name", required=False, strip=False)
    organization_name = forms.CharField(
        label="Organization name",
        required=False,
        strip=False,
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
            "full_name",
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
        self.person_name_fields = (
            ("given_name", "surname")
            if not self.original_name or self.original_parts
            else ("full_name",)
        )
        self._preserve_stale_field_shape()
        for field in {"given_name", "surname", "full_name"} - set(
            self.person_name_fields
        ):
            del self.fields[field]
        initial = kwargs.get("initial") or {}
        for field, kind in (("given_name", "given"), ("surname", "surname")):
            if field in self.fields and field not in initial and self.original_parts:
                self.initial[field] = self.original_parts.get(kind, "")
            if (
                field in self.fields
                and self.original_parts
                and any(
                    character in self.original_parts.get(kind, "")
                    for character in "\r\n"
                )
            ):
                self.fields[field].widget = forms.Textarea(attrs={"rows": 3})
        for field in ("full_name", "organization_name"):
            if field not in self.fields:
                continue
            if field not in initial:
                self.initial[field] = original_full
            if "\r" in original_full or "\n" in original_full:
                self.fields[field].widget = forms.Textarea(attrs={"rows": 3})
        selected_kind = (
            self.data.get(self.add_prefix("kind"))
            if self.is_bound
            else self.initial.get("kind", self.instance.kind)
        )
        inactive = (
            self.person_name_fields
            if selected_kind == Contact.Kind.ORGANIZATION
            else ("organization_name",)
        )
        for field in inactive:
            self.fields[field].disabled = True
        self.initial["expected_revision"] = self.instance.revision

    def _preserve_stale_field_shape(self):
        self.stale_revision = False
        if self.is_bound and self.instance.pk:
            try:
                submitted_revision = self.fields["expected_revision"].clean(
                    self.data.get(self.add_prefix("expected_revision"))
                )
            except forms.ValidationError:
                submitted_revision = None
            self.stale_revision = (
                submitted_revision is not None
                and submitted_revision != self.instance.revision
            )
            if self.stale_revision:
                if self.add_prefix("full_name") in self.data:
                    self.person_name_fields = ("full_name",)
                elif any(
                    self.add_prefix(field) in self.data
                    for field in ("given_name", "surname")
                ):
                    self.person_name_fields = ("given_name", "surname")
                for field in self.person_name_fields:
                    if any(
                        character in self.data.get(self.add_prefix(field), "")
                        for character in "\r\n"
                    ):
                        self.fields[field].widget = forms.Textarea(attrs={"rows": 3})

    def clean_expected_revision(self):
        value = self.cleaned_data["expected_revision"]
        if self.instance.pk and value is None:
            message = "Reload this contact before saving your changes."
            raise forms.ValidationError(message)
        return value

    def clean(self):
        cleaned = super().clean() or {}
        if self.stale_revision:
            self.add_error(
                None,
                "This contact changed while you were editing. Reload it and review the latest details before saving.",
            )
            return cleaned
        # Invalid name fields must never be turned into a replacement name.
        if any(
            field in self.errors
            for field in (*self.person_name_fields, "organization_name")
        ):
            return cleaned
        if cleaned.get("kind") == Contact.Kind.ORGANIZATION:
            self._clean_organization_name(cleaned)
        else:
            self._clean_person_name(cleaned)
        return cleaned

    def _clean_full_name(self, cleaned, field, message):
        text = cleaned.get(field, "")
        if not text.strip():
            self.add_error(field, message)
            return

        if not self.original_name or normalized(text) != normalized(
            render_name(self.original_name)
        ):
            self.instance.name = {"full": text}

    def _clean_organization_name(self, cleaned):
        self._clean_full_name(
            cleaned, "organization_name", "Enter an organization name."
        )

    def _clean_person_name(self, cleaned):
        if self.person_name_fields == ("full_name",):
            self._clean_full_name(cleaned, "full_name", "Enter a name.")
            return
        given, surname = cleaned.get("given_name", ""), cleaned.get("surname", "")
        if not given.strip() and not surname.strip():
            self.add_error("given_name", "Enter a given name or surname.")
            return
        values = {
            kind: value
            for kind, value in (("given", given), ("surname", surname))
            if value.strip()
        }
        if self.original_parts and {
            key: normalized(value) for key, value in self.original_parts.items()
        } == {key: normalized(value) for key, value in values.items()}:
            return
        name = self._updated_name(values)
        name["full"] = render_name(name)
        self.instance.name = name

    def _updated_name(self, values):
        if self.original_parts:
            name = deepcopy(self.original_name)
            name.pop("full", None)
            kept = {}
            replaced = set()
            for index, part in enumerate(name["components"]):
                group = component_group(part["kind"])
                if group == "separator" or group not in values:
                    continue
                if normalized(values[group]) == normalized(self.original_parts[group]):
                    kept[index] = part
                elif group not in replaced:
                    kept[index] = {"kind": part["kind"], "value": values[group]}
                    replaced.add(group)
            components = []
            previous = None
            for index, part in kept.items():
                if previous is not None:
                    separator = self._retained_separator(name, kept, previous, index)
                    if separator:
                        components.append(separator)
                components.append(part)
                previous = index
            self._add_missing_groups(components, values)
            name["components"] = components
            return name
        return {
            "components": [
                {"kind": kind, "value": value} for kind, value in values.items()
            ],
            "isOrdered": True,
            "defaultSeparator": " ",
        }

    def _add_missing_groups(self, components, values):
        for group in values.keys() - self.original_parts.keys():
            component = {"kind": group, "value": values[group]}
            boundary = {"kind": "separator", "value": " "}
            if not components:
                components.append(component)
            elif group == "given":
                components[0:0] = [component, boundary]
            else:
                components.extend([boundary, component])

    @staticmethod
    def _retained_separator(name, kept, previous, index):
        for position in range(previous + 1, index):
            separator = name["components"][position]
            if separator["kind"] != "separator":
                continue
            left = component_group(name["components"][position - 1]["kind"])
            right = component_group(name["components"][position + 1]["kind"])
            if (position == previous + 1 and index == previous + 2) or (
                left != right
                and left == component_group(kept[previous]["kind"])
                and right == component_group(kept[index]["kind"])
            ):
                return separator
        return None

    def _update_errors(self, errors):
        # The canonical name is internal; model errors belong to visible inputs.
        if hasattr(errors, "error_dict") and "name" in errors.error_dict:
            field = (
                "organization_name"
                if self.cleaned_data.get("kind") == Contact.Kind.ORGANIZATION
                else self.person_name_fields[0]
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
