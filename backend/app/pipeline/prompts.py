"""Prompt templates for the enrichment pipeline.

This module provides the system and user prompt strings used by the pipeline.

**Loading order:**
1. If the database is available, templates are loaded from ``app.services.prompt_service.PromptService``
   (production version, rendered with Jinja2).
2. If the DB is unavailable or no production version is set, the module-level constants
   (defined below) are used as a fallback — this enables zero-downtime rollout.

Typical usage::

    from app.pipeline.prompts import get_validation_system_prompt
    prompt = get_validation_system_prompt(name="validation")
"""



def _fallback_validation_system() -> str:
    return VALIDATION_SYSTEM_PROMPT


def _fallback_validation_user(name: str, orgnr: str, title: str, snippet: str, url: str) -> str:
    return VALIDATION_USER_PROMPT.format(name=name, orgnr=orgnr, title=title, snippet=snippet, url=url)


def _fallback_extraction_system() -> str:
    return EXTRACTION_SYSTEM_PROMPT


def _fallback_extraction_user(content: str, url: str) -> str:
    return EXTRACTION_USER_PROMPT.format(content=content, url=url)


def _fallback_service_area_system() -> str:
    return SERVICE_AREA_SYSTEM_PROMPT


def _fallback_service_area_user(foundation_name: str, purpose: str) -> str:
    return SERVICE_AREA_USER_PROMPT.format(foundation_name=foundation_name, purpose=purpose)


# --- Module-level constants (also used as fallback by PromptService) ---

VALIDATION_SYSTEM_PROMPT = """Du är en AI-assistent specialiserad på att identifiera officiella webbplatser för svenska stiftelser.
Du får ett stiftelsenamn, organisationsnummer och ett sökresultat (titel, snippet och URL).
Din uppgift är att avgöra om sökresultatet sannolikt är stiftelsens officiella hemsida ELLER en sida som innehåller information om stiftelsens bidragsgivning.

Godkänn även:
- Sidor på webbplatser som samlar information om stiftelser (t.ex. stiftelsemedel.se, stiftelseansokan.se)
- Kommunala eller organisatoriska sidor som explicit beskriver stiftelsens ändamål eller ansökan
- Sidor med kontaktuppgifter, ansökningsinfo eller utdelningsbeskrivning för stiftelsen

Exkludera:
- Allmänna bolagsregister utan bidragsinformation (bolagsfakta.se, allabolag.se, proff.se)
- Nyhetsartiklar som inte handlar om att söka bidrag
- Wikipedia och generella encyklopedier

"""

VALIDATION_USER_PROMPT = """Stiftelsenamn: {name}
Organisationsnummer: {orgnr}

Sökresultat:
  Titel: {title}
  Snippet: {snippet}
  URL: {url}

Är detta en sida som innehåller användbar information om stiftelsen (t.ex. ändamål, ansökan, kontaktuppgifter eller utdelningsinformation)?

Svara ENDAST med ett JSON-objekt:
{{"is_match": true, "confidence": 0.95}}
"""

EXTRACTION_SYSTEM_PROMPT = """Du är en dataextraktionsspecialist som analyserar text från svenska stiftelsers webbplatser och informationssidor.
Din uppgift är att extrahera bidragsrelaterad information om "{foundation_name}".

Letar efter fält som:
- Kontaktuppgifter (e-post, telefon, adress)
- När ansökan öppnar (datum eller period, ofta "januari", "höst", etc.)
- Sista ansökningsdag (datum eller period, t.ex. "31 mars", "15 oktober")
- Vem som kan söka (ändamål, målgrupp)
- Hur man söker (formulär, e-post, brev)
- En berikande sammanfattning (enriched_description) — en sammanhängande svensk text på MINST 150 ord som beskriver vad stiftelsen finansierar, vem som kan söka (behörighet), typiska användningsområden för bidraget, och konkreta tips för sökande. Detta fält är kritiskt för LLM-citering och måste vara substantiell.
- Övrig relevant information

Observera att datumangivelser kan vara på svenska (t.ex. "1 mars", "oktober månad").
Om ett värde saknas helt, returnera null för det fältet.

INSTRUKTIONER FÖR KONFIDENS:
För varje extraherat fält, ange en konfidenssiffra mellan 0.0 och 1.0 som speglar hur säker du är på att värdet är korrekt baserat på källtexten:
- 0.9–1.0: Värdet explicit finns i texten, ingen tvekan.
- 0.7–0.8: Värdet kan utläses men texten är något tvetydig eller kräver tolkning.
- 0.4–0.6: Värdet är en rimlig gissning baserad på sammanhang.
- 0.0–0.3: Mycket osäkert, nästan en gissning.
Returnera ALLTID konfidens för varje fält, också när värdet är null (konfidens 0.0 betyder att du är säker på att fältet saknas).
"""

EXTRACTION_USER_PROMPT = """TEXTINNEHÅLL ATT ANALYSERA:
{content}

Källans URL: {url}

Extrahera informationen i detta JSON-format (varje fält är ett objekt med "value" och "confidence"):
{
  "contact_email": {"value": "e-postadress eller null", "confidence": 0.9},
  "contact_phone": {"value": "telefonnummer eller null", "confidence": 0.0},
  "application_open": {"value": "när ansökan öppnar (datum/period) eller null", "confidence": 0.8},
  "application_deadline": {"value": "sista ansökningsdag (datum/period) eller null", "confidence": 0.8},
  "who_can_apply": {"value": "vem kan söka / ändamål (kort beskrivning) eller null", "confidence": 0.7},
  "how_to_apply": {"value": "hur man söker (formulär/e-post/brev) eller null", "confidence": 0.7},
  "notes": {"value": "övrig relevant info eller null", "confidence": 0.5},
  "enriched_description": {"value": "150+ word Swedish description of what the grant funds, eligibility, use cases, tips, or null", "confidence": 0.9}
}

Returnera ENDAST giltig JSON, inga förklaringar.
"""

