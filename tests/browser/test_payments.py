import os
import re
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import expect, sync_playwright

from wagtail_crm.contacts.models import Contact
from wagtail_crm.payments.models import Payment

FIXTURES = Path(__file__).parent.parent / "fixtures" / "paypal"


@pytest.mark.browser
class TestPaymentImportBrowser(StaticLiveServerTestCase):
    serialized_rollback = True

    def setUp(self):
        user = get_user_model().objects.create_user(
            username="ui-importer", password="synthetic-browser-password", is_staff=True
        )
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="wagtailadmin", codename="access_admin"
            ),
            *Permission.objects.filter(
                content_type__app_label="wagtail_crm_payments",
                codename__in=["add_payment", "change_payment", "view_payment"],
            ),
            *Permission.objects.filter(content_type__app_label="wagtail_crm_contacts"),
        )

    def sign_in(self, browser):
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.live_server_url}/")
        page.get_by_label("Username").fill("ui-importer")
        page.get_by_label("Password").fill("synthetic-browser-password")
        page.get_by_role("button", name="Sign in", exact=True).click()
        return page

    def launch(self, playwright):
        return playwright.chromium.launch(
            headless=True,
            executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"),
        )

    def test_upload_preview_confirm_and_repeat(self):
        with sync_playwright() as playwright:
            browser = self.launch(playwright)
            try:
                page = self.sign_in(browser)
                page.get_by_role("link", name="Payments").click()
                page.get_by_role("link", name="Import PayPal CSV").click()
                page.get_by_label("PayPal activity CSV").set_input_files(
                    FIXTURES / "activity.csv"
                )
                page.get_by_role("button", name="Preview").click()
                expect(page.get_by_text("6 to import, 7 skipped")).to_be_visible()
                expect(
                    page.get_by_text("Status Pending is not imported")
                ).to_be_visible()

                page.get_by_role("button", name="Import 6 payments").click()
                expect(page.get_by_text("Imported 6 payments.")).to_be_visible()
                expect(page.get_by_text("jordan@example.org")).to_be_visible()

                page.get_by_role("link", name="Import PayPal CSV").click()
                page.get_by_label("PayPal activity CSV").set_input_files(
                    FIXTURES / "activity.csv"
                )
                page.get_by_role("button", name="Preview").click()
                expect(page.get_by_text("Nothing new to import.")).to_be_visible()
                confirm = page.get_by_role(
                    "button", name=re.compile(r"^Import \d+ payments$")
                )
                expect(confirm).to_have_count(0)
            finally:
                browser.close()
        assert Payment.objects.count() == 6

    def test_link_a_payment_to_a_new_contact(self):
        gift = Payment.objects.create(
            transaction_id="GIFT1",
            occurred_at="2026-03-01T12:00:00Z",
            name="Avery Example",
            email="avery@example.org",
            type="Donation Payment",
            event_code="T0013",
            status="Completed",
            currency="USD",
            gross="100.00",
            fee="-3.00",
            net="97.00",
        )
        with sync_playwright() as playwright:
            browser = self.launch(playwright)
            try:
                page = self.sign_in(browser)
                page.get_by_role("link", name="Payments").click()
                page.get_by_role("row").filter(has_text="Avery Example").get_by_role(
                    "link"
                ).first.click()
                page.get_by_role("button", name="Choose a contact").click()
                modal = page.get_by_role("dialog")
                modal.get_by_role("tab", name="Create").click()
                expect(modal.get_by_label("Name", exact=True)).to_be_hidden()
                modal.get_by_label("Given name").fill("Avery")
                modal.get_by_label("Family name").fill("Example")
                modal.get_by_role("button", name="Create").click()
                expect(modal).to_be_hidden()
                page.get_by_role("spinbutton", name="Charitable amount").fill("100.00")
                page.get_by_role("button", name="Save").click()
                expect(page.get_by_text("updated")).to_be_visible()
            finally:
                browser.close()
        gift.refresh_from_db()
        assert gift.donor == Contact.objects.get(display_name="Avery Example")
        assert str(gift.charitable_amount) == "100.00"

    def test_refunded_payment_shows_its_refund(self):
        common = {
            "name": "Drew Reader",
            "email": "drew@example.org",
            "status": "Completed",
            "currency": "USD",
        }
        Payment.objects.create(
            transaction_id="GIFT2",
            occurred_at="2026-04-02T12:00:00Z",
            type="Website Payment",
            event_code="T0006",
            gross="20.00",
            fee="-0.88",
            net="19.12",
            charitable_amount="20.00",
            **common,
        )
        Payment.objects.create(
            transaction_id="REFUND2",
            occurred_at="2026-04-09T12:00:00Z",
            type="Payment Refund",
            event_code="T1107",
            gross="-20.00",
            fee="0.59",
            net="-19.41",
            reference_transaction_id="GIFT2",
            **common,
        )
        with sync_playwright() as playwright:
            browser = self.launch(playwright)
            try:
                page = self.sign_in(browser)
                page.get_by_role("link", name="Payments").click()
                page.get_by_role("row").filter(has_text="April 2, 2026").filter(
                    has_text="Drew Reader"
                ).get_by_role("link").first.click()
                expect(
                    page.get_by_text("Adjusted charitable amount: 0.00")
                ).to_be_visible()
                page.get_by_role("link", name=re.compile(r"^-20\.00 on ")).click()
                expect(page.get_by_text("Refund of")).to_be_visible()
            finally:
                browser.close()
