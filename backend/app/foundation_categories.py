"""
Foundation Category Definitions and Detailed Classification System
This file contains the detailed breakdown of foundation categories for the Ollama categorization system.
"""

from enum import Enum


class FoundationCategory(Enum):
    """
    Comprehensive foundation category enumeration with detailed definitions
    """

    EDUCATION_RESEARCH = "Utbildning och Forskning"
    SOCIAL_SUPPORT = "Socialt Stöd och Vård"
    CULTURAL_ARTS = "Kulturella Aktiviteter och Konst"
    HEALTHCARE_RESEARCH = "Hälso- och Sjukvård samt Medicinsk Forskning"
    ENVIRONMENTAL_CONSERVATION = "Miljövård och Naturskydd"
    SPORTS_ACTIVITIES = "Idrotts- och Fysiska Aktiviteter"
    RELIGIOUS_ACTIVITIES = "Religiösa Aktiviteter"
    COMMUNITY_DEVELOPMENT = "Samhällsutveckling"
    ECONOMIC_BUSINESS = "Ekonomiskt och Näringslivsstöd"
    SPECIALIZED_FIELDS = "Specialiserade Områden"
    TECHNICAL_QUALITY = "Teknisk Utveckling och Kvalitet"
    AGRICULTURE_FISHERIES = "Jordbruk och Fiske"
    DISABILITY_SUPPORT = "Stöd till Personer med Funktionsnedsättning"
    MARITIME = "Sjöfart och Sjöverksamhet"
    MILITARY_DEFENSE = "Militärt och Försvar"
    HOUSING_REAL_ESTATE = "Boende och Fastighet"
    LEADERSHIP_BUSINESS = "Ledarskap och Affärsutveckling"
    POLAR_RESEARCH = "Polarforskning"
    THEATER_PERFORMANCE = "Teater och Scenkonst"
    JOURNALISM_MEDIA = "Journalistik och Medier"
    ANTHROPOSOPHY_WALDORF = "Antroposofi och Waldorfpedagogik"
    SOCIAL_THERAPY = "Social Terapi och Speciella Behov"
    TECHNICAL_AIDS = "Tekniska Hjälpmedel och Ingenjörsarbete"
    NATURE_CONSERVATION = "Naturskydd och Miljöforskning"
    SOCIAL_ENTERPRISES = "Sociala Företag och Verkstäder"
    IMMIGRATION_INTEGRATION = "Invandring och Integration"


