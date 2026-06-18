"""
presets.py
----------
Pre-seeded use cases for the two showcase verticals.
These load instantly without an API call, so demos work even without connectivity.

Each entry now includes `industry_group` to anchor it in the industry-first UI flow.
"""

PRESETS = {
    "Real Estate Agent": {
        "role": "Real Estate Agent",
        "industry": "Residential Real Estate",
        "industry_group": "Finance, Insurance & Real Estate",
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
        "industry_group": "Technology & IT",
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
        "industry_group": "Finance, Insurance & Real Estate",
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
        "industry_group": "Social Services & Community",
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
        "industry_group": "Healthcare & Medical",
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
        "industry_group": "Government & Public Safety",
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
    "Scrum Master": {
        "role": "Scrum Master",
        "industry": "Software Development",
        "industry_group": "Technology & IT",
        "hourly_rate": 100,
        "context": (
            "Scrum Master on a cross-functional software delivery team of 6–10 engineers. "
            "Facilitates sprint ceremonies (planning, standups, reviews, retrospectives), "
            "removes impediments, tracks velocity and burndown, manages the team's Jira board, "
            "coaches team members on Agile practices, and interfaces with product owners and "
            "engineering managers on delivery forecasts and process improvement."
        ),
    },
    "Technical Product Owner": {
        "role": "Technical Product Owner",
        "industry": "Software Development",
        "industry_group": "Technology & IT",
        "hourly_rate": 110,
        "context": (
            "Technical Product Owner bridging engineering and business stakeholders for a "
            "SaaS platform. Owns and prioritizes the product backlog, writes and refines user "
            "stories and acceptance criteria, participates in sprint planning and reviews, "
            "conducts stakeholder demos, tracks feature release readiness, and manages "
            "competing priorities across engineering, design, and go-to-market teams. "
            "Works daily in Jira, Confluence, and Figma."
        ),
    },
    "Product Manager": {
        "role": "Product Manager",
        "industry": "Software Development / SaaS",
        "industry_group": "Technology & IT",
        "hourly_rate": 115,
        "context": (
            "Product Manager at a B2B SaaS company responsible for a core product area. "
            "Conducts customer discovery, defines roadmap and OKRs, writes PRDs, "
            "coordinates across engineering, design, sales, and marketing, tracks KPIs, "
            "manages feature launches, and synthesizes customer feedback and usage data "
            "into prioritization decisions. Spends significant time in meetings, Slack, "
            "and documentation tools."
        ),
    },
    "Technical Program Manager": {
        "role": "Technical Program Manager",
        "industry": "Software Development / Technology",
        "industry_group": "Technology & IT",
        "hourly_rate": 130,
        "context": (
            "Technical Program Manager (TPM) at a mid-to-large technology company, "
            "driving delivery of a complex multi-team software initiative. Owns the "
            "cross-team program plan, tracks dependencies and critical path, runs "
            "weekly program syncs, escalates blockers to engineering leadership, "
            "manages risk and scope, produces executive status reports, and coordinates "
            "between engineering, infrastructure, security, and product teams. "
            "Works heavily in Jira, Confluence, and slide decks. Deep enough technically "
            "to challenge engineering estimates and flag architectural risks."
        ),
    },
}
