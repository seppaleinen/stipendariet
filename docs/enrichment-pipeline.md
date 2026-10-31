# Foundation Enrichment Pipeline - Admin User Guide

This guide explains how to use the enrichment pipeline admin interface, interpret results, and export data.

## Triggering Enrichment

### Start Enrichment for New Foundations

1. Navigate to **Enrichment Results** in the admin panel
2. Click **Start Enrichment** button
3. Optional: Set batch size (default: 50 foundations)

The system will:
- Find foundations with `enrichment_status = UNPROCESSED`
- Queue them for the enrichment pipeline
- Update status to `PENDING` as they're processed

### Enrich Single Foundation

For testing or re-processing:
1. Click a foundation row to expand
2. Click the **eye icon** (View pipeline trace)
3. Or use the direct endpoint: `POST /api/admin/enrich/foundation/{id}`

## Reading Enrichment Results

### Status Legend

| Status | Description |
|--------|-------------|
| **Klar** (COMPLETED) | Successfully enriched with >=5 fields |
| **Misslyckades** (FAILED) | Pipeline failed after retries |
| **Ingen data** (NO_DATA) | No fields extracted from any source |
| **Ingen hemsida** (no_valid_site) | No valid website found |
| **Ej hittad** (NO_CANDIDATES) | No search candidates found |
| **Bearbetar** (PROCESSING) | Currently running |
| **Väntar** (PENDING) | Queued, not yet started |
| **Obehandlad** (UNPROCESSED) | Not yet processed |

### Interpreting Field Confidence

Each extracted field has an associated confidence score (0.0–1.0):

**High confidence (0.7–1.0)**: Reliable extraction, source verification recommended
**Medium confidence (0.4–0.7)**: Reasonable, cross-check with source URL
**Low confidence (0.0–0.4)**: Uncertain, verify manually

### Per-Field Source Attribution

The table shows:
- **Source URL**: Which website provided this field
- **Confidence**: LLM's confidence in the extraction

Use this to:
- Verify data sources
- Identify unreliable sources for future filtering
- Understand extraction quality per field

### Viewing the Pipeline Trace

Click the **eye 👁** icon on any foundation to open the trace modal.

**Trace Sections:**

1. **Discovery** (🔍): Candidate URLs found via search
2. **Validation** (🤖): LLM validation of each candidate URL
   - Green check: URL is relevant to the foundation
   - Red X: URL not relevant
3. **Sources** (🕷️): Crawled pages per source
   - Field names show extracted values
   - Page previews show what content was scraped
4. **Merged**: Final combined result with all 8 fields

**`re_search` Iterations** (Phase 6):
- Shows targeted re-queries for missing fields
- Lists which queries were run
- Shows which fields were filled

## Exporting Data

### CSV Export

For spreadsheets or manual review:
```
POST /api/admin/enrich/export
Content-Type: application/json

{
  "format": "csv"
}
```

Download includes columns:
- foundation_id, foundation_name
- contact_email, contact_phone, application_open, application_deadline, who_can_apply, how_to_apply, notes, enriched_description
- confidence (overall), source_url, extracted_at

### JSON Export

For programmatic processing:
```
POST /api/admin/enrich/export
Content-Type: application/json

{
  "format": "json"
}
```

JSON includes additional fields:
- `per_field_confidence`: Object mapping each field to its confidence score
- `source_per_field`: Object mapping each field to its contributing source URL

### Filtered Export

Export specific foundations:
```json
{
  "format": "json",
  "foundation_ids": [123, 456, 789]
}
```

## Field Completeness Dashboard

**Path**: `GET /api/admin/enrich/field-completeness?days=30`

Shows:
- **Per-field fill rates**: Percentage of records with each field filled
- **Daily buckets**: Track completeness over time
- **Overall ratio**: Foundations with ≥5/8 fields

Use this to:
- Monitor pipeline improvements
- Identify problematic fields
- Track progress before/after algorithm changes

## Prompt Version Management

### View Current Prompts

`GET /api/admin/enrich/defaults` returns current extraction and validation prompts.

### Understanding Prompt Versions

- **Name**: `extraction`, `validation`, `service_area`
- **Version**: Semantic version (e.g., `2.1.0`)
- **Production**: Only production prompts are used by the pipeline
- **Metrics**: Running averages for confidence and completeness

### Creating New Versions

1. Prepare new prompt template
2. POST to `/api/admin/enrich/prompts` (coming soon in Phase 8)
3. Test with manual enrichment
4. Set as production when validated

## Common Tasks

### Re-Process Failed Foundations

1. In the results table, filter by **Misslyckades** (FAILED)
2. Reset status via admin panel or database
3. Restart enrichment

### Verify Specific Fields

1. Find foundation in results table
2. Click eye icon to view trace
3. Navigate to **Sources** section
4. Click source URL to see extraction details
5. Follow the provided link to verify field completeness

### Bulk Status Reset

`POST /api/admin/enrich/reset`
- Resets all foundations to `UNPROCESSED`
- Useful for re-running with new prompts or algorithm changes

## Troubleshooting

### Foundation Shows "Ingen hemsida"

Possible causes:
- Foundation removed website
- Website URL not in search results
- Search ranking low

**Solution**: Check Bolagsverket registry for official website URL, add as custom source.

### Low Confidence Fields

- Verify the source URL in trace
- Check if content exists on page (page preview)
- Consider manual curation for critical fields

### Export Returns Empty File

- Check date range filter
- Verify foundation IDs exist
- Ensure foundations have been processed

## Service Area

The **Service Area** field shows geographic coverage (e.g., "Skåne, Halland") derived from foundation name and purpose. This is extracted in Stage 6 and can be backfilled independently.

For bulk service area updates:
```
POST /api/admin/enrich/backfill-service-area?limit=20
```

## API Reference Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/enrich/start` | POST | Start enrichment for all UNPROCESSED |
| `/admin/enrich/details` | GET | List enrichment results (filterable) |
| `/admin/enrich/status` | GET | Summary counts by status |
| `/admin/enrich/trace/{id}` | GET | Full pipeline trace for foundation |
| `/admin/enrich/field-completeness` | GET | Dashboard metrics |
| `/admin/enrich/prompt-metrics` | GET | Per-prompt performance |
| `/admin/enrich/export` | POST | Export data (CSV/JSON) |