from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from wagtail_crm.models import Contact, ContactHistory
from wagtail_crm.services import save_contact

pytestmark = pytest.mark.django_db


def test_anonymous_visitor_is_sent_to_login(client):
    response = client.get(reverse("wagtail_crm_contacts:index"))
    assert response.status_code == 302
    assert "/admin/login/" in response.url


@pytest.mark.parametrize(
    "action",
    ["index", "add", "edit", "delete", "inspect", "history", "history_results"],
)
def test_admin_access_alone_does_not_grant_contact_access(client, staff_user, action):
    contact = Contact.objects.create(display_name="Private Example")
    kwargs = (
        {"pk": contact.pk}
        if action in {"edit", "delete", "inspect", "history", "history_results"}
        else {}
    )
    client.force_login(staff_user)
    response = client.get(reverse(f"wagtail_crm_contacts:{action}", kwargs=kwargs))
    assert response.status_code == 302
    assert response.url == reverse("wagtailadmin_home")
    assert b"Private Example" not in response.content


def test_view_only_user_cannot_create_contact(client, staff_user):
    staff_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtail_crm", codename="view_contact"
        )
    )
    client.force_login(staff_user)
    assert client.get(reverse("wagtail_crm_contacts:index")).status_code == 200
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {"given_name": "Unauthorized Example", "kind": "person", "email": ""},
    )
    assert response.status_code == 302
    assert response.url == reverse("wagtailadmin_home")
    assert not Contact.objects.exists()


def test_editor_can_create_contact_without_a_website_account(client, contact_editor):
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {
            "organization_name": "Example Meeting",
            "kind": "organization",
            "email": "clerk@example.invalid",
        },
    )
    assert response.status_code == 302
    contact = Contact.objects.get(display_name="Example Meeting")
    assert contact.kind == Contact.Kind.ORGANIZATION
    assert contact.email == "clerk@example.invalid"


def test_editor_form_rejects_invalid_email(client, contact_editor):
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {"given_name": "Example", "kind": "person", "email": "not-an-email"},
    )
    assert response.status_code == 200
    assert response.context["form"].errors["email"]
    assert not Contact.objects.exists()


def test_mutation_requires_csrf_even_with_contact_permissions(contact_editor):
    client = Client(enforce_csrf_checks=True)
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {"given_name": "Example", "kind": "person", "email": ""},
    )
    assert response.status_code == 403
    assert not Contact.objects.exists()


def test_contacts_may_share_an_email_address():
    Contact.objects.create(display_name="Alex Example", email="shared@example.invalid")
    Contact.objects.create(
        display_name="Jordan Example", email="shared@example.invalid"
    )
    assert Contact.objects.count() == 2


def test_staff_form_has_ordinary_name_fields_and_multiline_address(
    client, contact_editor
):
    client.force_login(contact_editor)
    response = client.get(reverse("wagtail_crm_contacts:add"))
    form = response.context["form"]
    assert [field.name for field in form.visible_fields()] == [
        "kind",
        "given_name",
        "surname",
        "organization_name",
        "email",
        "postal_address",
    ]
    assert not form["given_name"].value()
    assert form.fields["given_name"].widget.__class__.__name__ == "TextInput"
    assert form.fields["postal_address"].widget.__class__.__name__ == "Textarea"
    assert "Enter name parts" not in response.content.decode()


def test_create_edit_inspect_and_delete_retain_private_history(client, contact_editor):
    client.force_login(contact_editor)
    address = "Example Meeting\n〒100-8994 東京都千代田区\nJapan"
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {
            "given_name": "王小明",
            "kind": "person",
            "email": "",
            "postal_address": address,
        },
    )
    assert response.status_code == 302
    contact = Contact.objects.get()
    uid = contact.uid
    assert contact.postal_address == address
    assert contact.history.get().actor == contact_editor
    assert contact.history.get().after["name"]["components"] == [
        {"kind": "given", "value": "王小明"}
    ]

    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        {
            "given_name": "王大明",
            "kind": "person",
            "email": "",
            "postal_address": address,
            "expected_revision": contact.revision,
        },
    )
    assert response.status_code == 302
    contact.refresh_from_db()
    assert contact.uid == uid
    assert contact.name["components"] == [{"kind": "given", "value": "王大明"}]
    assert contact.history.count() == 2
    change = contact.history.first()
    assert change.before["display_name"] == "王小明"
    assert change.after["display_name"] == "王大明"
    response = client.get(reverse("wagtail_crm_contacts:inspect", args=[contact.pk]))
    assert response.status_code == 200
    assert "History" in response.content.decode()
    assert "Full snapshots" not in response.content.decode()
    assert "contact_history" not in response.context
    response = client.get(reverse("wagtail_crm_contacts:history", args=[contact.pk]))
    assert "王小明" in response.content.decode()
    history = list(contact.history.all())

    response = client.post(
        reverse("wagtail_crm_contacts:delete", args=[contact.pk]),
        {"expected_revision": contact.revision},
    )
    assert response.status_code == 302
    assert not Contact.objects.exists()
    deleted = ContactHistory.objects.filter(contact_uid=uid, action="deleted").get()
    assert deleted.actor == contact_editor
    assert deleted.before["name"]["components"] == [
        {"kind": "given", "value": "王大明"}
    ]
    assert deleted.before["postal_address"] == address
    assert deleted.after is None
    for entry in history:
        entry.refresh_from_db()
        assert entry.contact_id is None
        assert entry.contact_uid == uid


