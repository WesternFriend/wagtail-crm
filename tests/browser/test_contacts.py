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

from wagtail_crm.contacts.models import Contact


@pytest.mark.browser
class TestContactBrowser(StaticLiveServerTestCase):
    serialized_rollback = True

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

    def allow_contacts(self):
        self.user.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="wagtail_crm_contacts")
        )

    def test_person_creation_editing_validation_search_inspect_and_history(self):
        self.allow_contacts()
        with self.browser_page():
            self.login()
            self.page.get_by_role("link", name="Contacts", exact=True).click()
            self.page.get_by_role("link", name="Add contact", exact=True).click()
            self.page.get_by_label("Given name", exact=True).fill("María del Carmen")
            self.page.get_by_label("Family name", exact=True).fill("García López")
            self.page.get_by_label("Postal address").fill(
                "Example Street\nHelsinki\nFinland"
            )
            self.page.get_by_label("Email", exact=True).fill("invalid@local")
            self.page.get_by_role("button", name="Create", exact=True).click()
            expect(
                self.page.get_by_text("Enter a valid email address.")
            ).to_be_visible()
            expect(self.page.get_by_label("Given name", exact=True)).to_have_value(
                "María del Carmen"
            )
            expect(self.page.get_by_label("Postal address")).to_have_value(
                "Example Street\nHelsinki\nFinland"
            )
            self.page.get_by_label("Email", exact=True).fill("")
            if directory := os.environ.get("CRM_SCREENSHOTS_DIR"):
                path = Path(directory)
                path.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(path=str(path / "person-form.png"), full_page=True)
            self.page.get_by_role("button", name="Create", exact=True).click()
            self.page.get_by_role(
                "link", name="María del Carmen García López", exact=True
            ).click()
            expect(self.page.get_by_label("Family name", exact=True)).to_have_value(
                "García López"
            )
            self.page.get_by_label("Given name", exact=True).fill("")
            self.page.get_by_label("Family name", exact=True).fill("王")
            self.page.get_by_role("button", name="Save", exact=True).click()
            self.page.get_by_placeholder("Search…", exact=True).fill("王")
            self.page.get_by_placeholder("Search…", exact=True).press("Enter")
            link = self.page.get_by_role("link", name="王", exact=True)
            expect(link).to_be_visible()
            pk = resolve(urlsplit(link.get_attribute("href")).path).kwargs["pk"]
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:inspect', args=[pk])}"
            )
            expect(self.page.locator("main")).to_contain_text("Finland")
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:history', args=[pk])}"
            )
            expect(
                self.page.get_by_role("columnheader", name="Action", exact=True)
            ).to_be_visible()
            expect(
                self.page.get_by_text("ui-reviewer", exact=True).last
            ).to_be_visible()

    def test_organization_uses_name_and_stock_delete_keeps_activity(self):
        self.allow_contacts()
        with self.browser_page():
            self.login()
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:add')}"
            )
            self.page.get_by_label("Contact type").select_option("organization")
            expect(self.page.get_by_label("Given name", exact=True)).to_be_hidden()
            expect(self.page.get_by_label("Family name", exact=True)).to_be_hidden()
            self.page.get_by_label("Name", exact=True).fill("Example Meeting")
            self.page.get_by_role("button", name="Create", exact=True).click()
            link = self.page.get_by_role("link", name="Example Meeting", exact=True)
            pk = resolve(urlsplit(link.get_attribute("href")).path).kwargs["pk"]
            link.click()
            expect(self.page.get_by_label("Name", exact=True)).to_have_value(
                "Example Meeting"
            )
            self.page.get_by_label("Name", exact=True).fill("Updated Meeting")
            self.page.get_by_role("button", name="Save", exact=True).click()
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:delete', args=[pk])}"
            )
            self.page.get_by_role("button", name="Yes, delete", exact=True).click()
            self.page.get_by_role("button", name="Reports", exact=True).click()
            self.page.get_by_role("link", name="Site history", exact=True).click()
            expect(
                self.page.get_by_text("Updated Meeting", exact=True).first
            ).to_be_visible()
            expect(self.page.get_by_text("Deleted", exact=True)).to_be_visible()

    def test_existing_contact_type_changes_use_ordinary_name_fields(self):
        self.allow_contacts()
        contact = Contact.objects.create(given_name="Type", family_name="Example")
        with self.browser_page():
            self.login()
            url = f"{self.live_server_url}{reverse('wagtail_crm_contacts:edit', args=[contact.pk])}"
            self.page.goto(url)
            self.page.get_by_label("Contact type").select_option("organization")
            expect(self.page.get_by_label("Given name", exact=True)).to_be_hidden()
            self.page.get_by_role("button", name="Save", exact=True).click()
            expect(
                self.page.get_by_text("Enter an organization name.", exact=True)
            ).to_be_visible()
            self.page.get_by_label("Name", exact=True).fill("Type Meeting")
            self.page.get_by_role("button", name="Save", exact=True).click()
            self.page.goto(url)
            self.page.get_by_label("Contact type").select_option("person")
            expect(self.page.get_by_label("Given name", exact=True)).to_be_visible()
            expect(self.page.get_by_label("Family name", exact=True)).to_be_visible()
            expect(self.page.get_by_label("Name", exact=True)).to_be_hidden()
            expect(self.page.get_by_label("Given name", exact=True)).to_have_value("")
            expect(self.page.get_by_label("Family name", exact=True)).to_have_value("")
            self.page.get_by_role("button", name="Save", exact=True).click()
            expect(
                self.page.get_by_text("Enter a given name or family name.", exact=True)
            ).to_be_visible()
            self.page.get_by_label("Given name", exact=True).fill("Jordan")
            self.page.get_by_role("button", name="Save", exact=True).click()
            self.page.goto(url)
            expect(self.page.get_by_label("Given name", exact=True)).to_have_value(
                "Jordan"
            )
            expect(self.page.get_by_label("Family name", exact=True)).to_have_value("")
        contact.refresh_from_db()
        assert contact.kind == "person"
        assert contact.name == ""
        assert contact.given_name == "Jordan"
        assert contact.family_name == ""

    def test_staff_without_contact_permissions_is_denied(self):
        Contact.objects.create(given_name="Private Browser Example")
        with self.browser_page():
            self.login()
            expect(
                self.page.get_by_role("link", name="Contacts", exact=True)
            ).to_have_count(0)
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:index')}"
            )
            expect(self.page).to_have_url(f"{self.live_server_url}/admin/")
            expect(
                self.page.get_by_text("Private Browser Example", exact=True)
            ).to_have_count(0)
