import json
import os
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import resolve, reverse
from playwright.sync_api import expect, sync_playwright

from wagtail_crm.models import Contact
from wagtail_crm.services import save_contact


@pytest.mark.browser
class TestContactBrowser(StaticLiveServerTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ui-reviewer", password="synthetic-browser-password", is_staff=True
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="wagtailadmin", codename="access_admin"
            )
        )

    @contextmanager
    def browser_page(self):
        # Stop Playwright's event loop before any synchronous ORM work resumes.
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"),
            )
            try:
                with browser.new_context(
                    viewport={"width": 1440, "height": 1000}
                ) as context:
                    self.page = context.new_page()
                    yield
            finally:
                browser.close()

    def login(self):
        self.page.goto(f"{self.live_server_url}/")
        # Wagtail includes its required-field marker in accessible labels.
        self.page.get_by_label("Username").fill("ui-reviewer")
        self.page.get_by_label("Password").fill("synthetic-browser-password")
        self.page.get_by_role("button", name="Sign in", exact=True).click()
        expect(self.page).to_have_url(f"{self.live_server_url}/admin/")

    def test_editor_can_log_in_and_create_contact(self):
        self.user.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="wagtail_crm")
        )
        with self.browser_page():
            self.login()
            self.page.get_by_role("link", name="Contacts", exact=True).click()
            self.page.get_by_role("link", name="Add contact", exact=True).click()
            self.page.locator("#id_name").fill("UI Example Meeting")
            self.page.get_by_label("Kind").select_option("organization")
            self.page.get_by_label("Postal address").fill(
                "Example Friends Meeting\n〒100-8994 東京都千代田区\nJapan"
            )
            self.page.get_by_label("Email").fill("invalid@local")
            self.page.get_by_role("button", name="Create", exact=True).click()
            expect(
                self.page.get_by_text("Enter a valid email address.")
            ).to_be_visible()
            expect(self.page.locator("#id_name")).to_have_value("UI Example Meeting")
            self.page.get_by_label("Email").fill("ui@example.invalid")
            self.page.get_by_role("button", name="Create", exact=True).click()
            expect(
                self.page.get_by_role("link", name="UI Example Meeting", exact=True)
            ).to_be_visible()

            self.page.get_by_role("link", name="UI Example Meeting", exact=True).click()
            expect(self.page.get_by_label("Postal address")).to_have_value(
                "Example Friends Meeting\n〒100-8994 東京都千代田区\nJapan"
            )
            self.page.locator("#id_name").fill("Updated Example Meeting")
            self.page.get_by_role("button", name="Save", exact=True).click()
            expect(
                self.page.get_by_role(
                    "link", name="Updated Example Meeting", exact=True
                )
            ).to_be_visible()

            edit_link = self.page.get_by_role(
                "link", name="Updated Example Meeting", exact=True
            )
            pk = resolve(urlsplit(edit_link.get_attribute("href")).path).kwargs["pk"]
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:inspect', args=[pk])}"
            )
            expect(
                self.page.get_by_role("heading", name="Change history", exact=True)
            ).to_be_visible()
            expect(self.page.locator("#contact-postal-address")).to_contain_text(
                "Japan"
            )

            if directory := os.environ.get("CRM_SCREENSHOTS_DIR"):
                path = Path(directory)
                path.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(path=str(path / "contacts.png"), full_page=True)
        contact = Contact.objects.get(display_name="Updated Example Meeting")
        assert contact.name == {"full": "Updated Example Meeting"}
        assert contact.history.count() == 2

    def test_structured_editor_creates_edits_and_returns_to_full_name(self):
        self.user.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="wagtail_crm")
        )
        with self.browser_page():
            self.login()
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:add')}"
            )
            self.page.locator("#id_name").fill("Supplied name stays intact")
            self.page.get_by_role("button", name="Enter name parts", exact=True).click()
            self.page.get_by_role("button", name="Use a full name", exact=True).click()
            expect(self.page.locator("#id_name")).to_have_value(
                "Supplied name stays intact"
            )
            self.page.get_by_role("button", name="Enter name parts", exact=True).click()
            rows = self.page.locator("[data-name-parts] [data-name-part]")
            rows.nth(0).get_by_label("Part value", exact=True).fill("Diego Luis")
            for value in ["Rivera", "Barrientos"]:
                self.page.get_by_role(
                    "button", name="Add name part", exact=True
                ).click()
                rows.last.get_by_label("Part type", exact=True).select_option("surname")
                rows.last.get_by_label("Part value", exact=True).fill(value)
            expect(self.page.get_by_label("Generated full name")).to_have_value(
                "Diego Luis Rivera Barrientos"
            )
            self.page.get_by_role("button", name="Create", exact=True).click()
            self.page.get_by_role(
                "link", name="Diego Luis Rivera Barrientos", exact=True
            ).click()
            expect(rows).to_have_count(3)
            rows.nth(0).get_by_label("Part value", exact=True).fill("王")
            rows.nth(0).get_by_label("Part type", exact=True).select_option("surname")
            rows.nth(1).get_by_label("Part value", exact=True).fill("小明")
            rows.nth(1).get_by_label("Part type", exact=True).select_option("given")
            rows.nth(2).get_by_role("button", name="Remove part", exact=True).click()
            self.page.get_by_label("Join parts with").fill("")
            expect(self.page.get_by_label("Generated full name")).to_have_value(
                "王小明"
            )
            rows.nth(1).get_by_label("Part value", exact=True).fill("大明")
            expect(self.page.get_by_label("Generated full name")).to_have_value(
                "王大明"
            )
            self.page.get_by_label("Email").fill("invalid@local")
            self.page.get_by_role("button", name="Save", exact=True).click()
            expect(
                self.page.get_by_text("Enter a valid email address.")
            ).to_be_visible()
            expect(rows.nth(1).get_by_label("Part value", exact=True)).to_have_value(
                "大明"
            )
            self.page.get_by_label("Email").fill("")
            if directory := os.environ.get("CRM_SCREENSHOTS_DIR"):
                path = Path(directory)
                path.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(
                    path=str(path / "structured-name.png"), full_page=True
                )
            self.page.get_by_role("button", name="Save", exact=True).click()
            self.page.get_by_role("link", name="王大明", exact=True).click()
            expect(self.page.get_by_label("Join parts with")).to_have_value("")
            self.page.get_by_role("button", name="Use a full name", exact=True).click()
            expect(self.page.locator("#id_name")).to_have_value("王大明")
            self.page.locator("#id_name").fill("Mary Beth van Berg")
            self.page.get_by_role("button", name="Save", exact=True).click()
            self.page.get_by_role("link", name="Mary Beth van Berg", exact=True).click()
            expect(self.page.locator("#id_name")).to_have_value("Mary Beth van Berg")
            self.page.get_by_label("Email").fill("example@example.test")
            self.page.get_by_role("button", name="Save", exact=True).click()
        contact = Contact.objects.get()
        assert contact.name == {"full": "Mary Beth van Berg"}
        assert contact.history.count() == 4
        assert contact.history.order_by("id")[1].after["display_name"] == "王大明"

    def test_movement_separators_drafts_errors_and_whitespace(self):
        self.user.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="wagtail_crm")
        )
        contact = save_contact(
            Contact(
                name={
                    "components": [
                        {"kind": "given", "value": "Alex"},
                        {"kind": "surname", "value": "Rivera"},
                    ],
                    "isOrdered": True,
                    "defaultSeparator": " ",
                }
            )
        )
        with self.browser_page():
            self.login()
            url = f"{self.live_server_url}{reverse('wagtail_crm_contacts:edit', args=[contact.pk])}"
            self.page.goto(url)
            rows = self.page.locator("[data-name-parts] [data-name-part]")
            rows.first.get_by_role("button", name="Move down", exact=True).click()
            expect(rows.last.get_by_label("Part value", exact=True)).to_be_focused()
            expect(rows.last).to_have_accessible_name("Name part 2")
            self.page.keyboard.press("Tab")
            expect(
                rows.last.get_by_role("button", name="Move up", exact=True)
            ).to_be_focused()
            self.page.keyboard.press("Enter")
            expect(rows.first.get_by_label("Part value", exact=True)).to_be_focused()
            expect(self.page.get_by_label("Generated full name")).to_have_value(
                "Alex Rivera"
            )
            self.page.get_by_role("button", name="Add name part", exact=True).click()
            rows.last.get_by_label("Part type", exact=True).select_option("separator")
            rows.last.get_by_label("Part value", exact=True).fill(" · ")
            rows.last.get_by_role("button", name="Move up", exact=True).click()
            expect(self.page.get_by_label("Generated full name")).to_have_value(
                "Alex · Rivera"
            )
            self.page.get_by_role("button", name="Save", exact=True).click()
            self.page.goto(url)
            expect(rows.nth(1).get_by_label("Part type", exact=True)).to_have_value(
                "separator"
            )
            self.page.get_by_label("Email").fill("correspondence@example.test")
            self.page.get_by_role("button", name="Save", exact=True).click()
            self.page.goto(url)
            expect(self.page.get_by_label("Generated full name")).to_have_value(
                "Alex · Rivera"
            )
            self.page.get_by_role("button", name="Use a full name", exact=True).click()
            expect(self.page.locator("#id_name")).to_have_value("Alex · Rivera")
            self.page.locator("#id_name").fill("Corrected supplied draft")
            self.page.get_by_role("button", name="Enter name parts", exact=True).click()
            self.page.get_by_role("button", name="Use a full name", exact=True).click()
            expect(self.page.locator("#id_name")).to_have_value(
                "Corrected supplied draft"
            )
            self.page.get_by_role("button", name="Enter name parts", exact=True).click()
            rows.first.get_by_label("Part value", exact=True).fill("\u0085")
            expect(self.page.locator("[data-name-preview-error]")).not_to_have_text("")
            rows.first.get_by_label("Part value", exact=True).fill("\ufeff")
            expect(self.page.locator("[data-name-preview-error]")).to_have_text("")
            rows.first.get_by_label("Part value", exact=True).fill("")
            self.page.get_by_role("button", name="Save", exact=True).click()
            expect(
                self.page.locator("[data-name-part] [data-part-value]").first
            ).to_have_attribute("aria-invalid", "true")
            self.page.get_by_role(
                "button", name="Go to the first error", exact=True
            ).click()
            expect(self.page.locator(".error-message").first).to_be_focused()
            description = rows.first.get_by_label(
                "Part value", exact=True
            ).get_attribute("aria-describedby")
            assert "id_name_error" in description.split()
            expect(self.page.locator("#id_name_error")).to_contain_text("nonempty")
            self.page.locator('label[for="id_name"]').click()
            expect(self.page.locator("[data-contact-name]")).to_be_focused()
            rows.first.get_by_label("Part value", exact=True).fill("Alex")
            self.page.get_by_role("button", name="Use a full name", exact=True).click()
            expect(self.page.locator("#id_name")).to_have_value("Alex · Rivera")
            self.page.get_by_role("button", name="Save", exact=True).click()
            self.page.goto(url)
            expect(self.page.locator("#id_name")).to_have_value("Alex · Rivera")
        contact.refresh_from_db()
        assert contact.display_name == "Alex · Rivera"
        assert contact.name == {"full": "Alex · Rivera"}
        assert contact.history.first().before["name"]["components"][1] == {
            "kind": "separator",
            "value": " · ",
        }

    def test_exact_line_breaks_round_trip_in_every_name_control(self):
        self.user.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="wagtail_crm")
        )
        examples = []
        for newline in ["\r", "\n", "\r\n"]:
            full = {"full": f"Full{newline}Name"}
            structured = {
                "components": [
                    {"kind": "given", "value": f"Given{newline}Name"},
                    {"kind": "separator", "value": f"/{newline}"},
                    {"kind": "surname", "value": "Surname"},
                    {"kind": "surname2", "value": "Other"},
                ],
                "isOrdered": True,
                "defaultSeparator": f"{newline}·",
            }
            examples.extend(
                (contact, contact.name)
                for name in [full, structured]
                for contact in [save_contact(Contact(name=name))]
            )
        with self.browser_page():
            self.login()
            for contact, original in examples:
                url = f"{self.live_server_url}{reverse('wagtail_crm_contacts:edit', args=[contact.pk])}"
                self.page.goto(url)
                self.page.get_by_label("Email").fill("unrelated@example.test")
                self.page.get_by_role("button", name="Save", exact=True).click()
                self.page.goto(url)
                raw = self.page.locator("[data-name-payload]").input_value()
                posted = json.loads(raw)
                if "components" in original:
                    assert posted["values"] == [
                        part["value"] for part in original["components"]
                    ]
                    assert posted["separator"] == original["defaultSeparator"]
                    expected = contact.display_name.replace("\r\n", "\n").replace(
                        "\r", "\n"
                    )
                    expect(self.page.get_by_label("Generated full name")).to_have_value(
                        expected
                    )
                else:
                    assert posted["full"] == original["full"]
                self.page.get_by_role("button", name="Save", exact=True).click()
        for contact, original in examples:
            contact.refresh_from_db()
            assert contact.name == original

    def test_admin_user_without_crm_permission_cannot_open_contact_list(self):
        Contact.objects.create(display_name="Private Browser Example")
        with self.browser_page():
            self.login()
            response = self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:index')}"
            )
            assert response.status == 200
            expect(self.page).to_have_url(f"{self.live_server_url}/admin/")
            expect(
                self.page.get_by_role("link", name="Contacts", exact=True)
            ).to_have_count(0)
            expect(
                self.page.get_by_text("Private Browser Example", exact=True)
            ).to_have_count(0)