def test_plain_name_editor_retains_unchanged_structure_then_preserves_previous_value(
    client, contact_editor
):
    structured = {
        "components": [
            {"kind": "surname", "value": "王"},
            {"kind": "given", "value": "小明"},
        ],
        "isOrdered": True,
        "defaultSeparator": "",
    }
    contact = save_contact(Contact(name=structured), actor=contact_editor)
    client.force_login(contact_editor)
    url = reverse("wagtail_crm_contacts:edit", args=[contact.pk])
    payload = {
        "given_name": "小明",
        "surname": "王",
        "kind": "person",
        "email": "new@example.test",
        "expected_revision": contact.revision,
    }
    assert client.post(url, payload).status_code == 302
    contact.refresh_from_db()
    assert contact.name["components"] == structured["components"]
    payload["given_name"] = "大明"
    payload["expected_revision"] = contact.revision
    assert client.post(url, payload).status_code == 302
    contact.refresh_from_db()
    assert contact.display_name == "王大明"
    assert (
        contact.history.first().before["name"]["components"] == structured["components"]
    )


def test_view_only_can_inspect_history_but_not_mutate(client, staff_user):
    staff_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtail_crm", codename="view_contact"
        )
    )
    contact = save_contact(Contact(name={"full": "Private Example"}))
    client.force_login(staff_user)
    response = client.get(reverse("wagtail_crm_contacts:inspect", args=[contact.pk]))
    assert response.status_code == 200
    assert "Private Example" in response.content.decode()
    assert "History" in response.content.decode()
    for action in ("edit", "delete"):
        response = client.post(
            reverse(f"wagtail_crm_contacts:{action}", args=[contact.pk])
        )
        assert response.status_code == 302
        assert response.url == reverse("wagtailadmin_home")
    assert contact.history.count() == 1
    assert Contact.objects.filter(pk=contact.pk).exists()


def test_inspect_escapes_contact_and_history_text(client, contact_editor):
    text = "Example <script>alert('synthetic')</script>"
    contact = save_contact(Contact(name={"full": text}, postal_address=text))
    client.force_login(contact_editor)
    response = client.get(reverse("wagtail_crm_contacts:inspect", args=[contact.pk]))
    html = response.content.decode()
    assert response.status_code == 200
    assert "&lt;script&gt;" in html
    assert "<script>alert('synthetic')</script>" not in html


def test_search_uses_updated_name_projection(client, contact_editor):
    contact = save_contact(Contact(name={"full": "Original Example"}))
    contact.name = {"full": "Changed Example"}
    save_contact(contact)
    client.force_login(contact_editor)
    response = client.get(reverse("wagtail_crm_contacts:index"), {"q": "Changed"})
    assert response.status_code == 200
    assert "Changed Example" in response.content.decode()


def test_blank_name_and_invalid_email_do_not_write_history(client, contact_editor):
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:add"),
        {"given_name": "   ", "kind": "person", "email": "bad"},
    )
    assert response.status_code == 200
    assert response.context["form"].errors["given_name"]
    assert not Contact.objects.exists()


