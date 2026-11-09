import os
import re
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import expect, sync_playwright

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
                codename__in=["add_payment", "view_payment"],
            ),
        )

    def test_upload_preview_confirm_and_repeat(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"),
            )
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.goto(f"{self.live_server_url}/")
                page.get_by_label("Username").fill("ui-importer")
                page.get_by_label("Password").fill("synthetic-browser-password")
                page.get_by_role("button", name="Sign in", exact=True).click()

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
