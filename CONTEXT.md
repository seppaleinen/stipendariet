# StipendieAssistenten

Helps individuals in Sweden find stipends and grants (stiftelser) whose purpose matches their personal situation. Users describe themselves once; the system finds and ranks foundations whose purposes are similar.

## Language

### People & things

**User**:
A private individual seeking stipends. Not to be confused with admins, who operate the enrichment pipeline.
_Avoid_: Member, account

**Foundation**:
An organization that grants money for specific purposes.
_Avoid_: Stipend (that is the money itself), grant-maker, fund

**Registered address**:
Where a Foundation is domiciled according to the source dataset. Administrative fact only — says nothing about who may benefit.

**Service area**:
The geography whose residents a Foundation may benefit — its eligibility footprint, at county, municipality, or finer level. Derived from the dataset codes or from mentions in the Foundation's own name and purpose; the two may disagree, and Service area wins because it governs eligibility.
_Avoid_: Location (ambiguous between Registered address and Service area)

### The user's description

**Profile**:
A user's saved self-representation used to find Foundations. A user has one or more Profiles; exactly one is active at a time.

**Structured selections**:
The checkbox-and-dropdown part of a Profile: life situations, health conditions and details, occupations, support purposes, county and municipality.

**Self-description**:
The user's situation written in their own words, saved as part of a Profile.
_Avoid_: Freetext, freetext field, notes (notes are an admin concept on Foundation enrichment)

**Matching text**:
The single text derived from a Profile — either its Structured selections or its Self-description, never both — that is compared against Foundation purposes to produce Matches.

### Finding foundations

**Match**:
A Foundation paired with a similarity score indicating how well its purpose aligns with the Matching text.

**Geographic filter**:
A hard constraint limiting Matches to Foundations whose **Service area** covers the Profile's county or municipality, or covers the whole country. Applied independently of which source produced the Matching text.

## Relationships

- A **User** owns one or more **Profiles**
- A **Profile** contains **Structured selections** and optionally a **Self-description**
- A search produces **Matches** from exactly one source of **Matching text**: either the Structured selections or the Self-description
- A **Foundation** has a **Registered address** and a **Service area** — distinct concepts that may disagree; eligibility follows the Service area
- The **Geographic filter** constrains Matches regardless of Matching-text source
- The **Self-description** drives Finding only — it never feeds application generation, which consumes Structured selections only

## Example dialogue

> **Dev:** "If a user only fills in their Self-description and leaves the Structured selections empty, can they still get Matches?"
> **Domain expert:** "Yes — either one alone can become the Matching text. But the Geographic filter still applies if they've picked a county."

> **Dev:** "And if both are filled in?"
> **Domain expert:** "They choose which one drives the search. We never blend them into one Matching text."

## Flagged ambiguities

- "freetext" was used to mean both a format (any string) and the feature (the user's own words) — resolved: the concept is called **Self-description**; "freetext" is avoided entirely.
- "profile data" was used loosely for both Structured selections and Self-description — resolved: these are distinct sources of **Matching text**.
- Whether the Self-description should also feed application generation — resolved for now: no (Matching only). Opt-in inclusion on the Generate page is the acknowledged future direction, deliberately deferred.
- "location" is ambiguous between a Foundation's **Registered address** and its **Service area** — resolved: these are distinct concepts; eligibility follows Service area.
- How multi-place Service-area mentions (e.g., "Kalmar och Västervik") should be split into codes — unresolved: defer to the manual-review path for ambiguous cases; unambiguous single-place mentions proceed on their own.