def test_correspondence_only_edit_records_exact_previous_values(client, contact_editor):
    contact = save_contact(
        Contact(
            name={"full": "Example"},
            email="old@example.test",
            postal_address="Old\nAddress",
        )
    )
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        {
            "full_name": "Example",
            "kind": "person",
            "email": "new@example.test",
            "postal_address": "New\n住所",
            "expected_revision": contact.revision,
        },
    )
    assert response.status_code == 302
    change = contact.history.first()
    assert change.before["email"] == "old@example.test"
    assert change.after["email"] == "new@example.test"
    assert change.before["postal_address"] == "Old\nAddress"
    assert change.after["postal_address"] == "New\n住所"


def test_stale_form_preserves_newer_contact_and_shows_entered_work(
    client, contact_editor
):
    contact = save_contact(Contact(name={"full": "Example"}))
    original_revision = contact.revision
    contact.email = "newer@example.test"
    save_contact(contact)
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        {
            "full_name": "Attempted edit",
            "kind": "person",
            "email": "",
            "expected_revision": original_revision,
        },
    )
    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert response.context["form"]["full_name"].value() == "Attempted edit"
    contact.refresh_from_db()
    assert contact.display_name == "Example"
    assert contact.email == "newer@example.test"
    assert contact.history.count() == 2


def test_edit_requires_its_hidden_revision(client, contact_editor):
    contact = save_contact(Contact(name={"full": "Example"}))
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:edit", args=[contact.pk]),
        {"full_name": "Changed", "kind": "person", "email": ""},
    )
    assert response.status_code == 200
    assert response.context["form"].errors["expected_revision"]
    contact.refresh_from_db()
    assert contact.display_name == "Example"


def test_form_respects_explicit_initial_name_and_unsaved_structure():
    from wagtail_crm.forms import ContactForm

    contact = Contact(
        name={
            "components": [{"kind": "given", "value": "Alex"}],
            "isOrdered": True,
            "defaultSeparator": " ",
        }
    )
    assert ContactForm(instance=contact)["given_name"].value() == "Alex"
    assert (
        ContactForm(instance=contact, initial={"given_name": "Initial"})[
            "given_name"
        ].value()
        == "Initial"
    )


@pytest.mark.parametrize("route", ["history", "history_results"])
def test_history_shows_contact_type_changes_and_pages_history(
    client, contact_editor, route
):
    contact = save_contact(Contact(name={"full": "Example"}))
    contact.kind = Contact.Kind.ORGANIZATION
    save_contact(contact)
    client.force_login(contact_editor)
    url = reverse(f"wagtail_crm_contacts:{route}", args=[contact.pk])
    html = client.get(url).content.decode()
    assert "Contact type" in html
    assert "Person" in html
    assert "Organization" in html
    for number in range(20):
        contact.email = f"example{number}@example.test"
        save_contact(contact)
    response = client.get(url)
    assert len(response.context["page_obj"]) == 20
    assert response.context["page_obj"].has_next()
    response = client.get(url, {"p": 2})
    assert len(response.context["page_obj"]) == 2


def test_history_explains_structural_changes_with_same_rendering(
    client, contact_editor
):
    contact = save_contact(Contact(name={"full": "Alex Example"}))
    contact.name = {
        "components": [
            {"kind": "given", "value": "Alex"},
            {"kind": "surname", "value": "Example"},
        ],
        "isOrdered": True,
        "defaultSeparator": " ",
    }
    save_contact(contact)
    client.force_login(contact_editor)
    response = client.get(reverse("wagtail_crm_contacts:history", args=[contact.pk]))
    assert (
        "Name structure changed; the displayed name is unchanged."
        in response.content.decode()
    )


def test_changed_contact_during_delete_returns_a_message(client, contact_editor):
    contact = save_contact(Contact(name={"full": "Example"}))
    client.force_login(contact_editor)
    with patch(
        "wagtail_crm.views.delete_contact",
        side_effect=ValidationError("This contact changed. Reload it before deleting."),
    ):
        response = client.post(
            reverse("wagtail_crm_contacts:delete", args=[contact.pk]),
            {"expected_revision": contact.revision},
            follow=True,
        )
    assert response.status_code == 200
    assert "Reload it before deleting." in response.content.decode()
    assert Contact.objects.filter(pk=contact.pk).exists()


def test_create_service_validation_error_stays_on_form(client, contact_editor):
    client.force_login(contact_editor)
    with patch(
        "wagtail_crm.forms.save_contact",
        side_effect=ValidationError("The contact could not be saved. Review the name."),
    ):
        response = client.post(
            reverse("wagtail_crm_contacts:add"),
            {"given_name": "Example", "kind": "person", "email": ""},
        )
    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert response.context["form"]["given_name"].value() == "Example"
    assert not Contact.objects.exists()


