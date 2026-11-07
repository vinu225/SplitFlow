"""
Generates sample sponsorship agreement PDFs for testing contract parsing, source highlighting, and diffing.
"""
import os
import fitz  # PyMuPDF

os.makedirs("sample_contracts", exist_ok=True)

def create_sample_pdf(filename: str, version: int, milestone_2_amount: str, net_days: int):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 size

    # Header
    page.insert_text((50, 60), f"BRAND SPONSORSHIP STATEMENT OF WORK (v{version})", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.4))
    page.insert_text((50, 85), f"Contract Reference: SOW-NORDVPN-2026-00{version}", fontsize=10, fontname="helv", color=(0.4, 0.4, 0.4))

    # Parties
    page.insert_text((50, 120), "1. PARTIES & ENGAGEMENT", fontsize=12, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text((50, 140), "Brand Sponsor: NordVPN Global Media Operations", fontsize=10, fontname="helv")
    page.insert_text((50, 155), "Content Creator: Apex Media Studios LLC", fontsize=10, fontname="helv")

    # Scope
    page.insert_text((50, 190), "2. CAMPAIGN DELIVERABLES", fontsize=12, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text((50, 210), "Creator agrees to produce one (1) dedicated 90-second YouTube mid-roll sponsorship segment", fontsize=10, fontname="helv")
    page.insert_text((50, 225), "featuring NordVPN security benefits with custom tracking link in top video description.", fontsize=10, fontname="helv")

    # Financial Terms & Milestones
    page.insert_text((50, 260), "3. COMPENSATION & PAYMENT MILESTONES", fontsize=12, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text((50, 280), "Total campaign consideration shall be disbursed in two distinct milestones:", fontsize=10, fontname="helv")
    
    # Milestone 1
    page.insert_text((60, 305), "• Milestone 1: $2,500.00 USD (50% due upon mutual signing).", fontsize=10, fontname="helv")
    page.insert_text((75, 320), "Deliverable: Completed script draft and visual storyboards.", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))

    # Milestone 2
    page.insert_text((60, 345), f"• Milestone 2: ${milestone_2_amount} USD (50% within 14 days of video publish).", fontsize=10, fontname="helv")
    page.insert_text((75, 360), "Deliverable: Final video live publication with tracking telemetry.", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))

    # Payment Window & Clauses
    page.insert_text((50, 395), "4. SETTLEMENT TERMS & RISK COVENANTS", fontsize=12, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text((50, 415), f"All invoices issued under this agreement are subject to Net-{net_days} payment terms via PayPal.", fontsize=10, fontname="helv")
    page.insert_text((50, 430), "Cancellation Clause: Standard kill fee applies on early cancellation before production start.", fontsize=10, fontname="helv")
    page.insert_text((50, 445), "Exclusivity: Creator agrees to 30-day cybersecurity exclusivity following video live date.", fontsize=10, fontname="helv")

    # Signatures
    page.insert_text((50, 500), "APPROVED & ACCEPTED BY:", fontsize=10, fontname="helv", color=(0.2, 0.2, 0.2))
    page.insert_text((50, 540), "Authorized Signatory (NordVPN Global Media)", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))
    page.insert_text((300, 540), "Executive Producer (Apex Media Studios LLC)", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))

    doc.save(filename)
    doc.close()
    print(f"Generated {filename}")

create_sample_pdf("sample_contracts/NordVPN_Sponsorship_Agreement_v1.pdf", version=1, milestone_2_amount="2,500.00", net_days=15)
create_sample_pdf("sample_contracts/NordVPN_Sponsorship_Agreement_v2.pdf", version=2, milestone_2_amount="2,000.00", net_days=60)

