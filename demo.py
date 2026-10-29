"""Fictional presentation fixtures; not jobs, search results, or AI output."""

from copy import deepcopy
from datetime import datetime


def demo_results() -> dict:
    date = datetime.now().astimezone().date().isoformat()
    example = {
        "title": "Workshop helper — fictional example",
        "employer": "Example Learning Studio (fictional)",
        "location": "Example location in South Bend",
        "work_arrangement": "in_person",
        "pay": "$13/hour — invented for this demonstration",
        "schedule": "Example schedule: 8 hours per week in summer",
        "minimum_age": 16,
        "why_fit": ["The fictional duties involve helping with beginner coding activities.",
                    "This illustrates how an explanation could connect a job's duties to an interest in coding."],
        "requirements": ["Example requirement: age 16 or older", "Example requirement: familiarity with basic coding"],
        "uncertainties": ["This employer and opening are fictional; there is no application."],
        "posted_date": None,
        "checked_date": date,
        "listing_url": "",
        "application_url": None,
        "match_label": "Possible match",
        "evidence": [],
    }
    uncertain = deepcopy(example)
    uncertain.update({
        "title": "Cafe team member — fictional example",
        "employer": "Example Neighborhood Cafe (fictional)",
        "location": "Example location in Mishawaka",
        "pay": "Not stated",
        "schedule": "Weekend shifts; exact hours not stated",
        "minimum_age": None,
        "why_fit": ["Example duties involving food service could connect to an interest in cooking."],
        "requirements": ["Not stated"],
        "uncertainties": ["What is the minimum age for this specific position?", "What are the pay and required shift times?", "Can the worksite be reached within your travel limit?"],
        "match_label": "Needs confirmation",
    })
    return {
        "mode": "demo", "search_date": date,
        "summary": "Fictional example results for a 16-year-old interested in coding and cooking. No search or AI call was made, and these are not real openings.",
        "assumptions": ["This example uses a made-up profile; it is not a search using the form you filled out."],
        "best_matches": [example], "needs_confirmation": [uncertain],
        "leads": [],
        "next_steps": ["Try the form to make a search plan using your own interests and location.",
                       "To use live AI search, follow the API key setup steps in README.md.",
                       "For live results, read the employer's original posting before making a decision."],
        "search_phrases": ["coding summer jobs South Bend", "cooking part time jobs Mishawaka",
                           'jobs "minimum age" "16" South Bend', '"paid youth" jobs South Bend',
                           '"no experience" summer jobs Mishawaka'],
        "limitations": ["All employers, duties, pay, requirements, and locations in these example cards are fictional.",
                        "Example mode does not use an AI model, verify sources, or connect to an employer."],
        "work_rules": [], "sources": [], "excluded_count": 0,
    }