@pytest.mark.parametrize("route", ["history", "history_results"])
def test_view_only_history_has_no_edit_actions(client, staff_user, route):
    staff_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtail_crm", codename="view_contact"
        )
    )
    contact = save_contact(Contact(name={"full": "Private Example"}))
    client.force_login(staff_user)
    response = client.get(reverse(f"wagtail_crm_contacts:{route}", args=[contact.pk]))
    assert response.status_code == 200
    html = response.content.decode()
    assert "Private Example" in html
    assert reverse("wagtail_crm_contacts:edit", args=[contact.pk]) not in html
    assert "Full snapshots" in html
    if route == "history":
        assert {
            "url": reverse("wagtail_crm_contacts:inspect", args=[contact.pk]),
            "label": contact.display_name,
        } in response.context["breadcrumbs_items"]


def test_history_summarizes_changes_and_collapses_complete_escaped_snapshots(
    client, contact_editor
):
    import json
    import re
    from html import unescape

    from wagtail.log_actions import log
    from wagtail.models import ModelLogEntry

    text = "Pat <script>alert('synthetic')</script> Morgan"
    contact = Contact.objects.create(
        name={"full": text}, postal_address="Unchanged private address"
    )
    contact.email = "new@example.test"
    save_contact(contact, actor=contact_editor, origin=ContactHistory.Origin.DEMO)
    log(instance=contact, action="wagtail.create", user=contact_editor)
    log(instance=contact, action="wagtail.edit", user=contact_editor)
    client.force_login(contact_editor)
    for route in ("history", "history_results"):
        response = client.get(
            reverse(f"wagtail_crm_contacts:{route}", args=[contact.pk])
        )
        assert response.status_code == 200
        html = response.content.decode()
        summary = re.sub(r"<details>.*?</details>", "", html, flags=re.DOTALL)
        # The page header may name the contact; the history table must not repeat it.
        table = summary.split("<tbody>")[1].split("</tbody>")[0]
        assert "Email" in table
        assert "Before: —" in table
        assert "After: new@example.test" in table
        assert "Pat" not in table
        assert "Unchanged private address" not in table
        assert "Synthetic data" in table
        assert "reviewer" in table
        assert "<details>" in html
        assert "<details open" not in html
        assert "&lt;script&gt;" in html
        assert "<script>alert('synthetic')</script>" not in html
        snapshots = re.findall(r"<pre>(.*?)</pre>", html, flags=re.DOTALL)
        before, after = [json.loads(unescape(value)) for value in snapshots]
        assert before == contact.history.get().before
        assert after == contact.history.get().after
        assert before["uid"] == str(contact.uid)
        assert before["name"] == {"full": text}
        assert before["postal_address"] == "Unchanged private address"
    # Rendering the canonical UI does not create additional audit records.
    assert ModelLogEntry.objects.count() == 2


def test_contact_type_labels_and_inspect_history_navigation(client, contact_editor):
    contact = save_contact(Contact(name={"full": "Pat Morgan"}))
    client.force_login(contact_editor)
    history_url = reverse("wagtail_crm_contacts:history", args=[contact.pk])
    for route in ("add", "index", "inspect", "edit"):
        args = [contact.pk] if route in {"inspect", "edit"} else []
        response = client.get(reverse(f"wagtail_crm_contacts:{route}", args=args))
        html = response.content.decode()
        assert "Contact type" in html
        assert ">Kind<" not in html
        if route in {"inspect", "edit"}:
            assert history_url in html
        if route == "inspect":
            assert str(contact.uid) not in html
            assert "Full snapshots" not in html
            assert "contact_history" not in response.context
    assert response.context["form"].fields["kind"].label == "Contact type"


@pytest.mark.parametrize(
    "permission", ["add_contact", "change_contact", "delete_contact"]
)
@pytest.mark.parametrize("route", ["history", "history_results"])
def test_history_requires_view_permission_even_with_other_contact_permissions(
    client, staff_user, permission, route
):
    staff_user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="wagtail_crm", codename=permission
        )
    )
    contact = save_contact(Contact(name={"full": "Private Example"}))
    client.force_login(staff_user)
    response = client.get(reverse(f"wagtail_crm_contacts:{route}", args=[contact.pk]))
    assert response.status_code == 302
    assert response.url == reverse("wagtailadmin_home")
    assert "Private Example" not in response.content.decode()


