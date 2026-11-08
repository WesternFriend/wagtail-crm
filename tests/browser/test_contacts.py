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

    def allow_contacts(self):
        self.user.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="wagtail_crm")
        )

    def test_editor_can_add_and_edit_person_on_one_ordinary_form(self):
        self.allow_contacts()
        with self.browser_page():
            self.login()
            self.page.get_by_role("link", name="Contacts", exact=True).click()
            self.page.get_by_role("link", name="Add contact", exact=True).click()
            given = self.page.get_by_label("Given name", exact=True)
            surname = self.page.get_by_label("Surname", exact=True)
            expect(given).to_be_visible()
            expect(surname).to_be_visible()
            assert given.get_attribute("required") is None
            assert surname.get_attribute("required") is None
            expect(self.page.locator('label[for="id_given_name"]')).not_to_contain_text(
                "*"
            )
            expect(self.page.locator('label[for="id_surname"]')).not_to_contain_text(
                "*"
            )
            expect(
                self.page.get_by_label("Organization name", exact=True)
            ).to_be_hidden()
            expect(
                self.page.get_by_text("Organization name", exact=True)
            ).to_be_hidden()
            expect(
                self.page.locator("[data-contact-name], [data-name-part]")
            ).to_have_count(0)
            expect(self.page.get_by_text("Join parts with", exact=True)).to_have_count(
                0
            )
            given.fill("Mary Beth")
            surname.fill("van Berg")
            self.page.get_by_label("Postal address").fill(
                "Example Street\nHelsinki\nFinland"
            )
            self.page.get_by_label("Email").fill("invalid@local")
            self.page.get_by_role("button", name="Create", exact=True).click()
            expect(
                self.page.get_by_text("Enter a valid email address.")
            ).to_be_visible()
            expect(given).to_have_value("Mary Beth")
            expect(surname).to_have_value("van Berg")
            self.page.get_by_label("Email").fill("synthetic@example.invalid")
            self.page.get_by_role("button", name="Create", exact=True).click()
            self.page.get_by_role("link", name="Mary Beth van Berg", exact=True).click()
            expect(given).to_have_value("Mary Beth")
            expect(surname).to_have_value("van Berg")
            given.fill("Mary Jane")
            if directory := os.environ.get("CRM_SCREENSHOTS_DIR"):
                path = Path(directory)
                path.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(path=str(path / "person-form.png"), full_page=True)
            self.page.get_by_role("button", name="Save", exact=True).click()
            edit_link = self.page.get_by_role(
                "link", name="Mary Jane van Berg", exact=True
            )
            pk = resolve(urlsplit(edit_link.get_attribute("href")).path).kwargs["pk"]
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:inspect', args=[pk])}"
            )
            expect(
                self.page.get_by_role("heading", name="Change history", exact=True)
            ).to_be_visible()
            expect(self.page.locator("#contact-postal-address")).to_contain_text(
                "Finland"
            )
        contact = Contact.objects.get()
        assert contact.display_name == "Mary Jane van Berg"
        assert contact.history.count() == 2
        assert contact.history.first().before["display_name"] == "Mary Beth van Berg"

    def test_single_names_and_combined_name_requirement(self):
        self.allow_contacts()
        with self.browser_page():
            self.login()
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:add')}"
            )
            self.page.get_by_label("Email").fill("retained@example.invalid")
            self.page.get_by_label("Postal address").fill("Retained address")
            self.page.get_by_role("button", name="Create", exact=True).click()
            expect(self.page.locator(".error-message").first).to_be_visible()
            expect(self.page.get_by_label("Email")).to_have_value(
                "retained@example.invalid"
            )
            expect(self.page.get_by_label("Postal address")).to_have_value(
                "Retained address"
            )
            self.page.get_by_label("Given name", exact=True).fill("Sukarno")
            self.page.get_by_role("button", name="Create", exact=True).click()
            expect(
                self.page.get_by_role("link", name="Sukarno", exact=True)
            ).to_be_visible()
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:add')}"
            )
            self.page.get_by_label("Surname", exact=True).fill("王")
            self.page.get_by_role("button", name="Create", exact=True).click()
            expect(self.page.get_by_role("link", name="王", exact=True)).to_be_visible()
        assert set(Contact.objects.values_list("display_name", flat=True)) == {
            "Sukarno",
            "王",
        }

    def test_existing_full_and_complex_names_survive_correspondence_edits(self):
        self.allow_contacts()
        examples = [
            save_contact(Contact(name={"full": "Unparsed Mary Beth van Berg"})),
            save_contact(
                Contact(
                    name={
                        "components": [
                            {"kind": "surname", "value": "Rivera"},
                            {"kind": "separator", "value": "・"},
                            {"kind": "surname", "value": "Barrientos"},
                            {"kind": "given", "value": "Diego Luis"},
                        ],
                        "isOrdered": True,
                        "defaultSeparator": "",
                    }
                )
            ),
        ]
        examples.append(
            save_contact(
                Contact(kind="organization", name={"full": "Existing\r\nOrganization"})
            )
        )
        examples.extend(
            [
                save_contact(Contact(name={"full": "Unparsed\r\nPerson"})),
                save_contact(
                    Contact(
                        name={
                            "components": [{"kind": "given", "value": "Given\r\nName"}],
                            "isOrdered": True,
                            "defaultSeparator": " ",
                        }
                    )
                ),
            ]
        )
        originals = [contact.name for contact in examples]
        with self.browser_page():
            self.login()
            for contact in examples:
                self.page.goto(
                    f"{self.live_server_url}{reverse('wagtail_crm_contacts:edit', args=[contact.pk])}"
                )
                expect(
                    self.page.get_by_text(
                        " ".join(contact.display_name.split()), exact=True
                    ).first
                ).to_be_visible()
                self.page.get_by_label("Email").fill("updated@example.invalid")
                self.page.get_by_role("button", name="Save", exact=True).click()
                expect(
                    self.page.get_by_role(
                        "link", name=" ".join(contact.display_name.split()), exact=True
                    )
                ).to_be_visible()
        for contact, original in zip(examples, originals, strict=True):
            contact.refresh_from_db()
            assert contact.name == original
            assert contact.email == "updated@example.invalid"

    def test_organization_retains_one_ordinary_name_field(self):
        self.allow_contacts()
        with self.browser_page():
            self.login()
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:add')}"
            )
            self.page.get_by_label("Kind").select_option("organization")
            expect(self.page.get_by_label("Given name", exact=True)).to_be_hidden()
            expect(self.page.get_by_label("Surname", exact=True)).to_be_hidden()
            expect(self.page.get_by_text("Given name", exact=True)).to_be_hidden()
            expect(self.page.get_by_text("Surname", exact=True)).to_be_hidden()
            self.page.get_by_label("Organization name", exact=True).fill(
                "Example Friends Meeting"
            )
            self.page.get_by_role("button", name="Create", exact=True).click()
            self.page.get_by_role(
                "link", name="Example Friends Meeting", exact=True
            ).click()
            self.page.get_by_label("Organization name", exact=True).fill(
                "Updated Example Meeting"
            )
            self.page.get_by_role("button", name="Save", exact=True).click()
            expect(
                self.page.get_by_role(
                    "link", name="Updated Example Meeting", exact=True
                )
            ).to_be_visible()
        contact = Contact.objects.get()
        assert contact.kind == Contact.Kind.ORGANIZATION
        assert contact.name == {"full": "Updated Example Meeting"}

    def test_kind_changes_keep_drafts_and_show_relevant_validation(self):
        self.allow_contacts()
        with self.browser_page():
            self.login()
            self.page.goto(
                f"{self.live_server_url}{reverse('wagtail_crm_contacts:add')}"
            )
            kind = self.page.get_by_label("Kind")
            given = self.page.get_by_label("Given name", exact=True)
            surname = self.page.get_by_label("Surname", exact=True)
            organization = self.page.get_by_label("Organization name", exact=True)
            given.fill("Retained given draft")
            surname.fill("Retained surname draft")
            kind.select_option("organization")
            organization.fill("Example Organization")
            kind.select_option("person")
            expect(given).to_have_value("Retained given draft")
            expect(surname).to_have_value("Retained surname draft")
            expect(given).to_be_enabled()
            expect(organization).to_be_disabled()
            kind.select_option("organization")
            expect(organization).to_have_value("Example Organization")
            self.page.get_by_label("Email").fill("invalid@local")
            self.page.get_by_role("button", name="Create", exact=True).click()
            expect(
                self.page.get_by_text("Enter a valid email address.")
            ).to_be_visible()
            expect(organization).to_have_value("Example Organization")
            expect(given).to_be_hidden()
            expect(given).to_be_disabled()
            self.page.get_by_label("Email").fill("valid@example.invalid")
            organization.fill("")
            self.page.get_by_role("button", name="Create", exact=True).click()
            expect(
                self.page.get_by_text("Enter an organization name.", exact=True)
            ).to_be_visible()
            organization.fill("Example Organization")
            self.page.get_by_role("button", name="Create", exact=True).click()
            self.page.get_by_role(
                "link", name="Example Organization", exact=True
            ).click()
            kind.select_option("person")
            expect(self.page.get_by_text("Recorded name:", exact=False)).to_be_visible()
            expect(given).to_have_value("")
            expect(surname).to_have_value("")
            self.page.get_by_role("button", name="Save", exact=True).click()
            self.page.get_by_role(
                "link", name="Example Organization", exact=True
            ).click()
            kind.select_option("organization")
            expect(organization).to_have_value("Example Organization")
            self.page.get_by_role("button", name="Save", exact=True).click()
        contact = Contact.objects.get()
        assert contact.kind == Contact.Kind.ORGANIZATION
        assert contact.name == {"full": "Example Organization"}
        assert contact.history.count() == 3

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
