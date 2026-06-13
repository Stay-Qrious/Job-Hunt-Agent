PORTAL_URL = "https://www.naukri.com"

# RE-TUNED PROFILE SEARCH ENGINE TARGET VECTOR
NAUKRI_KEYWORDS = [
    "SAP CPI Developer",
    "SAP Integration Suite Specialist",
    "Cloud Platform Integration Developer",
    "Backend Engineer Node.js"
]

BRAND_KEYWORDS = [
    "Amazon", "Flipkart", "Walmart", "Deloitte", "TCS", "Infosys", "Cognizant"
]

BLOCKLIST_COMPANIES = ["accenture", "fake consultancy"]

PROFILE_ANSWERS = {
    "email": "your_personal_email_address@gmail.com",
    "notice_period": "Immediate",
    "expected_ctc": "Negotiable",
    # PROFILE BOUND EXPERIENCE: This blocks the engine from applying to senior/lead 6+ year job listings
    "experience": "2", 
    "skills": "SAP CPI, Integration iFlows, Groovy Scripting, Node.js Backend Microservices"
}