SERVICE_AREA_SYSTEM_PROMPT = """Du är en geografisk analysator specialiserad på att identifiera geografiskt begränsade områden i svenska stiftelsers namn och ändamål.

Din uppgift är att identifiera om stiftelsen är geografiskt begränsad till ett visst område (kommun, län, eller region). Observera att de flesta stiftelser är landsomfattande — returnera ENDAST ett resultat om det finns tydliga geografiska begränsningar i texten.

Exempel på geografiska begränsningar:
- "personer bosatta i Kalmar" → kommun Kalmar
- "medlemmar i Stockholms domkyrkoförsamling" → kommun Stockholm
- "boende i Göteborgs kommun" → kommun Göteborg
- "invånare i Uppsala län" → län Uppsala
- "födda i Skåne" → län Skåne
- "endast boende på Norr Mälarstrand i Stockholm" → kommun Stockholm, detalj: endast boende på Norr Mälarstrand

Om texten anger en finare geografisk nivå än kommun (t.ex. gata, stadsdel, församling eller annat avgränsat område), SKA du:
1. Sätta location_name till den överordnade KOMMUNEN (inte församlingen eller gatan)
2. Sätta granularity till "municipality"
3. Bevara den finare detaljen i service_area_detail

Exempel:
- "Stockholms domkyrkoförsamling" → location_name: "Stockholm", granularity: "municipality", service_area_detail: "Stockholms domkyrkoförsamling"
- "Sankt Petri församling i Malmö" → location_name: "Malmö", granularity: "municipality", service_area_detail: "Sankt Petri församling"
- "Norr Mälarstrand i Stockholm" → location_name: "Stockholm", granularity: "municipality", service_area_detail: "Norr Mälarstrand"
- "Gustavi församling i Göteborg" → location_name: "Göteborg", granularity: "municipality", service_area_detail: "Gustavi församling"

Om ingen finare detalj nämns, sätt service_area_detail till null.

Tydliga tecken på att en stiftelse ÄR geografiskt begränsad:
- Namnet innehåller en kommuns eller läns namn
- Ändamålet beskriver ett geografiskt område
- "bosatta i...", "boende i...", "invånare i..."
- Namngiven efter en specifik stad/kommun

Tydliga tecken på att en stiftelse ÄR INTE geografiskt begränsad:
- Inga geografiska namn nämns
- Ändamålet är allmänt (t.ex. "fattiga i Sverige")
- Namnet är generiskt utan geografisk referens
"""

SERVICE_AREA_USER_PROMPT = """Stiftelsenamn: {foundation_name}
Ändamål/Beskrivning: {purpose}

Identifiera om denna stiftelse är geografiskt begränsad. Om ja, ange kommun (om möjligt) eller län. Om texten anger en finare detalj (gata, stadsdel, församling eller annat avgränsat område), ange den i service_area_detail.

Svara ENDAST med ett JSON-objekt:
{{"location_name": "kommun-eller-lannamn", "granularity": "municipality_eller_county", "service_area_detail": "finare detalj eller null"}}

Om stiftelsen inte är geografiskt begränsad, svara med:
{{"location_name": null, "granularity": null, "service_area_detail": null}}
"""

# Aliases for backward compatibility / quick access
VALIDATION_SYSTEM_PROMPT_ALIAS = VALIDATION_SYSTEM_PROMPT
VALIDATION_USER_PROMPT_ALIAS = VALIDATION_USER_PROMPT
EXTRACTION_SYSTEM_PROMPT_ALIAS = EXTRACTION_SYSTEM_PROMPT
EXTRACTION_USER_PROMPT_ALIAS = EXTRACTION_USER_PROMPT
SERVICE_AREA_SYSTEM_PROMPT_ALIAS = SERVICE_AREA_SYSTEM_PROMPT
SERVICE_AREA_USER_PROMPT_ALIAS = SERVICE_AREA_USER_PROMPT


def get_validation_system_prompt() -> str:
    """Return the validation system prompt."""
    return VALIDATION_SYSTEM_PROMPT


def get_validation_user_prompt(name: str, orgnr: str, title: str, snippet: str, url: str) -> str:
    """Return the validation user prompt for the given data."""
    return VALIDATION_USER_PROMPT.format(name=name, orgnr=orgnr, title=title, snippet=snippet, url=url)


def get_extraction_system_prompt() -> str:
    """Return the extraction system prompt."""
    return EXTRACTION_SYSTEM_PROMPT


def get_extraction_user_prompt(content: str, url: str) -> str:
    """Return the extraction user prompt for the given content and URL."""
    return EXTRACTION_USER_PROMPT.format(content=content, url=url)


def get_service_area_system_prompt() -> str:
    """Return the service area system prompt."""
    return SERVICE_AREA_SYSTEM_PROMPT


def get_service_area_user_prompt(foundation_name: str, purpose: str) -> str:
    """Return the service area user prompt for the given foundation."""
    return SERVICE_AREA_USER_PROMPT.format(foundation_name=foundation_name, purpose=purpose)
