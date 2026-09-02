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
- En berikande sammanfattning (enriched_description) — en sammanhängande svensk text på MINST 150 ord som beskriver vad stiftelsen finansierar, vem som kan söka (behörighet), typiska användningsområden för bidraget, och konkreta tips för sökande. Detta fält är kritiskt för LLM-citering och måste vara substantiellt.
- Övrig relevant information

Observera att datumangivelser kan vara på svenska (t.ex. "1 mars", "oktober månad").
Om ett värde saknas helt, returnera null för det fältet.
"""

EXTRACTION_USER_PROMPT = """TEXTINNEHÅLL ATT ANALYSERA:
{content}

Extrahera informationen i detta JSON-format:
{{
  "contact_email": "e-postadress eller null",
  "contact_phone": "telefonnummer eller null",
  "application_open": "när ansökan öppnar (datum/period) eller null",
  "application_deadline": "sista ansökningsdag (datum/period) eller null",
  "who_can_apply": "vem kan söka / ändamål (kort beskrivning) eller null",
  "how_to_apply": "hur man söker (formulär/e-post/brev) eller null",
  "notes": "övrig relevant info eller null",
  "enriched_description": "150+ word Swedish description of what the grant funds, eligibility, use cases, tips, or null"
}}

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
