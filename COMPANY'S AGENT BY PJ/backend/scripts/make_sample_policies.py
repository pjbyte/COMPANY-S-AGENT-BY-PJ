"""Generate three realistic company-policy PDFs into data/policies/.

These are the demo corpus for PolicyPilot. Content is fictional
(NimbusSoft Technologies Pvt. Ltd.) but written like real corporate
policies - numbered sections, concrete numbers, effective dates - so
retrieval, citations and the eval set behave like production data.

Run:  python scripts/make_sample_policies.py
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
)

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "policies"

POLICIES: list[dict] = [
    {
        "file": "Employee_Leave_and_Attendance_Policy.pdf",
        "title": "Employee Leave and Attendance Policy",
        "meta": "NimbusSoft Technologies Pvt. Ltd. | Version 3.2 | Effective 1 January 2025 | Owner: People Operations",
        "intro": (
            "This policy defines every category of leave available to NimbusSoft employees and the "
            "attendance expectations that apply across all offices. It applies to all full-time employees "
            "on the company payroll. Contractors and interns follow the provisions in their engagement "
            "letters. This document supersedes all earlier leave circulars."
        ),
        "sections": [
            ("Purpose and Scope", [
                "The purpose of this policy is to provide a fair, transparent and consistent framework "
                "for planning, requesting and approving time away from work. It balances employee "
                "well-being with business continuity. The policy covers annual leave, sick leave, "
                "casual leave, statutory leave, public holidays, leave without pay and daily attendance "
                "norms.",
            ]),
            ("Annual Leave (Privileged Leave)", [
                "Every full-time employee is entitled to 24 working days of annual leave per calendar "
                "year, credited at the rate of 2 days per completed month of service. Annual leave must "
                "be planned with your reporting manager and recorded in the HRMS portal.",
                "A maximum of 8 unused annual leave days may be carried forward into the next calendar "
                "year. Any balance above 8 days lapses on 31 December. Annual leave cannot be "
                "encashed during employment; unavailed leave is encashed at basic salary only at the "
                "time of full and final settlement.",
            ]),
            ("Sick Leave", [
                "Employees are entitled to 12 days of sick leave per calendar year. Sick leave is meant "
                "for personal illness, medical procedures and recovery, and cannot be carried forward "
                "to the next year.",
                "A medical certificate from a registered medical practitioner is mandatory for any sick "
                "leave of 3 or more consecutive working days. The certificate must be uploaded to the "
                "HRMS within 5 working days of returning to work. For hospitalisation lasting more "
                "than 5 days, intimate your manager within 48 hours and People Operations will assist "
                "with insurance formalities.",
            ]),
            ("Casual Leave", [
                "Employees may take up to 6 days of casual leave per calendar year for short personal "
                "matters, family events or emergencies. Casual leave cannot be taken for more than "
                "3 consecutive working days; anything longer must be applied for as annual leave or "
                "leave without pay.",
                "Casual leave does not accrue, cannot be carried forward and lapses at year end. "
                "Casual leave may be combined with a public holiday or weekend but not with annual leave.",
            ]),
            ("Maternity Leave", [
                "Female employees are entitled to 26 weeks of paid maternity leave as provided under "
                "the Maternity Benefit Act, 1961, of which up to 8 weeks may be taken before the "
                "expected delivery date. For the second and subsequent children, the entitlement is "
                "12 weeks.",
                "On returning from maternity leave, an employee may opt for work-from-home arrangements "
                "for up to 2 months with her reporting manager's consent, in line with the Remote Work "
                "and Expense Reimbursement Policy.",
            ]),
            ("Paternity Leave", [
                "Male employees are entitled to 10 working days of paid paternity leave, to be availed "
                "within 3 months of the birth or legal adoption of a child. Paternity leave may be "
                "taken in a single continuous block or split into at most two blocks with manager approval.",
            ]),
            ("Public Holidays", [
                "The company observes 12 paid public holidays per calendar year, published in the annual "
                "holiday calendar each January. In addition, every employee may choose 2 floating "
                "holidays per year to observe festivals of personal significance. Floating holidays must "
                "be applied for at least 3 working days in advance and cannot be carried forward.",
            ]),
            ("Leave Approval Workflow", [
                "All planned leave must be applied for in the HRMS portal at least 7 calendar days in "
                "advance, excluding emergencies and sick leave. The reporting manager is expected to "
                "approve or decline a request within 3 working days.",
                "If a request remains unactioned for more than 3 working days, the HRMS automatically "
                "escalates it to the People Operations team, who may approve it on the manager's behalf "
                "if the leave is within entitlement. Declined requests must carry a written reason.",
            ]),
            ("Leave Without Pay", [
                "Leave without pay (LWP) may be granted when no leave balance remains or for extended "
                "personal reasons such as higher education, sabbatical or family care. LWP requires "
                "approval of the Head of People Operations and is capped at 30 days per calendar year.",
                "During LWP the employment relationship continues but salary, provident fund "
                "contributions and benefit accruals are paused pro rata. Continuous LWP beyond 90 days "
                "may be treated as separation unless an extension is approved in writing.",
            ]),
            ("Attendance and Late Arrivals", [
                "Standard working hours are 9:30 to 18:30 with a core collaboration window from 10:00 "
                "to 16:00. Arriving later than 15 minutes after the start of your team's shift counts "
                "as a late mark.",
                "More than 6 late marks in a calendar quarter will result in the deduction of one day "
                "of casual leave. Persistent attendance issues are addressed under the disciplinary "
                "process, starting with a documented counselling conversation with your manager.",
            ]),
            ("Emergency and Uninformed Absence", [
                "In genuine emergencies, inform your reporting manager by phone or message before your "
                "shift begins, and regularise the absence in the HRMS within 2 working days. Any "
                "absence that is neither approved nor regularised for 3 consecutive working days may "
                "be treated as voluntary abandonment of employment under company rules.",
            ]),
            ("Contact and Interpretation", [
                "Questions about this policy should be directed to People Operations at hr@nimbussoft.example "
                "or raised through the HRMS helpdesk. People Operations owns the interpretation of this "
                "policy, and the company may amend it prospectively with notice to all employees.",
            ]),
        ],
    },
    {
        "file": "IT_Security_and_Acceptable_Use_Policy.pdf",
        "title": "IT Security and Acceptable Use Policy",
        "meta": "NimbusSoft Technologies Pvt. Ltd. | Version 5.1 | Effective 1 March 2025 | Owner: Information Security Office",
        "intro": (
            "This policy sets out the rules for using NimbusSoft information systems, devices and data "
            "securely. It applies to every employee, contractor and vendor account, and to every device "
            "that touches company data, whether issued by the company or personal. Following these rules "
            "is a condition of access to company systems."
        ),
        "sections": [
            ("Purpose and Scope", [
                "The purpose of this policy is to protect the confidentiality, integrity and availability "
                "of company and customer information. It covers password and authentication standards, "
                "device usage, remote access, software installation, data classification, email security, "
                "incident reporting, backups and workplace hygiene.",
            ]),
            ("Password Requirements", [
                "All account passwords must be at least 12 characters long. Passphrases of three or more "
                "unrelated words are strongly recommended over complex short passwords. Passwords must "
                "not reuse any of your last 5 passwords.",
                "There is no routine expiry for passwords; change your password immediately if you "
                "suspect it has been exposed, if the identity team notifies you of a breach, or after "
                "any suspected compromise. Passwords must never be shared, written on paper near your "
                "desk, or reused across personal and company accounts. A company-provided password "
                "manager is the approved place to store credentials.",
            ]),
            ("Multi-Factor Authentication", [
                "Multi-factor authentication (MFA) is mandatory for VPN access, corporate email, the "
                "HRMS, cloud consoles and all remote access. MFA must be via the approved authenticator "
                "app; SMS-based OTP is permitted only where an authenticator app cannot be installed.",
                "Employees with privileged or administrative access must use a hardware security key "
                "for all administrative logins. Losing your MFA device must be reported to the IT "
                "Service Desk immediately so the token can be revoked and re-issued the same day.",
            ]),
            ("Device Usage", [
                "Company data must be stored only on company-issued devices. Full-disk encryption "
                "(BitLocker on Windows, FileVault on macOS) is mandatory and must remain enabled at all "
                "times. Devices must auto-lock after a maximum of 5 minutes of inactivity, and you must "
                "lock your screen manually whenever you step away.",
                "Jailbroken or rooted devices may never connect to company systems. Operating systems "
                "and browsers must receive security updates within 14 days of release. Company devices "
                "must not be lent to family members or used to run unapproved business services.",
            ]),
            ("Remote Work Security", [
                "When working from home, co-working spaces or travel, connect to the company network "
                "only through the approved VPN client. Public Wi-Fi must never be used without the VPN. "
                "Home Wi-Fi networks must use WPA2 or WPA3 encryption with a unique password.",
                "Work data must not be downloaded to personal devices, personal cloud storage or "
                "personal email under any circumstances. Video calls discussing confidential matters "
                "must use the approved conferencing tool with waiting rooms enabled.",
            ]),
            ("Software Installation", [
                "Software may be installed only from the Company Software Portal, where titles are "
                "vetted and licensed. Employees do not have local administrator rights by default; "
                "elevation requests are made through the Service Desk and expire after 24 hours.",
                "Installing cracked, pirated or unapproved software is a critical violation of this "
                "policy, even on personal devices that also access company email. Browser extensions "
                "that read page content (including AI assistants and translators) must be approved "
                "before use on corporate data.",
            ]),
            ("Data Classification", [
                "All company information falls into one of four classes: Public, Internal, Confidential "
                "or Restricted. Public data may be shared freely. Internal data is for employees only. "
                "Confidential data (contracts, roadmaps, pricing) is shared on a need-to-know basis. "
                "Restricted data (customer PII, source code, financial records, credentials) may only "
                "be stored, processed and transmitted through approved systems with access logging.",
                "Restricted data must never be pasted into unapproved external tools, including public "
                "AI chatbots and translation sites. Sharing Restricted data with third parties requires "
                "a signed non-disclosure agreement and Information Security approval.",
            ]),
            ("Email and Phishing", [
                "Treat every unexpected email, SMS and chat message as potentially hostile. Verify "
                "payment-detail changes and credential requests by phone using known contact details, "
                "never by replying to the message itself.",
                "Report suspected phishing using the Report Phish button in your mail client within "
                "24 hours of receipt. Quarterly phishing simulations are mandatory; repeated failures "
                "trigger refresher training. Never open unexpected attachments in sandboxed or "
                "unprotected environments.",
            ]),
            ("Security Incident Reporting", [
                "Report any suspected security incident - lost device, clicked phishing link, malware "
                "alert, unauthorised access, data exposure - to security@nimbussoft.example or the "
                "24x7 hotline within 2 hours of discovery.",
                "Do not power off or attempt to clean a compromised device; disconnect it from the "
                "network and leave it on so evidence can be preserved. The Information Security Office "
                "owns all decisions about regulatory breach notification, including the 72-hour "
                "notification window under applicable data-protection law. Do not discuss incidents "
                "outside the response team.",
            ]),
            ("Backups and Retention", [
                "Endpoints are backed up nightly with a weekly full backup, and backups are retained on "
                "a 90-day rolling window. Server and cloud data follow service-specific retention "
                "schedules published by the platform team. Deleted files can be restored by the "
                "Service Desk within the retention window.",
            ]),
            ("Clear Desk and Clear Screen", [
                "Confidential documents must not be left unattended on desks or printers. Lock printed "
                "material away, use the confidential-waste shredder for disposal, and collect printouts "
                "immediately. Whiteboards used in meetings must be photographed and wiped at the end "
                "of the day.",
            ]),
            ("Violations and Enforcement", [
                "Violations are classified as minor (for example, an unlocked screen), major (unapproved "
                "software holding company data) or critical (data exfiltration, credential sharing). "
                "Consequences range from refresher training to access revocation and termination of "
                "employment, and may include legal action where laws are broken. Suspected violations "
                "are investigated by the Information Security Office with HR involvement.",
            ]),
        ],
    },
    {
        "file": "Remote_Work_and_Expense_Reimbursement_Policy.pdf",
        "title": "Remote Work and Expense Reimbursement Policy",
        "meta": "NimbusSoft Technologies Pvt. Ltd. | Version 2.0 | Effective 1 June 2025 | Owner: People Operations and Finance",
        "intro": (
            "This policy explains who may work remotely, what the company provides for a home office, "
            "and how work expenses are claimed and reimbursed. It applies to all employees of "
            "NimbusSoft Technologies and should be read together with the Employee Leave and Attendance "
            "Policy and the IT Security and Acceptable Use Policy."
        ),
        "sections": [
            ("Purpose and Scope", [
                "The company operates a hybrid-first model that combines in-office collaboration with "
                "remote flexibility. This policy defines remote work eligibility, availability "
                "expectations, home office support and the complete expense claim process, so that "
                "employees and managers share one clear set of rules.",
            ]),
            ("Remote Work Eligibility", [
                "Employees based in Bengaluru and Hyderabad work from the office at least 2 days per "
                "week; teams choose which days to anchor in-office for collaboration. Fully remote "
                "arrangements are exceptional and require written approval from both the department "
                "head and the Head of People Operations, usually limited to roles with no physical "
                "dependencies.",
                "Working from another city or country for more than 15 working days in a year requires "
                "HR approval in advance, both for tax and for security reasons. International remote "
                "work beyond 30 days may have payroll implications and is rarely approved.",
            ]),
            ("Core Hours and Availability", [
                "The core collaboration window is 11:00 to 16:00 IST. During core hours, remote "
                "employees must be reachable on the approved chat and conferencing tools and respond "
                "to direct messages within 60 minutes. Outside core hours, normal notice norms apply.",
                "Calendar accuracy is mandatory: update your calendar when stepping away for more than "
                "an hour, and keep your working location in your profile current so facilities and "
                "security can reach you in an emergency.",
            ]),
            ("Home Office Setup Stipend", [
                "The company provides a one-time home office setup stipend of Rs. 25,000 for approved "
                "fully remote employees and Rs. 10,000 for hybrid employees. The stipend covers desk, "
                "chair, monitor, keyboard, mouse, headset and web camera purchases.",
                "Claims must be submitted through the HRMS with receipts within 90 days of joining or "
                "of remote-approval date. Purchases above the stipend value are personal expenses. "
                "Items bought with the stipend remain company property for asset records.",
            ]),
            ("Internet Reimbursement", [
                "Fully remote employees are reimbursed Rs. 1,500 per month toward home internet. Hybrid "
                "employees are not eligible for internet reimbursement. Claims are filed monthly with "
                "a copy of the bill; claims without a bill copy are rejected by the finance system "
                "automatically.",
            ]),
            ("Expense Limits and Approvals", [
                "All business expenses require pre-approval through the expense tool. Expenses below "
                "Rs. 5,000 are approved by the reporting manager. Expenses between Rs. 5,000 and "
                "Rs. 15,000 require manager and finance approval. Expenses above Rs. 15,000 require "
                "vice-president approval in addition.",
                "Claims must be submitted within 30 days of the expense date; older claims lapse "
                "automatically. Every claim needs an itemised bill or invoice; cash memos without GST "
                "details above Rs. 1,000 are not accepted. Personal expenses mixed into a business "
                "invoice are a policy violation.",
            ]),
            ("Travel and Commute", [
                "Daily commute between home and the office is not reimbursable for hybrid employees. "
                "Travel to client sites is governed by the Travel Policy; book through the approved "
                "travel desk. For air travel, economy class is standard for flights under 6 hours; "
                "premium economy requires vice-president approval for longer flights. Hotel ceilings "
                "are Rs. 6,000 per night in metro cities and Rs. 4,500 elsewhere.",
            ]),
            ("Company Equipment", [
                "Every employee receives a company laptop, refreshed every 3 years. Accessories such "
                "as keyboards, mice and headsets are replaced on request every 2 years through the "
                "Service Desk. Damage caused by negligence may be charged to the employee after "
                "review by People Operations.",
                "All company equipment must be returned within 10 working days of your last working "
                "day during exit clearance. Uncollected notices are sent to the personal email on "
                "record, and unreturned assets are recovered from the final settlement.",
            ]),
            ("Home Office Safety", [
                "Employees are responsible for the safety of their home workspace, including electrical "
                "safety and ergonomics. The company is not liable for home accidents outside the scope "
                "of employment. Employees may request an ergonomics consultation from People Operations "
                "at any time.",
            ]),
            ("Tax Treatment and Documentation", [
                "Reimbursements made against valid bills for official purposes are treated as "
                "non-taxable reimbursements under applicable Income Tax rules. Claims without "
                "supporting bills are treated as taxable perquisites and taxed in payroll. The home "
                "office stipend may have tax implications depending on current rules; Finance publishes "
                "an annual note before tax filing season.",
            ]),
            ("Stipend Clawback on Early Exit", [
                "If an employee resigns within 6 months of receiving the home office setup stipend, "
                "50 percent of the stipend is recovered in the final settlement. After 6 months of "
                "service no clawback applies. Internet reimbursements already paid are not clawed back.",
            ]),
        ],
    },
]

styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle("PPolicyTitle", parent=styles["Title"], fontSize=20, leading=26, spaceAfter=6)
META_STYLE = ParagraphStyle("PMeta", parent=styles["Normal"], fontSize=9, textColor="#555555", spaceAfter=18)
SECTION_STYLE = ParagraphStyle("PSection", parent=styles["Heading1"], fontSize=14, spaceBefore=16, spaceAfter=8)
BODY_STYLE = ParagraphStyle("PBody", parent=styles["Normal"], fontSize=10.5, leading=15.5, alignment=TA_JUSTIFY, spaceAfter=8)


def render_policy(policy: dict, out_path: Path) -> None:    doc = BaseDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
        title=policy["title"],
        author="NimbusSoft Technologies Pvt. Ltd.",
        subject=policy["meta"],
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor("#777777")
        canvas.drawString(doc_.leftMargin, 1.1 * cm, f'{policy["title"]} - NimbusSoft Technologies Pvt. Ltd.')
        canvas.drawRightString(A4[0] - doc_.rightMargin, 1.1 * cm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=footer)])

    story = [Paragraph(policy["title"], TITLE_STYLE), Paragraph(policy["meta"], META_STYLE)]
    story.append(Paragraph(policy["intro"], BODY_STYLE))
    for number, (section, paragraphs) in enumerate(policy["sections"], start=1):
        story.append(Paragraph(f"SECTION {number}: {section}", SECTION_STYLE))
        for para in paragraphs:
            story.append(Paragraph(para, BODY_STYLE))
    doc.build(story)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for policy in POLICIES:
        out_path = OUT_DIR / policy["file"]
        render_policy(policy, out_path)
        print(f"created {out_path.name}")


if __name__ == "__main__":
    main()
