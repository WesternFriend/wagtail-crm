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
        self.page.goto(f"{self.live_server_url}/admin/login/")
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
            self.page.get_by_label("Name", exact=False).fill("UI Example Meeting")
            self.page.get_by_label("Kind").select_option("organization")
            self.page.get_by_label("Postal address").fill(
                "Example Friends Meeting\n〒100-8994 東京都千代田区\nJapan"
            )
            self.page.get_by_label("Email").fill("invalid@local")
            self.page.get_by_role("button", name="Create", exact=True).click()
            expect(
                self.page.get_by_text("Enter a valid email address.")
            ).to_be_visible()
            expect(self.page.get_by_label("Name", exact=False)).to_have_value(
                "UI Example Meeting"
            )
            self.page.get_by_label("Email").fill("ui@example.invalid")
            self.page.get_by_role("button", name="Create", exact=True).click()
            expect(
                self.page.get_by_role("link", name="UI Example Meeting", exact=True)
            ).to_be_visible()

            self.page.get_by_role("link", name="UI Example Meeting", exact=True).click()
            expect(self.page.get_by_label("Postal address")).to_have_value(
                "Example Friends Meeting\n〒100-8994 東京都千代田区\nJapan"
            )
            self.page.get_by_label("Name", exact=False).fill("Updated Example Meeting")
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
