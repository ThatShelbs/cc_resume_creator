"""
A fictional, fuller persona for demos, template thumbnails, and screenshots.
Nothing here describes a real person or employer. The paragraph layout is the
one generate_resume.py parses (see make_examples.py for the minimal version).
"""

PERSONA = {
    "name": "Jordan Rivera",
    "email": "jordan.rivera@example.com",
    "phone": "(555) 010-0199",
    "location": "Denver, CO",
    "linkedin": "linkedin.com/in/jordan-rivera-example",
}

PROFILE = [
    ("Applicant info", "Normal"),
    (PERSONA["name"], "List Paragraph"),
    (PERSONA["email"], "List Paragraph"),
    (PERSONA["phone"], "List Paragraph"),
    (PERSONA["location"], "List Paragraph"),
    (PERSONA["linkedin"], "List Paragraph"),
    ("Leadership", "Normal"),
    ("6 years managing analytics teams, currently 7 direct reports", "List Paragraph"),
    ("Hired and developed analysts into senior and lead roles", "List Paragraph"),
    ("Partner with marketing, finance, and product leaders on measurement strategy", "List Paragraph"),
    ("Projects", "Normal"),
    ("Northwind Traders: built a customer churn model that cut churn 12% in one year.", "List Paragraph"),
    ("Northwind Traders: launched a marketing mix model that reallocated $4M of annual spend.", "List Paragraph"),
    ("Northwind Traders: designed an experimentation program running 40+ A/B tests per year.", "List Paragraph"),
    ("Contoso Retail: automated weekly sales reporting, saving 10 hours per week.", "List Paragraph"),
    ("Contoso Retail: built store-level demand forecasts that reduced stockouts 18%.", "List Paragraph"),
    ("Fabrikam Health: built patient segmentation used by 3 regional outreach teams.", "List Paragraph"),
    ("Software/Tools", "Normal"),
    ("Python", "List Paragraph"),
    ("SQL", "List Paragraph"),
    ("Tableau", "List Paragraph"),
    ("dbt", "List Paragraph"),
    ("Snowflake", "List Paragraph"),
    ("Git", "List Paragraph"),
    ("Skills", "Normal"),
    ("Forecasting", "List Paragraph"),
    ("A/B testing & experimentation", "List Paragraph"),
    ("Marketing mix modeling", "List Paragraph"),
    ("Customer segmentation", "List Paragraph"),
    ("Churn modeling", "List Paragraph"),
    ("Team Leadership", "List Paragraph"),
    ("Stakeholder Management", "List Paragraph"),
    ("Data visualization", "List Paragraph"),
    ("Recent Awards", "Normal"),
    ("Northwind Traders Analytics Impact Award (2024)", "List Paragraph"),
]

RESUME = [
    ("Summary", "Normal"),
    ("Analytics leader with 11 years of experience turning customer and marketing data into decisions.", "Normal"),
    ("Education", "Normal"),
    ("State University | Boulder, CO\t2010 - 2014", "Normal"),
    ("B.S. Statistics", "Normal"),
    ("Experience", "Normal"),
    ("Northwind Traders | Denver, CO\t2019 - Present", "Normal"),
    ("Director, Analytics", "Normal"),
    ("Built a customer churn model that cut churn 12% in one year.", "List Paragraph"),
    ("Launched a marketing mix model that reallocated $4M of annual spend toward higher-return channels.", "List Paragraph"),
    ("Designed an experimentation program running 40+ A/B tests per year across web and email.", "List Paragraph"),
    ("Lead a team of 7 analysts and data scientists.", "List Paragraph"),
    ("Contoso Retail | Denver, CO\t2016 - 2019", "Normal"),
    ("Senior Data Analyst", "Normal"),
    ("Automated weekly sales reporting, saving 10 hours per week.", "List Paragraph"),
    ("Built store-level demand forecasts that reduced stockouts 18%.", "List Paragraph"),
    ("Fabrikam Health | Aurora, CO\t2014 - 2016", "Normal"),
    ("Data Analyst", "Normal"),
    ("Built patient segmentation used by 3 regional outreach teams.", "List Paragraph"),
    ("Created Tableau dashboards for program performance.", "List Paragraph"),
    ("Skills", "Normal"),
    ("Python, SQL, Tableau, dbt, Snowflake, Forecasting, Experimentation", "Normal"),
]

FACT_BANK = """\
# Demo fact bank for the fictional persona in examples/demo_data.py.
facts:
- {id: F001, employer: Northwind Traders, kind: accomplishment, text: Built a customer churn model that cut churn 12% in one year., metrics: ["12%"], tags: [churn modeling, retention, python]}
- {id: F002, employer: Northwind Traders, kind: accomplishment, text: Launched a marketing mix model that reallocated $4M of annual spend toward higher-return channels., metrics: ["$4M"], tags: [marketing mix modeling, marketing measurement]}
- {id: F003, employer: Northwind Traders, kind: project, text: Designed an experimentation program running 40+ A/B tests per year across web and email., metrics: ["40+"], tags: [a/b testing, experimentation]}
- {id: F004, employer: Northwind Traders, kind: responsibility, text: Lead a team of 7 analysts and data scientists., metrics: ["7"], tags: [team leadership]}
- {id: F005, employer: Contoso Retail, kind: accomplishment, text: Automated weekly sales reporting, saving 10 hours per week., metrics: ["10 hours"], tags: [automation, reporting, sql]}
- {id: F006, employer: Contoso Retail, kind: accomplishment, text: Built store-level demand forecasts that reduced stockouts 18%., metrics: ["18%"], tags: [forecasting]}
- {id: F007, employer: Fabrikam Health, kind: accomplishment, text: Built patient segmentation used by 3 regional outreach teams., metrics: ["3"], tags: [customer segmentation]}
- {id: F008, employer: Fabrikam Health, kind: project, text: Created Tableau dashboards for program performance., metrics: [], tags: [tableau, data visualization]}
- {id: F009, employer: general, kind: tool, text: "Python, SQL, Tableau, dbt, Snowflake, and Git.", metrics: [], tags: [python, sql, tableau, dbt, snowflake]}
- {id: F010, employer: general, kind: skill, text: Partner with marketing, finance, and product leaders on measurement strategy., metrics: [], tags: [stakeholder management]}
- {id: F011, employer: general, kind: award, text: Northwind Traders Analytics Impact Award (2024)., metrics: ["2024"], tags: [award]}
"""

