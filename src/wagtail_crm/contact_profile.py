"""The deliberately small RFC 9553 Card 1.0 interchange profile.

This is a validator for this application's supported subset, not for all JSContact.
Formatting uses confirmed component order and separators; it does not infer locale.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

UUID_VERSION = 4

if TYPE_CHECKING:
    from .models import Contact


def _error(message: str) -> None:
    raise ValidationError(message)


def _object(value: Any, allowed: set[str], required: set[str]) -> dict:
    if not isinstance(value, dict) or not required <= value.keys():
        _error("Missing or invalid contact properties.")
    if value.keys() - allowed:
        _error("Unsupported contact properties.")
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        _error("A nonempty text value is required.")
    return value


def render_name(name: dict) -> str:
    """Validate and render a full-only or explicitly ordered JSContact Name."""
    _object(name, {"full", "components", "isOrdered", "defaultSeparator"}, set())
    if "components" not in name:
        if set(name) != {"full"}:
            _error("An unstructured name requires only its full text.")
        return _text(name["full"])
    if name.get("isOrdered") is not True or not isinstance(
        name.get("defaultSeparator"), str
    ):
        _error("Structured names require confirmed order and a default separator.")
    full = _render_components(name["components"], name["defaultSeparator"])
    if "full" in name and name["full"] != full:
        _error("Full name conflicts with its components.")
    return full


def _render_components(components: Any, default_separator: str) -> str:
    if not isinstance(components, list) or not components:
        _error("Name components must be a nonempty list.")
    parts: list[str] = []
    previous_separator = True
    for component in components:
        _object(component, {"kind", "value"}, {"kind", "value"})
        kind = component["kind"]
        if not isinstance(kind, str) or kind not in {
            "given",
            "surname",
            "surname2",
            "separator",
        }:
            _error("Unsupported name component kind.")
        separator = kind == "separator"
        value = component["value"]
        if separator:
            if not isinstance(value, str):
                _error("A separator must be text.")
        else:
            value = _text(value)
        if separator and previous_separator:
            _error("Name separators must occur between name components.")
        if parts and not separator and not previous_separator:
            parts.append(default_separator)
        parts.append(value)
        previous_separator = separator
    if previous_separator:
        _error("A name cannot end with a separator.")
    return "".join(parts)


def _correspondence(card: dict, key: str, field: str) -> str:
    if key not in card:
        return ""
    mapping = _object(card[key], {"correspondence"}, {"correspondence"})
    entry = _object(mapping["correspondence"], {field}, {field})
    return _text(entry[field])


def decode_contact(card: dict) -> dict:
    """Validate our Card profile without creating or matching any contacts."""
    _object(
        card,
        {"@type", "version", "uid", "kind", "name", "emails", "addresses"},
        {"@type", "version", "uid", "kind", "name"},
    )
    if card["@type"] != "Card" or card["version"] != "1.0":
        _error("Only JSContact Card version 1.0 is supported.")
    uid = card["uid"]
    if not isinstance(uid, str) or not uid.startswith("urn:uuid:"):
        _error("Contact UID must be a UUID version 4 URN.")
    try:
        parsed_uid = UUID(uid.removeprefix("urn:uuid:"))
    except (ValueError, AttributeError) as exc:
        message = "Invalid contact UUID."
        raise ValidationError(message) from exc
    if parsed_uid.version != UUID_VERSION:
        _error("Contact UID must be a UUID version 4 URN.")
    kinds = {"individual": "person", "org": "organization"}
    if not isinstance(card["kind"], str) or card["kind"] not in kinds:
        _error("Unsupported contact kind.")
    display_name = render_name(card["name"])
    email = _correspondence(card, "emails", "address")
    if email:
        validate_email(email)
    return {
        "uid": parsed_uid,
        "name": deepcopy(card["name"]),
        "display_name": display_name,
        "kind": kinds[card["kind"]],
        "email": email,
        "postal_address": _correspondence(card, "addresses", "full"),
    }


def encode_contact(contact: Contact) -> dict:
    """Encode a supported contact; report invalid legacy data without changing it."""
    kinds = {"person": "individual", "organization": "org"}
    if contact.kind not in kinds:
        _error("Unsupported contact kind.")
    card = {
        "@type": "Card",
        "version": "1.0",
        "uid": f"urn:uuid:{contact.uid}",
        "kind": kinds[contact.kind],
        "name": deepcopy(contact.name),
    }
    if contact.email:
        card["emails"] = {"correspondence": {"address": contact.email}}
    if contact.postal_address:
        card["addresses"] = {"correspondence": {"full": contact.postal_address}}
    decode_contact(card)
    return card