@pytest.mark.parametrize("field", ["display_name", "postal_address"])
def test_history_explains_whitespace_only_changes(client, contact_editor, field):
    import re

    contact = Contact.objects.create(name={"full": "Pat Morgan"}, postal_address="A B")
    if field == "display_name":
        contact.name = {"full": "Pat  Morgan "}
    else:
        contact.postal_address = "A  B "
    save_contact(contact)
    entry = contact.history.get()
    client.force_login(contact_editor)
    response = client.get(reverse("wagtail_crm_contacts:history", args=[contact.pk]))
    summary = re.sub(
        r"<details>.*?</details>", "", response.content.decode(), flags=re.DOTALL
    )
    assert "Whitespace changed; full snapshots retain the exact values." in summary
    contact.refresh_from_db()
    assert getattr(contact, field) == entry.after[field]
    assert entry.before[field] != entry.after[field]


@pytest.mark.parametrize("action", ["created", "baseline"])
@pytest.mark.parametrize("route", ["history", "history_results"])
def test_initial_history_has_meaningful_summary_and_complete_closed_snapshots(
    client, contact_editor, action, route
):
    import json
    import re
    from html import unescape

    contact = save_contact(
        Contact(name={"full": "Pat <Morgan>"}, postal_address="First line\nSecond line")
    )
    entry = contact.history.get()
    if action == "baseline":
        entry.action = action
        entry.origin = "migration"
        entry.save(update_fields=["action", "origin"])
    client.force_login(contact_editor)
    response = client.get(reverse(f"wagtail_crm_contacts:{route}", args=[contact.pk]))
    html = response.content.decode()
    summary = re.sub(r"<details>.*?</details>", "", html, flags=re.DOTALL)
    label = "Initial record" if action == "baseline" else "Created"
    assert label in summary
    assert "Before: —" in summary
    assert "After: Pat &lt;Morgan&gt;" in summary
    assert "After: Person" in summary
    assert "After: First line<br>Second line" in summary
    assert "<details>" in html
    assert "<details open" not in html
    assert f"(change {entry.pk})" in html
    assert f'aria-label="Full snapshots: {label}, ' in html
    assert ">Full snapshots</summary>" in html
    snapshots = re.findall(r"<pre>(.*?)</pre>", html, flags=re.DOTALL)
    assert [json.loads(unescape(value)) for value in snapshots] == [None, entry.after]


@pytest.mark.parametrize("route", ["history", "history_results"])
def test_postal_address_only_history_summary_escapes_multiline_changes(
    client, contact_editor, route
):
    import re

    contact = Contact.objects.create(
        name={"full": "Unchanged name"},
        email="unchanged@example.test",
        postal_address="Old <street>\nOld city",
    )
    contact.postal_address = "New <street>\nNew city"
    save_contact(contact)
    client.force_login(contact_editor)
    response = client.get(reverse(f"wagtail_crm_contacts:{route}", args=[contact.pk]))
    summary = re.sub(
        r"<details>.*?</details>", "", response.content.decode(), flags=re.DOTALL
    )
    table = summary.split("<tbody>")[1].split("</tbody>")[0]
    assert "Postal address" in table
    assert "Before: Old &lt;street&gt;<br>Old city" in table
    assert "After: New &lt;street&gt;<br>New city" in table
    assert "<street>" not in table
    assert "Unchanged name" not in table
    assert "unchanged@example.test" not in table
    assert "Contact type" not in table


def test_history_actor_profile_queries_remain_bounded(
    client, contact_editor, django_user_model
):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    from wagtail.users.models import UserProfile

    contact = Contact.objects.create(name={"full": "Pat Morgan"})
    for number in range(8):
        actor = django_user_model.objects.create_user(username=f"actor-{number}")
        UserProfile.objects.get_or_create(user=actor)
        contact.email = f"pat{number}@example.test"
        save_contact(contact, actor=actor)
    client.force_login(contact_editor)
    # Warm request-level Wagtail caches before measuring profile lookups.
    url = reverse("wagtail_crm_contacts:history_results", args=[contact.pk])
    client.get(url)
    with CaptureQueriesContext(connection) as queries:
        response = client.get(url)
    assert response.status_code == 200
    profile_queries = [
        query
        for query in queries.captured_queries
        if "wagtailusers_userprofile" in query["sql"]
    ]
    # One joined history query, plus at most one lookup for the current staff user.
    assert len(profile_queries) <= 2
    assert response.content.decode().count("actor-") == 8


