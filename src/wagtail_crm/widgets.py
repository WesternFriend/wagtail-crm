"""Accessible controls for supplied text or ordered, confirmed name parts."""

import json
from itertools import zip_longest

from django import forms


class ContactNameWidget(forms.Widget):
    template_name = "wagtail_crm/widgets/contact_name.html"

    class Media:
        css = {"all": ("wagtail_crm/contact_name.css",)}
        js = ("wagtail_crm/contact_name.js",)

    def value_from_datadict(self, data, files, name):
        if payload := data.get(f"{name}_payload"):
            try:
                parsed = json.loads(payload)
                if (
                    isinstance(parsed, dict)
                    and set(parsed) == {"mode", "full", "separator", "kinds", "values"}
                    and all(
                        isinstance(parsed[key], str)
                        for key in ("mode", "full", "separator")
                    )
                    and all(
                        isinstance(parsed[key], list)
                        and all(isinstance(item, str) for item in parsed[key])
                        for key in ("kinds", "values")
                    )
                ):
                    return parsed
            except (ValueError, TypeError):
                pass
            return {
                "mode": "invalid",
                "full": "",
                "separator": " ",
                "kinds": [],
                "values": [],
            }
        mode = data.get(f"{name}_mode")
        if mode is None:
            return data.get(name, "")

        def values(key):
            if hasattr(data, "getlist"):
                return data.getlist(key)
            value = data.get(key, [])
            return value if isinstance(value, list) else [value]

        return {
            "mode": mode,
            "full": data.get(name, ""),
            "separator": data.get(f"{name}_separator", " "),
            "kinds": values(f"{name}_kind"),
            "values": values(f"{name}_value"),
        }

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if isinstance(value, dict) and "mode" in value:
            editor = value
        elif isinstance(value, dict) and "components" in value:
            editor = {
                "mode": "structured",
                "full": "",
                "separator": value["defaultSeparator"],
                "kinds": [part["kind"] for part in value["components"]],
                "values": [part["value"] for part in value["components"]],
            }
        else:
            editor = {
                "mode": "supplied",
                "full": value.get("full", "")
                if isinstance(value, dict)
                else value or "",
                "separator": " ",
                "kinds": ["given"],
                "values": [""],
            }
        context["widget"]["editor"] = editor
        context["widget"]["initial_id"] = (
            f"{context['widget']['attrs'].get('id', name)}_initial"
        )
        context["widget"]["control_attrs"] = {
            key: value
            for key, value in context["widget"]["attrs"].items()
            if key not in {"id", "required"}
        }
        context["widget"]["parts"] = list(
            zip_longest(editor["kinds"], editor["values"], fillvalue="")
        )
        context["widget"]["kinds"] = (
            ("given", "Given name"),
            ("surname", "Surname"),
            ("surname2", "Second surname"),
            ("separator", "Separator"),
        )
        return context
