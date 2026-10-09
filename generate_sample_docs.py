import os
import json
import csv
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_sample_documents(target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate Academic Regulations & Handbook PDF (Multi-page PDF)
    pdf_path = target_dir / "college_handbook_2026.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=14
    )
    h1_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1D4ED8'),
        spaceBefore=12,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=8
    )

    story = []

    # Page 1: Title & Attendance Policy
    story.append(Paragraph("GOVERNMENT ACCREDITED ENGINEERING & ARTS COLLEGE", title_style))
    story.append(Paragraph("Official Student Handbook & Academic Guidelines 2026", styles['Heading3']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("Section 1: Attendance Rules and Minimum Requirement", h1_style))
    story.append(Paragraph(
        "1.1 Regular Attendance Requirement: Every registered student is mandatory to secure a minimum of <b>75% attendance</b> "
        "in every course across lecture, tutorial, and practical sessions to be eligible to appear for the End-Semester Examinations.",
        body_style
    ))
    story.append(Paragraph(
        "1.2 Condonation of Attendance Shortage: Students having attendance between <b>65% and 74%</b> due to certified medical reasons, "
        "hospitalization, or authorized participation in official sports/symposiums may be granted condonation upon submitting "
        "valid medical certificates within 3 working days and paying the prescribed condonation fee of Rs. 1,000.",
        body_style
    ))
    story.append(Paragraph(
        "1.3 Disqualification (Redo/Detention): Students who secure attendance <b>below 65%</b> are strictly not eligible to write "
        "the semester examinations. Such candidates must repeat the entire semester in the subsequent academic year.",
        body_style
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Section 2: Examination and Grading Regulations", h1_style))
    story.append(Paragraph(
        "2.1 Assessment Breakdown: Continuous Internal Assessment (CIA) carries 40% weightage, and the End-Semester Examination carries 60% weightage. "
        "Students must score at least 45% in the end-semester exam and 50% aggregate overall to obtain a passing grade.",
        body_style
    ))
    story.append(Paragraph(
        "2.2 Revaluation & Photocopy of Answer Scripts: A student who wishes to apply for revaluation of their theory answer script "
        "must first apply for a photocopy of the answer paper within 10 days of results publication by paying Rs. 300 per subject. "
        "Upon review by the course faculty, revaluation may be requested with a fee of Rs. 600 per subject.",
        body_style
    ))

    # Page 2: Library & Hostel Regulations
    story.append(PageBreak())
    story.append(Paragraph("Section 3: Library Rules & Borrowing Entitlement", h1_style))
    story.append(Paragraph(
        "3.1 Working Hours: The Central Library remains open on all working days from 8:30 AM to 7:00 PM. During semester examinations, "
        "library reading halls remain accessible until 9:00 PM.",
        body_style
    ))
    story.append(Paragraph(
        "3.2 Book Borrowing Policy: Undergraduate students are eligible to borrow up to <b>4 books for a duration of 14 days</b>. "
        "Postgraduate students may borrow up to 6 books for 21 days. Renewal is permitted once if no reservations exist.",
        body_style
    ))
    story.append(Paragraph(
        "3.3 Overdue Fines: A late return fine of <b>Rs. 5 per day per book</b> is levied for the first week of delay, and <b>Rs. 10 per day</b> thereafter. "
        "Loss of book requires replacement with the latest edition or payment of double the book cost.",
        body_style
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Section 4: Campus Code of Conduct and Anti-Ragging Policy", h1_style))
    story.append(Paragraph(
        "4.1 Anti-Ragging Statutory Warning: Ragging in any form is completely prohibited inside and outside the college campus as per Supreme Court directives. "
        "Any student found guilty of ragging will face immediate suspension, rustication, and filing of a First Information Report (FIR) with the local police. "
        "Toll-free Anti-Ragging Helpline: 1800-180-5522. College Committee Head: Prof. S. Ramanathan (Phone: 9444102030).",
        body_style
    ))
    story.append(Paragraph(
        "4.2 Dress Code: Formal and neat attire is expected on all working days. Collared shirts and trousers for boys; salwar kameez or formal attire for girls. "
        "Lab coats and safety shoes are compulsory during engineering laboratory and workshop hours.",
        body_style
    ))

    doc.build(story)
    print(f"Generated PDF: {pdf_path}")

    # 2. Generate Academic Regulations Text file
    txt_path = target_dir / "academic_regulations.txt"
    txt_content = """# COLLEGE ACADEMIC REGULATIONS & TIMETABLE TIMINGS

## SECTION 1: DAILY TIMETABLE & WORKING HOURS
- College General Shift: 8:45 AM to 4:15 PM (Monday through Friday).
- Period 1: 8:45 AM - 9:40 AM
- Period 2: 9:40 AM - 10:35 AM
- Tea Break: 10:35 AM - 10:50 AM
- Period 3: 10:50 AM - 11:45 AM
- Period 4: 11:45 AM - 12:40 PM
- Lunch Interval: 12:40 PM - 1:30 PM
- Period 5 (Lab / Theory): 1:30 PM - 2:25 PM
- Period 6 (Lab / Theory): 2:25 PM - 3:20 PM
- Period 7 (Library / Sports / Mentoring): 3:20 PM - 4:15 PM

## SECTION 2: ON-DUTY (OD) LEAVE REGULATIONS
- Students representing the institution in authorized sports competitions, cultural events, hackathons, or national symposia can claim On-Duty (OD) attendance.
- Maximum permitted OD leave is 10 working days per semester.
- Prior approval must be obtained from the respective Head of the Department (HOD) at least 2 days prior to the event date.

## SECTION 3: SEMESTER EXAM HALL TICKET ISSUANCE
- Hall tickets for semester examinations are issued 5 days before the commencement of the exam.
- Clearance of all semester tuition fees, library dues, and hostel dues is mandatory to download the hall ticket from the student portal.
- Students must produce their valid college identity card along with the printed hall ticket in the exam hall.

## SECTION 4: TAMIL LANGUAGE INSTRUCTION / தமிழ் வழி வகுப்புகள்
- மாணவர்களுக்கான சந்தேக தீர்வு மற்றும் வழிகாட்டுதல் தமிழ் மற்றும் ஆங்கிலத்தில் பேராசிரியர்களால் வழங்கப்படும்.
- தமிழ் வழி பயிலும் மாணவர்களுக்கு அண்ணா பல்கலைக்கழக பாடத்திட்டத்தின்படி தமிழ் மொழி வினாத்தாள்கள் மற்றும் வழிகாட்டிகள் துறை நூலகத்தில் கிடைக்கின்றன.
"""
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)
    print(f"Generated TXT: {txt_path}")

    # 3. Generate Fee Structure CSV file
    csv_path = target_dir / "fee_structure_and_deadlines.csv"
    csv_rows = [
        ["Fee_Category", "Department_or_Quota", "Annual_Amount_INR", "Due_Date", "Late_Fee_INR", "Payment_Mode"],
        ["Tuition Fee - Govt Quota", "All Engineering Branches", "55000", "August 15, 2026", "500", "Online NetBanking / UPI"],
        ["Tuition Fee - Management Quota", "Computer Science & AI", "125000", "August 15, 2026", "1000", "Online NetBanking / Demand Draft"],
        ["Tuition Fee - Management Quota", "Mechanical & Civil", "85000", "August 15, 2026", "1000", "Online NetBanking / Demand Draft"],
        ["Semester Exam Fee", "All UG Courses", "250 per theory paper", "September 30, 2026", "200", "Student Portal Payment Gateway"],
        ["Hostel Room Rent (AC)", "Boys & Girls Hostel", "60000 per year", "July 31, 2026", "500", "Hostel Office DD / NetBanking"],
        ["Hostel Room Rent (Non-AC)", "Boys & Girls Hostel", "35000 per year", "July 31, 2026", "500", "Hostel Office DD / NetBanking"],
        ["Mess Food Fee", "Hostel Resident Students", "42000 per year", "Payable in two installments (July & Dec)", "250", "Hostel Account Online"],
        ["College Bus Transport Fee", "Within 15 KM radius", "18000 per year", "August 10, 2026", "300", "Transport Section Counter"],
        ["College Bus Transport Fee", "Beyond 15 KM radius", "26000 per year", "August 10, 2026", "300", "Transport Section Counter"],
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)
    print(f"Generated CSV: {csv_path}")

    # 4. Generate Department Directory JSON
    dept_path = target_dir / "department_directory.json"
    departments_data = [
        {
            "department": "Computer Science and Engineering (CSE)",
            "hod_name": "Dr. K. Senthil Kumar, Ph.D.",
            "office_location": "Academic Block A, Third Floor, Room 304",
            "contact_email": "hod.cse@college.edu",
            "phone_extension": "401",
            "labs": ["Artificial Intelligence Lab", "Cloud Computing Lab", "Open Source Software Lab"],
            "total_faculty": 28
        },
        {
            "department": "Electronics and Communication Engineering (ECE)",
            "hod_name": "Dr. M. Revathi, Ph.D.",
            "office_location": "Academic Block B, Second Floor, Room 208",
            "contact_email": "hod.ece@college.edu",
            "phone_extension": "402",
            "labs": ["VLSI Design Lab", "Embedded Systems Lab", "Optical & Microwave Lab"],
            "total_faculty": 24
        },
        {
            "department": "Mechanical Engineering (MECH)",
            "hod_name": "Dr. P. Rajasekaran, Ph.D.",
            "office_location": "Workshop Block C, Ground Floor, Room 102",
            "contact_email": "hod.mech@college.edu",
            "phone_extension": "403",
            "labs": ["CAD/CAM Simulation Center", "Thermal Engineering Lab", "Mechatronics Lab"],
            "total_faculty": 20
        },
        {
            "department": "Office of the Dean of Student Affairs",
            "hod_name": "Prof. A. Vijayalakshmi",
            "office_location": "Administrative Block, First Floor, Room 110",
            "contact_email": "studentaffairs@college.edu",
            "phone_extension": "105",
            "services": ["Scholarships", "Bus Passes", "Railway Concession", "Grievance Redressal"],
            "total_faculty": 6
        }
    ]
    with open(dept_path, "w", encoding="utf-8") as f:
        json.dump(departments_data, f, indent=2, ensure_ascii=False)
    print(f"Generated Department JSON: {dept_path}")

    # 5. Generate Holiday Calendar 2026 JSON
    holidays_path = target_dir / "holiday_calendar_2026.json"
    holidays_data = [
        {
            "event": "Pongal & Tamil Harvest Festival",
            "date": "January 14 to January 17, 2026",
            "type": "Government & College Holiday",
            "tamil_name": "பொங்கல் மற்றும் உழவர் திருநாள் விடுமுறை",
            "description": "College closed for all academic and administrative activities for 4 days."
        },
        {
            "event": "Republic Day",
            "date": "January 26, 2026",
            "type": "National Holiday",
            "tamil_name": "குடியரசு தின விழா",
            "description": "Flag hoisting at 8:30 AM in College Central Ground. Attendance compulsory for NCC/NSS cadets."
        },
        {
            "event": "Annual College Cultural & Tech Symposium (AURA 2026)",
            "date": "March 20 to March 21, 2026",
            "type": "College Fest",
            "tamil_name": "கல்லூரி கலாச்சார மற்றும் தொழில்நுட்ப விழா",
            "description": "Two-day inter-college national technical symposium and cultural event."
        },
        {
            "event": "Tamil New Year / Puthandu",
            "date": "April 14, 2026",
            "type": "State Holiday",
            "tamil_name": "தமிழ் புத்தாண்டு விடுமுறை",
            "description": "Official holiday across all institutions in Tamil Nadu."
        },
        {
            "event": "End-Semester Examinations (Even Semester)",
            "date": "May 4 to May 25, 2026",
            "type": "Academic Examination Schedule",
            "tamil_name": "பருவத் தேர்வுகள் அட்டவணை",
            "description": "Theory examinations conducted in morning and afternoon sessions."
        },
        {
            "event": "Summer Vacation for Students",
            "date": "June 1 to July 5, 2026",
            "type": "Student Vacation",
            "tamil_name": "கோடை விடுமுறை",
            "description": "College reopens for Odd Semester classes on Monday, July 6, 2026."
        }
    ]
    with open(holidays_path, "w", encoding="utf-8") as f:
        json.dump(holidays_data, f, indent=2, ensure_ascii=False)
    print(f"Generated Holiday Calendar JSON: {holidays_path}")

if __name__ == "__main__":
    from config import DOCUMENTS_DIR, SAMPLE_DATA_DIR
    create_sample_documents(DOCUMENTS_DIR)
    create_sample_documents(SAMPLE_DATA_DIR)