# Detailed category definitions for AI training
CATEGORY_DEFINITIONS = {
    FoundationCategory.EDUCATION_RESEARCH: {
        "keywords": [
            "utbildning",
            "studier",
            "forskning",
            "skola",
            "lärare",
            "student",
            "studie",
            "undervisning",
            "pedagog",
            "förening",
            "universitet",
            "högskola",
        ],
        "description": "Foundations focused on education, research, teaching, academic work, student support, and educational development.",
    },
    FoundationCategory.SOCIAL_SUPPORT: {
        "keywords": [
            "barn",
            "vård",
            "fostran",
            "ungdom",
            "familj",
            "social",
            "hjälp",
            "stöd",
            "behövande",
            "ålderstigna",
            "sjuka",
            "lytta",
            "föräldralösa",
            "fattigvård",
        ],
        "description": "Foundations supporting children, youth, families, elderly, sick or disabled people, and other vulnerable groups.",
    },
    FoundationCategory.CULTURAL_ARTS: {
        "keywords": [
            "kultur",
            "konst",
            "musik",
            "teater",
            "bibliotek",
            "museum",
            "galleri",
            "konstnär",
            "skapande",
            "kulturell",
            "författare",
            "bok",
            "litteratur",
        ],
        "description": "Foundations supporting arts, culture, music, theater, literature, museums, libraries, and creative activities.",
    },
    FoundationCategory.HEALTHCARE_RESEARCH: {
        "keywords": [
            "hälsa",
            "medicinsk",
            "cancer",
            "patient",
            "hjärt",
            "medicin",
            "sjuk",
            "vård",
            "forskning",
            "sjukvård",
            "rehabilitering",
        ],
        "description": "Foundations focused on medical research, healthcare, patient support, and treating various diseases.",
    },
    FoundationCategory.ENVIRONMENTAL_CONSERVATION: {
        "keywords": [
            "miljö",
            "natur",
            "djur",
            "klimat",
            "grönt",
            "skog",
            "vatten",
            "naturvård",
            "kulturvård",
            "bevarande",
            "miljöskydd",
        ],
        "description": "Foundations working on environmental protection, nature conservation, animal welfare, and sustainable development.",
    },
    FoundationCategory.SPORTS_ACTIVITIES: {
        "keywords": [
            "idrott",
            "sport",
            "fotboll",
            "golf",
            "tennis",
            "badminton",
            "boll",
            "motion",
            "olympiska",
            "sportslig",
            "tränare",
        ],
        "description": "Foundations supporting sports, physical activities, athletic training, and promoting physical health.",
    },
    FoundationCategory.RELIGIOUS_ACTIVITIES: {
        "keywords": [
            "religiös",
            "kyrka",
            "mission",
            "gud",
            "bön",
            "präst",
            "kristen",
            "gudstjänst",
            "andlig",
            "kyrkoherde",
            "metodist",
        ],
        "description": "Foundations with religious or spiritual purposes, church activities, missions, and faith-based services.",
    },
    FoundationCategory.COMMUNITY_DEVELOPMENT: {
        "keywords": [
            "förening",
            "samhälle",
            "granne",
            "lokalt",
            "bygd",
            "kommun",
            "församling",
            "hembygd",
            "samverkan",
        ],
        "description": "Foundations working on community development, local issues, neighborhood activities, and regional development.",
    },
    FoundationCategory.ECONOMIC_BUSINESS: {
        "keywords": [
            "ekonomi",
            "näringsliv",
            "företag",
            "bygg",
            "industri",
            "handel",
            "affär",
            "arbetare",
            "fackförening",
        ],
        "description": "Foundations supporting business, economic development, industry, trade, and workers' interests.",
    },
    FoundationCategory.SPECIALIZED_FIELDS: {
        "keywords": [
            "specifikt",
            "särskilt",
            "särart",
            "egendom",
            "förvaltning",
            "äldreboende",
            "fonder",
        ],
        "description": "Foundations with very specific or mixed purposes that don't clearly fit into other categories.",
    },
    FoundationCategory.TECHNICAL_QUALITY: {
        "keywords": [
            "byggstål",
            "kvalitet",
            "kvalitetsutveckling",
            "produktkvalitet",
            "teknisk",
            "ingenjörs",
            "teknik",
        ],
        "description": "Foundations focused on technical development, quality assurance, engineering, and technical standards.",
    },
    FoundationCategory.AGRICULTURE_FISHERIES: {
        "keywords": [
            "jordbruk",
            "fiske",
            "landbruk",
            "biodynamisk",
            "lantbruk",
            "trädgård",
            "fiskare",
            "havsfiske",
        ],
        "description": "Foundations supporting agriculture, farming, gardening, fishing, and related activities.",
    },
    FoundationCategory.DISABILITY_SUPPORT: {
        "keywords": [
            "handikapp",
            "funktionsnedsättning",
            "utvecklingsstörning",
            "psykisk",
            "intellektuell",
            "behov",
            "stöd",
        ],
        "description": "Foundations supporting people with disabilities, mental health issues, or other special needs.",
    },
    FoundationCategory.MARITIME: {
        "keywords": [
            "sjö",
            "sjöman",
            "sjömän",
            "sjömans",
            "hamn",
            "sjöfart",
            "båt",
            "marin",
            "sjöförsvar",
        ],
        "description": "Foundations supporting maritime activities, sailors, naval personnel, and waterfront communities.",
    },
    FoundationCategory.MILITARY_DEFENSE: {
        "keywords": [
            "militär",
            "försvar",
            "soldat",
            "officer",
            "yrkesofficer",
            "totalförsvaret",
            "soldater",
        ],
        "description": "Foundations supporting military personnel, defense, veterans, and related services.",
    },
    FoundationCategory.HOUSING_REAL_ESTATE: {
        "keywords": [
            "bostad",
            "bostäder",
            "hyres",
            "lägenhet",
            "fastighet",
            "förvaltning",
            "hem",
            "boende",
        ],
        "description": "Foundations focused on housing provision, real estate management, and residential support.",
    },
    FoundationCategory.LEADERSHIP_BUSINESS: {
        "keywords": [
            "ledarskap",
            "företagare",
            "nyföretagande",
            "entreprenör",
            "ekonomi",
            "bank",
            "ledarskapsprogram",
        ],
        "description": "Foundations supporting leadership development, entrepreneurship, and business development.",
    },
    FoundationCategory.POLAR_RESEARCH: {
        "keywords": ["polar", "forskning", "arktisk", "antarktisk", "is", "fältarbete"],
        "description": "Foundations focused specifically on polar research and Arctic/Antarctic studies.",
    },
    FoundationCategory.THEATER_PERFORMANCE: {
        "keywords": [
            "teater",
            "scen",
            "föreställning",
            "konserter",
            "artist",
            "uppträdande",
            "kulturinstitution",
        ],
        "description": "Foundations supporting theatrical performances, concerts, and similar performance arts.",
    },
    FoundationCategory.JOURNALISM_MEDIA: {
        "keywords": [
            "journalist",
            "media",
            "tidning",
            "tidskrift",
            "publikation",
            "information",
            "kommunikation",
            "publucist",
        ],
        "description": "Foundations supporting journalism, media, publications, and information dissemination.",
    },
    FoundationCategory.ANTHROPOSOPHY_WALDORF: {
        "keywords": [
            "rudolf steiner",
            "antroposofi",
            "waldorf",
            "frihögskola",
            "läkepedagog",
            "goetheanum",
        ],
        "description": "Foundations based on anthroposophy principles, Waldorf education, and associated activities.",
    },
    FoundationCategory.SOCIAL_THERAPY: {
        "keywords": [
            "läkepedagog",
            "socialterapi",
            "socialterapeutisk",
            "behandling",
            "terapi",
            "verkstad",
            "arbetsmöjlighet",
        ],
        "description": "Foundations providing social therapy, special education, and therapeutic support for people with special needs.",
    },
    FoundationCategory.TECHNICAL_AIDS: {
        "keywords": [
            "tekniska hjälpmedel",
            "hjälpmedel",
            "teknik",
            "hjälp",
            "teknisk hjälp",
            "utvecklingsarbete",
        ],
        "description": "Foundations developing and supporting technical aids for people with disabilities.",
    },
    FoundationCategory.NATURE_CONSERVATION: {
        "keywords": [
            "naturvård",
            "kulturvård",
            "naturreservat",
            "bevarande",
            "miljöforskning",
            "inventering",
            "landskapsvård",
        ],
        "description": "Foundations with specific focus on nature conservation, landscape preservation, and environmental research.",
    },
    FoundationCategory.SOCIAL_ENTERPRISES: {
        "keywords": [
            "verkstad",
            "arbetsplats",
            "skyddad",
            "arbetsplats",
            "verkstäder",
            "inpassning",
            "näringsliv",
        ],
        "description": "Foundations creating workshops and employment opportunities for people with disabilities.",
    },
    FoundationCategory.IMMIGRATION_INTEGRATION: {
        "keywords": [
            "invandring",
            "integration",
            "invandrare",
            "migration",
            "kulturell",
            "förståelse",
            "utrikes",
        ],
        "description": "Foundations supporting immigration research, integration, and cross-cultural understanding.",
    },
}


