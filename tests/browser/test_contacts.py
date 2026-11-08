import os
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from playwright.sync_api import expect, sync_playwright

from wagtail_crm.models import Contact


@pytest.mark.browser
class TestContactBrowser(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(
                headless=True,
                executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"),
            )
        except Exception:
            cls.playwright.stop()
            super().tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            cls.browser.close()
            cls.playwright.stop()
        finally:
            super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ui-reviewer", password="synthetic-browser-password", is_staff=True
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="wagtailadmin", codename="access_admin"
            )
        )
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 1000}
        )
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()

    def login(self):
        self.page.goto(f"{self.live_server_url}/admin/login/")
        self.page.get_by_label("Username", exact=True).fill("ui-reviewer")
        self.page.get_by_label("Password", exact=True).fill(
            "synthetic-browser-password"
        )
        self.page.get_by_role("button", name="Sign in", exact=True).click()
        expect(self.page).to_have_url(f"{self.live_server_url}/admin/")

    def test_editor_can_log_in_and_create_contact(self):
        self.user.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="wagtail_crm")
        )
        self.login()
        self.page.get_by_role("link", name="Contacts", exact=True).click()
        self.page.get_by_role("link", name="Add contact", exact=True).click()
        self.page.get_by_label("Display name", exact=True).fill("UI Example Meeting")
        self.page.get_by_label("Kind", exact=True).select_option("organization")
        self.page.get_by_label("Email", exact=True).fill("ui@example.invalid")
        self.page.get_by_role("button", name="Save", exact=True).click()
        expect(
            self.page.get_by_role("link", name="UI Example Meeting", exact=True)
        ).to_be_visible()
        assert Contact.objects.filter(display_name="UI Example Meeting").exists()

        if directory := os.environ.get("CRM_SCREENSHOTS_DIR"):
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(path / "contacts.png"), full_page=True)

    def test_admin_user_without_crm_permission_cannot_open_contact_list(self):
        Contact.objects.create(display_name="Private Browser Example")
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
