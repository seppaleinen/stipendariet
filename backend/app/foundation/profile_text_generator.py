"""
Profile Text Generator

Converts structured profile selections to descriptive Swedish text for vector embedding.
This text is used to match profiles against foundation purposes using semantic search.
"""
from app.db import schemas

# Swedish descriptions for life situations
LIFE_SITUATION_DESCRIPTIONS = {
    "low_income": "Jag har låg inkomst och ekonomiska svårigheter",
    "single_parent": "Jag är ensamstående förälder",
    "widow": "Jag är änka eller änkling",
    "pensioner": "Jag är pensionär",
    "student": "Jag är student eller studerande",
    "youth": "Jag är ung (under 30 år)",
    "unemployed": "Jag är arbetslös eller arbetssökande",
}

# Swedish descriptions for health conditions
HEALTH_CONDITION_DESCRIPTIONS = {
    "mobility": "Jag har nedsatt rörelseförmåga eller rörelsehinder",
    "vision_hearing": "Jag har nedsatt syn eller hörsel",
    "mental_health": "Jag har psykisk ohälsa eller psykiska besvär",
    "allergy": "Jag har allergier eller överkänslighet",
    "diabetes": "Jag har diabetes",
    "cancer": "Jag har eller har haft cancer",
    "chronic_illness": "Jag har en kronisk sjukdom",
}

# Swedish descriptions for occupations/backgrounds
OCCUPATION_DESCRIPTIONS = {
    "hotel_restaurant": "Jag arbetar eller har arbetat inom hotell- och restaurangbranschen",
    "retail": "Jag arbetar eller har arbetat inom detaljhandeln",
    "maritime": "Jag arbetar eller har arbetat inom sjöfart eller fiske",
    "crafts": "Jag arbetar eller har arbetat som hantverkare",
    "healthcare": "Jag arbetar eller har arbetat inom vård och omsorg",
    "agriculture": "Jag arbetar eller har arbetat inom jordbruk eller skogsbruk",
    "arts": "Jag arbetar eller har arbetat inom konst och kultur",
    "journalism": "Jag arbetar eller har arbetat som journalist eller skribent",
}

# Swedish descriptions for support purposes
SUPPORT_PURPOSE_DESCRIPTIONS = {
    "education": "utbildning, studier eller fortbildning",
    "financial_aid": "ekonomiskt stöd eller bidrag till livsomkostnader",
    "health_care": "vård, behandling eller rehabilitering",
    "projects": "projekt, verksamhet eller evenemang",
    "research": "forskning eller vetenskapligt arbete",
    "travel": "resor eller semester",
    "equipment": "utrustning, hjälpmedel eller tekniska lösningar",
}


def generate_profile_text(profile: schemas.Profile, include_geography: bool = False) -> str:
    """
    Convert structured profile selections to Swedish text for vector embedding.

    Args:
        profile: The user's profile with structured selections
        include_geography: Whether to include geographic info in the text (for soft matching)

    Returns:
        Descriptive Swedish text suitable for embedding
    """
    parts = []

    # Section 1: Geography (optional - for soft matching mode)
    if include_geography and profile.county_code:
        # This could be expanded to include actual county/municipality names
        parts.append("Jag bor i Sverige")

    # Section 2: Life situations
    if profile.life_situations:
        for situation in profile.life_situations:
            if situation in LIFE_SITUATION_DESCRIPTIONS:
                parts.append(LIFE_SITUATION_DESCRIPTIONS[situation])

    # Section 3: Health conditions
    if profile.health_conditions:
        for condition in profile.health_conditions:
            if condition in HEALTH_CONDITION_DESCRIPTIONS:
                parts.append(HEALTH_CONDITION_DESCRIPTIONS[condition])

    # Add freetext health details if provided
    if profile.health_details:
        parts.append(f"Jag har följande hälsotillstånd: {profile.health_details}")

    # Section 4: Occupations/backgrounds
    if profile.occupations:
        for occupation in profile.occupations:
            if occupation in OCCUPATION_DESCRIPTIONS:
                parts.append(OCCUPATION_DESCRIPTIONS[occupation])

    # Section 5: Support purposes
    if profile.support_purposes:
        support_parts = []
        for purpose in profile.support_purposes:
            if purpose in SUPPORT_PURPOSE_DESCRIPTIONS:
                support_parts.append(SUPPORT_PURPOSE_DESCRIPTIONS[purpose])
        if support_parts:
            parts.append(f"Jag söker stöd för {', '.join(support_parts)}")

    return ". ".join(parts) + "." if parts else ""


def get_profile_summary(profile: schemas.Profile) -> dict:
    """
    Get a summary of the profile for display purposes.

    Returns a dict with human-readable summaries of each section.
    """
    summary = {
        "geography": None,
        "life_situations": [],
        "health": [],
        "occupations": [],
        "support_purposes": [],
    }

    if profile.county_code:
        summary["geography"] = f"Län: {profile.county_code}"
        if profile.municipality_code:
            summary["geography"] += f", Kommun: {profile.municipality_code}"

    if profile.life_situations:
        summary["life_situations"] = [
            LIFE_SITUATION_DESCRIPTIONS.get(s, s)
            for s in profile.life_situations
        ]

    if profile.health_conditions:
        summary["health"] = [
            HEALTH_CONDITION_DESCRIPTIONS.get(c, c)
            for c in profile.health_conditions
        ]
        if profile.health_details:
            summary["health"].append(profile.health_details)

    if profile.occupations:
        summary["occupations"] = [
            OCCUPATION_DESCRIPTIONS.get(o, o)
            for o in profile.occupations
        ]

    if profile.support_purposes:
        summary["support_purposes"] = [
            SUPPORT_PURPOSE_DESCRIPTIONS.get(p, p)
            for p in profile.support_purposes
        ]

    return summary