JOBS = {
    "lumen": {
        "company": "Lumen Outdoor Co.",
        "role": "Head of Marketing Analytics",
        "status": "interviewing",
        "text": """Head of Marketing Analytics
Lumen Outdoor Co. | Denver, CO (Hybrid)

About Lumen
Lumen Outdoor Co. makes gear for people who spend their weekends outside. We're a fast-growing direct-to-consumer brand.

The role
You'll build and lead our marketing analytics function: marketing mix modeling, experimentation, and customer analytics that guide
a $30M annual marketing budget.

What you'll do
- Own marketing measurement: MMM, incrementality testing, and A/B testing.
- Build churn and retention models for our subscription program.
- Lead and grow a team of analysts.
- Partner with marketing, finance, and product leadership.

What you bring
- 8+ years in analytics, 3+ leading teams.
- Strong Python and SQL; experience with dbt and Snowflake is a plus.
- Experience with forecasting and customer segmentation.
- Clear communication and stakeholder management.
""",
    },
    "tailspin": {
        "company": "Tailspin Toys",
        "role": "Director, Customer Insights",
        "status": "applied",
        "text": """Director, Customer Insights (Tailspin Toys)

Tailspin Toys is looking for a Director of Customer Insights to lead segmentation, retention, and forecasting work across our
retail and e-commerce channels.

Responsibilities: lead a team of 5 analysts; build customer segmentation and churn models; own demand forecasting with the supply
chain team; present insights to executives; champion experimentation.

Qualifications: 10 years of analytics experience; Python, SQL, Tableau; forecasting; team leadership; stakeholder management.
""",
    },
    "wingtip": {
        "company": "Wingtip Air",
        "role": "Senior Manager, Experimentation",
        "status": "draft",
        "text": """Senior Manager, Experimentation
Company: Wingtip Air

Help Wingtip Air build a culture of testing. You'll run our A/B testing platform, set experimentation standards, and coach
product teams on measurement. Requirements: experimentation at scale, Python, SQL, clear writing, stakeholder management.
""",
    },
}

# A hand-written, truthful (every claim is in the persona above) tailored
# result, used to render the template thumbnails without a Claude call.
DEMO_RESULT = {
    "schema": 1,
    "generated_at": "2026-09-28T10:30:00",
    "model": "sonnet",
    "effort": "medium",
    "template": "classic",
    "inputs": {"Profile": "in_profile.docx", "Prior resume": "in_resume_Jordan-Rivera.docx", "Job posting": "job.txt"},
    "contact": {
        "first_name": "Jordan",
        "last_name": "Rivera",
        "email": PERSONA["email"],
        "phone": PERSONA["phone"],
        "location": PERSONA["location"],
        "linkedin": PERSONA["linkedin"],
    },
    "summary": (
        "Analytics leader with 11 years of experience in marketing measurement, experimentation, and customer analytics. "
        "Built the marketing mix model that reallocated $4M of annual spend and an experimentation program running 40+ tests a year, "
        "and currently leads a team of 7 analysts and data scientists."
    ),
    "education": [{"institution": "State University", "location": "Boulder, CO", "dates": "2010 - 2014", "degree": "B.S. Statistics"}],
    "experience": [
        {
            "company": "Northwind Traders",
            "location": "Denver, CO",
            "dates": "2019 - Present",
            "title": "Director, Analytics",
            "bullets": [
                {"text": "Launched a marketing mix model that reallocated $4M of annual spend toward higher-return channels.", "ids": ["F002"]},
                {"text": "Designed an experimentation program running 40+ A/B tests per year across web and email.", "ids": ["F003"]},
                {"text": "Built a customer churn model that cut churn 12% in one year.", "ids": ["F001"]},
                {"text": "Lead a team of 7 analysts and data scientists, partnering with marketing, finance, and product leaders.", "ids": ["F004", "F010"]},
            ],
        },
        {
            "company": "Contoso Retail",
            "location": "Denver, CO",
            "dates": "2016 - 2019",
            "title": "Senior Data Analyst",
            "bullets": [
                {"text": "Built store-level demand forecasts that reduced stockouts 18%.", "ids": ["F006"]},
                {"text": "Automated weekly sales reporting in SQL, saving 10 hours per week.", "ids": ["F005"]},
            ],
        },
        {
            "company": "Fabrikam Health",
            "location": "Aurora, CO",
            "dates": "2014 - 2016",
            "title": "Data Analyst",
            "bullets": [
                {"text": "Built patient segmentation used by 3 regional outreach teams.", "ids": ["F007"]},
                {"text": "Created Tableau dashboards for program performance.", "ids": ["F008"]},
            ],
        },
    ],
    "skills": [
        "A/B Testing", "Churn Modeling", "Customer Segmentation", "dbt", "Forecasting", "Marketing Mix Modeling",
        "Python", "Snowflake", "SQL", "Stakeholder Management", "Tableau", "Team Leadership",
    ],
    "cover_letter": None,
    "coverage": {"covered": [], "missing": []},
    "page_count": None,
    "draft": "(demo content written by hand; no Claude call)",
}
