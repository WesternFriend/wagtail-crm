# Rehearse a PayPal reporting period

## Prepare a synthetic January download

Follow the [development setup](development.md#setup) with a fresh SQLite file. Set `DATABASE_URL` in the shell **before** migrating, seeding and starting the server. Use the setup superuser to open **Settings → Users → Add a user**. Enter a separate username and password. On the **Roles** tab, select **CRM Editors** under **Groups**, leave **Administrator** unchecked and choose **Create**. Sign out and use the new login for the rehearsal. The demo provides Alex Example and Jordan Sample.

From the repository root, generate the file for the Editor. The script uses a fixed Faker seed and includes 102 January transactions. The first week has two gifts, a partial refund and a pending payment. The later rows exercise the upload at volume while keeping the period small enough to review by hand.

```sh
mkdir -p .data
mise exec -- uv run --script scripts/rehearse_paypal.py > .data/january-activity.csv
```

## Run January 1–7, 2026 with the Editor

Use the keyboard and the Editor's preferred browser zoom throughout the cycle. Note any control they cannot reach or read.

1. In **Payments → Import PayPal CSV**, preview the file. Expect **101 to import, 1 skipped**. Review the reason for Jordan's pending payment and confirm. Preview the same file again and verify there's nothing new to import.
2. In **Payments**, search for Alex Example. Open the $300 received payment, choose the demo contact Alex Example and enter $300 as charitable. Reopen it and follow the $75 refund back to its original payment. The adjusted charitable amount is $225. Link Jordan's $50 received payment to Jordan Sample and enter $50 as charitable.
3. In **Payments → Record check**, enter check **1001** for Alex, received January 6, 2026. Enter $50 for both the amount and the charitable amount. Search for 1001 and confirm it appears once.
4. In **Reconciliations → Add reconciliation**, enter January 1 through January 7, inclusive, and the figures below. Create the reconciliation and reopen it. All five differences should read **None**. The mailed check should appear separately with gross $50. Accept and save once the comparison matches.
5. In **Letters → Donors due a letter**, select the accepted week. With the demo's $250 threshold, Alex is due **$275** ($225 plus the $50 check). Issue from Alex's row. Preview the PDF, check both contributions including **Check 1001**, and issue the letter. Reopen the due list and verify it's empty.
6. Find the issued letter under **Not sent**. Record a simulated failed postal dispatch with a note and check its date against the Editor's local date. Find it under **Sending failed**, record a successful retry, then find it under **Sent**. Open the dispatch's **Edit** link and view its **History**. Issue a synthetic correction from the letter and check that the original shows **Superseded** and the correction shows **Not sent**.

| PayPal field | Independent total for January 1–7 (USD) |
| --- | ---: |
| Count received | 2 |
| Gross received | 350.00 |
| Fees on receipts | -10.50 |
| Net received | 339.50 |
| Refund gross | -75.00 |

Ask the Editor where they looked for the due list and dispatch history, whether the date default worked for them, and how they checked for duplicate check entry. Record their assessment and any reproducible problems on [#11](https://github.com/WesternFriend/wagtail-crm/issues/11).

## Compare a real export in the restricted pilot

Once staff have the [restricted pilot environment](https://github.com/WesternFriend/wagtail-crm/issues/13), use its individual staff accounts. Keep the export, donor details and supporting figures in the pilot's private storage.

1. Choose a reporting period. Record its UTC start and exclusive end (midnight after the last day). Confirm the PayPal report's time zone and boundary transactions. If the account uses local dates, export enough surrounding days to cover the UTC interval, then restrict the independent comparison to that interval using each row's time zone.
2. Export an Activity Download CSV with **Transaction Event Code** selected. Check that it also contains **Reference Txn ID** and **Balance Impact**. Record the row count, file size, date format and time zone values privately. [PayPal report fields](https://developer.paypal.com/reports/activity-download/)
3. Preview the file. Account for skipped statuses, currencies and transaction types. Investigate unexpected skips, reversals or changes to a known transaction ID before confirming.
4. Have the Bookkeeper independently confirm PayPal's figures for the same UTC range. Compare the count, gross, fees and net of completed USD incoming payments and the separate signed gross of completed USD refunds. Exclude mailed checks and withdrawals. If the report covers different activity, keep the discrepancy visible until staff can explain it. Review any partial refund allocation with the Bookkeeper.
5. Confirm the import. If it warns that imported activity changed an accepted period, review that period against its acceptance History with the Bookkeeper. Resolve the in-period payments and refunds.
6. In **Reconciliations**, enter the UTC start date and the calendar day before the exclusive end as **End**. For an exclusive end of January 8 at 00:00 UTC, enter January 7. Enter the Bookkeeper's figures. Compare all five differences before accepting. Record the result and any format differences on [#12](https://github.com/WesternFriend/wagtail-crm/issues/12) using synthetic examples for public reports. The pilot ends at reconciliation unless Brylie authorizes issuing real letters.
