# /// script
# requires-python = ">=3.12"
# dependencies = ["Faker==37.4.0"]
# ///
"""Write a synthetic January Activity Download to stdout for the Editor rehearsal."""

import csv
import sys
from decimal import Decimal

from faker import Faker

# https://developer.paypal.com/reports/activity-download/
COLUMNS = (
    "Date",
    "Time",
    "TimeZone",
    "Name",
    "Type",
    "Status",
    "Currency",
    "Gross",
    "Fee",
    "Net",
    "From Email Address",
    "To Email Address",
    "Transaction ID",
    "Reference Txn ID",
    "Transaction Event Code",
    "Balance Impact",
)


def activity_row(number, day, donor, gross, *, refund_of="", pending=False):  # noqa: PLR0913
    name, email = donor
    fee = Decimal("0.00") if refund_of else -Decimal(gross) * Decimal("0.03")
    account = "giving@example.invalid"
    return (
        f"01/{day:02}/2026",
        "12:00:00",
        "GMT",
        name,
        "Payment Refund" if refund_of else "Donation Payment",
        "Pending" if pending else "Completed",
        "USD",
        gross,
        f"{fee:.2f}",
        f"{Decimal(gross) + fee:.2f}",
        account if refund_of else email,
        email if refund_of else account,
        f"DEMO{number:013}",
        refund_of,
        "T1107" if refund_of else "T0013",
        "Debit" if refund_of else "Credit",
    )


def main():
    fake = Faker("en_US")
    fake.seed_instance(11)
    writer = csv.writer(sys.stdout)
    writer.writerow(COLUMNS)
    alex = ("Alex Example", "alex@example.invalid")
    jordan = ("Jordan Sample", "jordan@example.invalid")
    writer.writerow(activity_row(1, 2, alex, "300.00"))
    writer.writerow(activity_row(2, 3, jordan, "50.00"))
    writer.writerow(activity_row(3, 4, alex, "-75.00", refund_of="DEMO0000000000001"))
    writer.writerow(activity_row(4, 5, jordan, "25.00", pending=True))
    # The rest of the download exercises the preview at volume, outside the week
    # staff will reconcile and classify by hand.
    for number in range(5, 103):
        dollars = fake.random_int(min=5, max=500)
        writer.writerow(
            activity_row(
                number,
                fake.random_int(min=8, max=31),
                (fake.name(), f"donor{number}@example.invalid"),
                f"{dollars}.00",
            )
        )


if __name__ == "__main__":
    main()
