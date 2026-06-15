"""
presets.py
----------
Pre-seeded use cases for the two showcase verticals.
These load instantly without an API call, so demos work even without connectivity.
"""

PRESETS = {
    "Real Estate Agent": {
        "role": "Real Estate Agent",
        "industry": "Residential Real Estate",
        "hourly_rate": 65,
        "context": (
            "Independent real estate agent handling buyer and seller clients. "
            "Manages listings, showings, negotiations, contracts, and client relationships. "
            "Works with MLS, CRM, and DocuSign. Spends significant time on client communication, "
            "market research, and administrative paperwork."
        ),
    },
    "API Developer": {
        "role": "API Developer",
        "industry": "Software Development / Fintech",
        "hourly_rate": 120,
        "context": (
            "Backend software engineer building and maintaining REST and GraphQL APIs. "
            "Works in an Agile team, writes documentation, reviews code, writes tests, "
            "responds to incidents, participates in sprint ceremonies, and handles "
            "stakeholder communication about API capabilities and integration timelines."
        ),
    },
    "Loan Officer": {
        "role": "Loan Officer",
        "industry": "Financial Services / Banking",
        "hourly_rate": 85,
        "context": (
            "Residential mortgage loan officer at a community bank or credit union. "
            "Handles the full loan lifecycle: prospecting, application intake, document collection, "
            "underwriting coordination, compliance review, and closing. "
            "Works with Encompass or similar LOS, communicates heavily with borrowers, realtors, "
            "and title companies. Spends significant time chasing documents and explaining loan status."
        ),
    },
    "Nonprofit Program Director": {
        "role": "Nonprofit Program Director",
        "industry": "Nonprofit / Social Services",
        "hourly_rate": 55,
        "context": (
            "Program director at a mid-sized nonprofit managing multiple grant-funded programs. "
            "Responsible for program design, staff supervision, grant reporting, donor communication, "
            "community outreach, outcome measurement, and board presentations. "
            "Works with limited staff and budget; wears many hats including data collection, "
            "writing, and compliance tracking."
        ),
    },
    "Healthcare Operations Manager": {
        "role": "Healthcare Operations Manager",
        "industry": "Healthcare / Hospital Systems",
        "hourly_rate": 90,
        "context": (
            "Operations manager at a mid-sized medical practice or hospital department. "
            "Oversees scheduling, staff coordination, billing workflows, compliance documentation, "
            "vendor contracts, and patient experience reporting. "
            "Works with EHR systems (Epic, Cerner), handles regulatory reporting, "
            "manages credentialing, and interfaces with clinical staff and insurance companies."
        ),
    },
    "Government Program Manager": {
        "role": "Government Program Manager",
        "industry": "Federal / State Government",
        "hourly_rate": 95,
        "context": (
            "Program manager at a federal or state agency overseeing a multi-year, "
            "multi-contractor program. Responsible for acquisition planning, contractor oversight, "
            "status reporting to agency leadership, budget tracking, risk management, "
            "and interagency coordination. Works within FAR/procurement constraints, "
            "produces program documentation, and manages competing stakeholder priorities "
            "across technical, policy, and legal teams."
        ),
    },
}
