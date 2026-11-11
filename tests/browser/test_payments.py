import os
import re
import tempfile
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.files.storage import FileSystemStorage
from playwright.sync_api import expect, sync_playwright

from wagtail_crm.contacts.models import Contact
from wagtail_crm.letters.models import Letter
from wagtail_crm.payments.models import Payment, Reconciliation

FIXTURES = Path(__file__).parent.parent / "fixtures" / "paypal"


@pytest.mark.browser
class TestPaymentImportBrowser(StaticLiveServerTestCase):
    serialized_rollback = True

    def setUp(self):
        # Issued PDFs go to a temporary folder, not the development data.
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        field = Letter._meta.get_field("pdf")
        self.addCleanup(setattr, field, "storage", field.storage)
        field.storage = FileSystemStorage(folder.name)
        user = get_user_model().objects.create_user(
            username="ui-importer", password="synthetic-browser-password", is_staff=True
        )
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="wagtailadmin", codename="access_admin"
            ),
            *Permission.objects.filter(
                content_type__app_label="wagtail_crm_payments",
                codename__in=[
                    "add_payment",
                    "change_payment",
                    "view_payment",
                    "add_reconciliation",
                    "change_reconciliation",
                    "view_reconciliation",
                ],
            ),
            *Permission.objects.filter(content_type__app_label="wagtail_crm_contacts"),
            *Permission.objects.filter(
                content_type__app_label="wagtail_crm_letters",
                codename__in=["add_letter", "view_letter"],
            ),
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

    def test_reconcile_and_accept_a_year(self):
        Payment.objects.create(
            transaction_id="GIFT3",
            occurred_at="2026-03-01T12:00:00Z",
            name="Avery Example",
            type="Donation Payment",
            event_code="T0013",
            status="Completed",
            currency="USD",
            gross="100.00",
            fee="-3.00",
            net="97.00",
            charitable_amount="100.00",
        )
        with sync_playwright() as playwright:
            browser = self.launch(playwright)
            try:
                page = self.sign_in(browser)
                page.get_by_role("link", name="Reconciliations").click()
                page.get_by_role("link", name="Add reconciliation").click()
                page.get_by_label("Start").fill("2026-01-01")
                page.get_by_label("End").fill("2026-12-31")
                page.get_by_label("PayPal count").fill("1")
                page.get_by_label("PayPal gross").fill("110.00")
                page.get_by_label("PayPal fees").fill("-3.00")
                page.get_by_label("PayPal net").fill("97.00")
                page.get_by_label("PayPal refunds").fill("0")
                page.get_by_role("button", name="Create").click()
                page.get_by_role("link", name="2026-01-01 to 2026-12-31").click()
                expect(page.get_by_text("-10.00", exact=True)).to_be_visible()
                page.get_by_role("checkbox", name="Accept this reconciliation").check()
                page.get_by_role("button", name="Save").click()
                page.get_by_role("link", name="2026-01-01 to 2026-12-31").click()
                expect(page.get_by_text("can no longer be changed")).to_be_visible()
            finally:
                browser.close()

    def test_preview_issue_and_correct_a_letter(self):
        avery = Contact.objects.create(
            given_name="Avery", family_name="Example", postal_address="1 Example Street"
        )
        Payment.objects.create(
            transaction_id="GIFT4",
            occurred_at="2026-03-01T12:00:00Z",
            name="Avery Example",
            type="Donation Payment",
            event_code="T0013",
            status="Completed",
            currency="USD",
            gross="100.00",
            fee="-3.00",
            net="97.00",
            donor=avery,
            charitable_amount="100.00",
        )
        Reconciliation.objects.create(
            start="2026-01-01",
            end="2026-12-31",
            paypal_count=1,
            paypal_gross="100.00",
            paypal_fees="-3.00",
            paypal_net="97.00",
            paypal_refunds="0",
            accepted_at="2027-01-05T12:00:00Z",
        )
        with sync_playwright() as playwright:
            browser = self.launch(playwright)
            try:
                page = self.sign_in(browser)
                page.get_by_role("link", name="Letters").click()
                page.get_by_role("link", name="Issue letter").click()
                page.get_by_role("button", name="Choose a contact").click()
                modal = page.get_by_role("dialog")
                modal.get_by_role("link", name="Avery Example").click()
                expect(modal).to_be_hidden()
                page.get_by_role("combobox", name="Period").select_option(
                    label="2026-01-01 to 2026-12-31"
                )
                with page.context.expect_event(
                    "response",
                    lambda r: r.headers.get("content-type") == "application/pdf",
                ) as preview:
                    page.get_by_role("button", name="Preview PDF").click()
                assert preview.value.ok

                page.get_by_role("button", name="Issue letter").click()
                expect(page.get_by_text("Issued Avery Example")).to_be_visible()
                expect(page.get_by_text("GIFT4: 100.00 charitable")).to_be_visible()
                with page.expect_download() as download:
                    page.get_by_role("link", name="Download PDF").click()
                assert download.value.suggested_filename.endswith(".pdf")

                page.get_by_role("link", name="Issue correction").click()
                expect(page.get_by_text("This letter corrects")).to_be_visible()
                page.get_by_role("button", name="Issue letter").click()
                expect(page.get_by_text("the letter dated")).to_be_visible()
            finally:
                browser.close()
        # Preview saved nothing: only the original and its correction exist.
        assert Letter.objects.count() == 2
        assert Letter.objects.filter(corrects__isnull=False).count() == 1