def get_all_keywords() -> list[str]:
    """Get all keywords from all categories for AI training"""
    all_keywords = []
    for category_info in CATEGORY_DEFINITIONS.values():
        all_keywords.extend(category_info["keywords"])
    return list(set(all_keywords))  # Remove duplicates


def get_category_description(category: FoundationCategory) -> str:
    """Get the description for a specific category"""
    return CATEGORY_DEFINITIONS[category]["description"]


def get_category_keywords(category: FoundationCategory) -> list[str]:
    """Get the keywords for a specific category"""
    return CATEGORY_DEFINITIONS[category]["keywords"]


# Define broader category groups for simplification
BROAD_CATEGORY_GROUPS = {
    "Education & Research": [
        FoundationCategory.EDUCATION_RESEARCH,
        FoundationCategory.POLAR_RESEARCH,
        FoundationCategory.ANTHROPOSOPHY_WALDORF,
    ],
    "Health & Social Care": [
        FoundationCategory.HEALTHCARE_RESEARCH,
        FoundationCategory.SOCIAL_SUPPORT,
        FoundationCategory.DISABILITY_SUPPORT,
        FoundationCategory.SOCIAL_THERAPY,
    ],
    "Culture & Arts": [
        FoundationCategory.CULTURAL_ARTS,
        FoundationCategory.THEATER_PERFORMANCE,
        FoundationCategory.JOURNALISM_MEDIA,
    ],
    "Environment & Nature": [
        FoundationCategory.ENVIRONMENTAL_CONSERVATION,
        FoundationCategory.AGRICULTURE_FISHERIES,
        FoundationCategory.NATURE_CONSERVATION,
    ],
    "Community & Society": [
        FoundationCategory.COMMUNITY_DEVELOPMENT,
        FoundationCategory.MILITARY_DEFENSE,
        FoundationCategory.MARITIME,
        FoundationCategory.IMMIGRATION_INTEGRATION,
    ],
    "Economy & Development": [
        FoundationCategory.ECONOMIC_BUSINESS,
        FoundationCategory.TECHNICAL_QUALITY,
        FoundationCategory.TECHNICAL_AIDS,
        FoundationCategory.SOCIAL_ENTERPRISES,
        FoundationCategory.LEADERSHIP_BUSINESS,
        FoundationCategory.HOUSING_REAL_ESTATE,
    ],
    "Specialized Fields": [FoundationCategory.SPECIALIZED_FIELDS],
}