def test_inspect_uses_one_native_history_link(client, contact_editor):
    contact = save_contact(Contact(name={"full": "Jordan Sample"}))
    client.force_login(contact_editor)
    response = client.get(reverse("wagtail_crm_contacts:inspect", args=[contact.pk]))
    url = reverse("wagtail_crm_contacts:history", args=[contact.pk])
    assert response.content.decode().count(f'href="{url}"') == 1


@pytest.mark.parametrize("endpoint", ["history", "history_results"])
def test_creation_history_omits_empty_optional_changes(
    client, contact_editor, endpoint
):
    import re

    contact = save_contact(Contact(name={"full": "Jordan Sample"}))
    client.force_login(contact_editor)
    response = client.get(
        reverse(f"wagtail_crm_contacts:{endpoint}", args=[contact.pk])
    )
    html = response.content.decode()
    summary = re.sub(r"<details>.*?</details>", "", html, flags=re.DOTALL)
    assert "After: Jordan Sample" in summary
    assert "<dt>Email</dt>" not in summary
    assert "<dt>Postal address</dt>" not in summary
    assert "&quot;email&quot;: &quot;&quot;" in html
    assert "&quot;postal_address&quot;: &quot;&quot;" in html


def test_delete_requires_fresh_confirmation(client, contact_editor):
    from wagtail.models import ModelLogEntry

    contact = save_contact(Contact(name={"full": "Before"}))
    client.force_login(contact_editor)
    url = reverse("wagtail_crm_contacts:delete", args=[contact.pk])
    response = client.get(url)
    revision = response.context["form"]["expected_revision"].value()
    contact.name = {"full": "After"}
    save_contact(contact)
    response = client.post(url, {"expected_revision": revision}, follow=True)
    assert response.status_code == 200
    assert "review the latest details before continuing" in response.content.decode()
    assert Contact.objects.filter(pk=contact.pk).exists()
    assert contact.history.count() == 2
    assert not ModelLogEntry.objects.filter(action="wagtail.delete").exists()
    assert response.context["form"]["expected_revision"].value() == contact.revision
    client.post(url, {"expected_revision": contact.revision})
    assert not Contact.objects.filter(pk=contact.pk).exists()
    assert ModelLogEntry.objects.filter(action="wagtail.delete").count() == 1


@pytest.mark.parametrize("revision", [None, "invalid", -1])
def test_delete_without_valid_revision_cannot_delete(client, contact_editor, revision):
    contact = save_contact(Contact(name={"full": "Protected"}))
    client.force_login(contact_editor)
    response = client.post(
        reverse("wagtail_crm_contacts:delete", args=[contact.pk]),
        {"expected_revision": revision} if revision is not None else {},
    )
    assert response.status_code == 200
    assert response.context["form"].errors
    assert Contact.objects.filter(pk=contact.pk).exists()
    assert contact.history.count() == 1


def test_inspect_postal_address_uses_standard_field_and_escapes_markup(
    client, contact_editor
):
    contact = save_contact(
        Contact(
            name={"full": "Postal Example"},
            postal_address="<script>private</script>\nFinland",
        )
    )
    client.force_login(contact_editor)
    response = client.get(reverse("wagtail_crm_contacts:inspect", args=[contact.pk]))
    assert response.status_code == 200
    fields = {field["label"]: field["value"] for field in response.context["fields"]}
    assert fields["Postal address"] == "&lt;script&gt;private&lt;/script&gt;<br>Finland"
    assert "<script>private</script>" not in response.content.decode()


def test_delete_history_failure_rolls_back_contact_and_both_audit_logs(
    client, contact_editor
):
    from wagtail.models import ModelLogEntry

    contact = save_contact(Contact(name={"full": "Retained"}))
    original_history = list(contact.history.values())
    client.force_login(contact_editor)
    with (
        patch(
            "wagtail_crm.services.ContactHistory.objects.using",
            side_effect=RuntimeError("History unavailable"),
        ),
        pytest.raises(RuntimeError, match="History unavailable"),
    ):
        client.post(
            reverse("wagtail_crm_contacts:delete", args=[contact.pk]),
            {"expected_revision": contact.revision},
        )
    contact.refresh_from_db()
    assert contact.display_name == "Retained"
    assert list(contact.history.values()) == original_history
    assert not ModelLogEntry.objects.filter(action="wagtail.delete").exists()
