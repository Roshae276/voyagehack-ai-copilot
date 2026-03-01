from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import os

OUTPUT_DIR = "quotes"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


def generate_quote_pdf(data, payment_link=None):

    filename = f"{OUTPUT_DIR}/quote_{int(datetime.utcnow().timestamp())}.pdf"

    c = canvas.Canvas(filename, pagesize=A4)

    y = 800

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "VoyageHack AI Travel Quote")

    y -= 40

    flights = data.get("TopFlights", [])

    if flights:

        f = flights[0]

        c.setFont("Helvetica", 12)

        c.drawString(
            50, y,
            f"Flight: {f.get('Airline')} ₹{f.get('SellingPrice')}"
        )

        y -= 30

    hotels = data.get("TopHotels", [])

    if hotels:

        h = hotels[0]

        c.drawString(
            50, y,
            f"Hotel: {h.get('HotelName')} ₹{h.get('SellingPrice')}"
        )

        y -= 30

    c.drawString(
        50, y,
        f"Total Price: ₹{data.get('TotalTripPrice',0)}"
    )

    y -= 20

    c.drawString(
        50, y,
        f"Commission: ₹{data.get('TotalCommission',0)}"
    )

    y -= 40

    if payment_link:

        c.setFont("Helvetica-Bold", 14)

        c.drawString(50, y, "Payment Link:")

        y -= 20

        c.setFont("Helvetica", 12)

        c.drawString(50, y, payment_link)

    c.save()

    return filename

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import os

OUTPUT_DIR = "quotes"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# ============================
# USER PDF (NO COMMISSION)
# ============================

def generate_user_pdf(data, payment_link=None):

    filename = f"{OUTPUT_DIR}/user_quote_{int(datetime.utcnow().timestamp())}.pdf"

    c = canvas.Canvas(filename, pagesize=A4)

    y = 800

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "VoyageHack Travel Quotation")

    y -= 40

    # Flights
    flights = data.get("TopFlights", [])

    if flights:

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Flight Options:")
        y -= 20

        for f in flights:

            c.setFont("Helvetica", 12)
            c.drawString(
                50, y,
                f"{f.get('Airline')} - ₹{f.get('SellingPrice')}"
            )
            y -= 20

        y -= 10

    # Hotels
    hotels = data.get("TopHotels", [])

    if hotels:

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Hotel Options:")
        y -= 20

        for h in hotels:

            c.setFont("Helvetica", 12)
            c.drawString(
                50, y,
                f"{h.get('HotelName')} - ₹{h.get('SellingPrice')}"
            )
            y -= 20

        y -= 10

    # Payment link
    if payment_link:

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Payment Link:")
        y -= 20

        c.setFont("Helvetica", 12)
        c.drawString(50, y, payment_link)

    c.save()

    return filename


# ============================
# AGENT PDF (WITH COMMISSION)
# ============================

def generate_agent_pdf(data):

    filename = f"{OUTPUT_DIR}/agent_quote_{int(datetime.utcnow().timestamp())}.pdf"

    c = canvas.Canvas(filename, pagesize=A4)

    y = 800

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "VoyageHack Agent Commission Report")

    y -= 40

    flights = data.get("TopFlights", [])

    for f in flights:

        c.setFont("Helvetica", 12)
        c.drawString(
            50, y,
            f"{f.get('Airline')} Price ₹{f.get('SellingPrice')} Commission ₹{f.get('Commission')}"
        )
        y -= 20

    hotels = data.get("TopHotels", [])

    for h in hotels:

        c.drawString(
            50, y,
            f"{h.get('HotelName')} Price ₹{h.get('SellingPrice')} Commission ₹{h.get('Commission')}"
        )
        y -= 20

    c.drawString(
        50, y,
        f"Total Commission ₹{data.get('TotalCommission')}"
    )

    c.save()

    return filename