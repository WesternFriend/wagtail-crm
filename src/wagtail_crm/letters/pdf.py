"""A plain acknowledgment letter; layout and wording can be refined later."""

from io import BytesIO

from django.utils.html import escape
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def render_pdf(values):
    """PDF bytes for a letter's stored values."""
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    story = [
        Paragraph(escape(values["date"]), body),
        Spacer(1, 0.3 * inch),
        Paragraph(escape(values["name"]), body),
        *(Paragraph(escape(line), body) for line in values["address"].splitlines()),
        Spacer(1, 0.3 * inch),
        Paragraph("Acknowledgment of contributions", styles["Heading2"]),
    ]
    if values["corrects"]:
        story.append(
            Paragraph(
                escape(f"This letter corrects the letter dated {values['corrects']}."),
                body,
            )
        )
    story += [
        Paragraph(
            escape(
                "Thank you for your contributions received from "
                f"{values['start']} to {values['end']}:"
            ),
            body,
        ),
        Spacer(1, 0.2 * inch),
        Table(
            [
                ["Date", "Reference", "Received", "Charitable", "Goods or services"],
                *(
                    [
                        line["date"],
                        line["transaction_id"],
                        line["gross"],
                        line["amount"],
                        line["goods_or_services"],
                    ]
                    for line in values["lines"]
                ),
                ["", "Total charitable (USD)", "", values["total"], ""],
            ],
            hAlign="LEFT",
            style=TableStyle([("ALIGN", (2, 0), (-1, -1), "RIGHT")]),
        ),
    ]
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        title="Acknowledgment of contributions",
        # One-page letters stay small uncompressed, and their text stays
        # searchable in the bytes.
        pageCompression=0,
    )
    document.build(story)
    return buffer.getvalue()
