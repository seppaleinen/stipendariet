"""PromptService — manages versioned Jinja2 prompt templates stored in the database.

Provides methods to:
- Load and render the production prompt by name
- Create new prompt versions (semver)
- Set the production version for A/B testing and rollback
- Retrieve per-version metrics (avg_confidence, field_completeness, runs_count)

Falls back to internal module constants if the DB is unavailable, enabling
zero-downtime rollout. The same constants are also exported from
``app.pipeline.prompts`` for direct use.
"""

from contextlib import contextmanager

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from sqlalchemy import select

from app.db.database import get_db
from app.db.models.enrichment_prompts import EnrichmentPrompt

_jinja_env = None


def _get_jinja_env():
    """Lazily create the Jinja2 environment pointing at the prompts/ directory."""
    global _jinja_env
    if _jinja_env is not None:
        return _jinja_env
    _jinja_env = Environment(
        loader=FileSystemLoader("backend/app/pipeline/prompts"),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    return _jinja_env


# --- Internal fallback constants (kept in sync with app.pipeline.prompts) ---

_VALIDATION_SYSTEM_PROMPT = """Du är en AI-assistent specialiserad på att identifiera officiella webbplatser för svenska stiftelser.
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

_VALIDATION_USER_PROMPT = """Stiftelsenamn: {name}
Organisationsnummer: {orgnr}

Sökresultat:
  Titel: {title}
  Snippet: {snippet}
  URL: {url}

Är detta en sida som innehåller användbar information om stiftelsen (t.ex. ändamål, ansökan, kontaktuppgifter eller utdelningsinformation)?

Svara ENDAST med ett JSON-objekt:
{"is_match": true, "confidence": 0.95}
"""

_EXTRACTION_SYSTEM_PROMPT = """Du är en dataextraktionsspecialist som analyserar text från svenska stiftelsers webbplatser och informationssidor.
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

_EXTRACTION_USER_PROMPT = """TEXTINNEHÅLL ATT ANALYSERA:
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

_SERVICE_AREA_SYSTEM_PROMPT = """Du är en geografisk analysator specialiserad på att identifiera geografiskt begränsade områden i svenska stiftelsers namn och ändamål.

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

_SERVICE_AREA_USER_PROMPT = """Stiftelsenamn: {foundation_name}
Ändamål/Beskrivning: {purpose}

Identifiera om denna stiftelse är geografiskt begränsad. Om ja, ange kommun (om möjligt) eller län. Om texten anger en finare detalj (gata, stadsdel, församling eller annat avgränsat område), ange den i service_area_detail.

Svara ENDAST med ett JSON-objekt:
{"location_name": "kommun-eller-lannamn", "granularity": "municipality_eller_county", "service_area_detail": "finare detalj eller null"}

Om stiftelsen inte är geografiskt begränsad, svara med:
{"location_name": null, "granularity": null, "service_area_detail": null}
"""


class PromptService:
    """Service for managing versioned Jinja2 prompt templates."""

    def _get_session(self):
        """Return a DB session via get_db()."""
        gen = get_db()
        return next(gen)

    def get_production_prompt(self, name: str) -> str | None:
        """Load the production template for the given prompt name and render it.

        Returns the rendered template string, or None if no production version
        exists.
        """
        session = self._get_session()
        try:
            stmt = (
                select(EnrichmentPrompt)
                .where(EnrichmentPrompt.name == name)
                .where(EnrichmentPrompt.is_production == True)
            )
            row = session.execute(stmt).scalar_one_or_none()
        finally:
            session.close()

        if row is None:
            return None

        try:
            template = _get_jinja_env().from_string(row.template)
            # Render with empty defaults; caller should provide specific vars
            return template.render()
        except Exception:
            # If rendering fails, fall back to the raw template text
            return row.template

    def create_prompt_version(
        self, name: str, version: str, template: str, variables: dict | None = None
    ) -> int:
        """Create a new prompt version.

        Returns the ID of the newly created row.
        """
        import json as _json

        session = self._get_session()
        try:
            # Check if (name, version) already exists
            stmt = select(EnrichmentPrompt).where(
                EnrichmentPrompt.name == name, EnrichmentPrompt.version == version
            )
            existing = session.execute(stmt).scalar_one_or_none()
            if existing is not None:
                raise ValueError(f"Prompt version ({name}, {version}) already exists.")

            row = EnrichmentPrompt(
                name=name,
                version=version,
                template=template,
                variables=(_json.dumps(variables) if variables else None),
                is_production=False,
                metrics=_json.dumps({"avg_confidence": 0.0, "field_completeness": 0.0, "runs_count": 0}),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id
        finally:
            session.close()

    def set_production_version(self, name: str, version: str) -> None:
        """Set a specific version as the production version.

        Sets is_production=True for the requested version and False for all
        other versions of the same prompt name.
        """
        session = self._get_session()
        try:
            # Reset all versions of this name to non-production
            session.execute(
                EnrichmentPrompt.__table__.update()
                .where(EnrichmentPrompt.name == name)
                .values(is_production=False)
            )

            # Set the requested version to production
            session.execute(
                EnrichmentPrompt.__table__.update()
                .where(EnrichmentPrompt.name == name)
                .where(EnrichmentPrompt.version == version)
                .values(is_production=True)
            )
            session.commit()
        finally:
            session.close()

    def get_prompt_metrics(self, name: str) -> dict:
        """Return metrics for all versions of the given prompt name.

        Returns a dict keyed by version string, each with
        {avg_confidence, field_completeness, runs_count}.
        """
        session = self._get_session()
        try:
            stmt = select(EnrichmentPrompt).where(EnrichmentPrompt.name == name)
            rows = session.execute(stmt).scalars().all()
        finally:
            session.close()

        metrics_by_version = {}
        for row in rows:
            vars_dict = {}
            if row.variables:
                try:
                    vars_dict = row.variables if isinstance(row.variables, dict) else {}
                except Exception:
                    vars_dict = {}

            metrics_by_version[row.version] = {
                "avg_confidence": row.metrics.get("avg_confidence", 0.0) if row.metrics else 0.0,
                "field_completeness": row.metrics.get("field_completeness", 0.0) if row.metrics else 0.0,
                "runs_count": row.metrics.get("runs_count", 0) if row.metrics else 0,
            }

        return metrics_by_version

    def get_production_version(self, name: str) -> str | None:
        """Return the version string currently marked as production, or None."""
        session = self._get_session()
        try:
            stmt = (
                select(EnrichmentPrompt.version)
                .where(EnrichmentPrompt.name == name)
                .where(EnrichmentPrompt.is_production == True)
            )
            row = session.execute(stmt).scalar_one_or_none()
        finally:
            session.close()
        return row

    def increment_runs(self, name: str, version: str, avg_confidence: float | None = None, field_completeness: float | None = None) -> None:
        """Increment the runs_count and optionally update confidence/completeness metrics."""

        session = self._get_session()
        try:
            stmt = (
                select(EnrichmentPrompt)
                .where(EnrichmentPrompt.name == name)
                .where(EnrichmentPrompt.version == version)
            )
            row = session.execute(stmt).scalar_one_or_none()

            if row is None:
                return

            current_runs = (row.metrics or {}).get("runs_count", 0) or 0
            new_runs = current_runs + 1

            # Compute running averages
            current_avg_conf = (row.metrics or {}).get("avg_confidence", 0.0) or 0.0
            current_avg_fe = (row.metrics or {}).get("field_completeness", 0.0) or 0.0

            if avg_confidence is not None:
                new_avg_conf = (current_avg_conf * current_runs + avg_confidence) / new_runs
            else:
                new_avg_conf = current_avg_conf

            if field_completeness is not None:
                new_avg_fe = (current_avg_fe * current_runs + field_completeness) / new_runs
            else:
                new_avg_fe = current_avg_fe

            row.metrics = {
                "avg_confidence": new_avg_conf,
                "field_completeness": new_avg_fe,
                "runs_count": new_runs,
            }
            session.commit()
        finally:
            session.close()
