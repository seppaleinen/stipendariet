# Enrichment Pipeline TODO

## Future Enhancements

### Source Table Architecture (Option B)
**Priority:** Medium  
**Complexity:** High

Create a database table for "sources" (aggregator sites like `annsansradstod.se`) that list multiple foundations with their deadlines.

**Proposed Schema:**
```sql
-- Source sites that list multiple foundations
CREATE TABLE enrichment_sources (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    site_name TEXT,
    source_type TEXT,  -- 'aggregator', 'official', 'blog'
    last_scraped TIMESTAMP,
    reliability_score FLOAT,  -- 0-1 based on accuracy history
    created_at TIMESTAMP DEFAULT NOW()
);

-- Junction table linking foundations to sources
CREATE TABLE foundation_source_data (
    id SERIAL PRIMARY KEY,
    foundation_id INTEGER REFERENCES foundations(id),
    source_id INTEGER REFERENCES enrichment_sources(id),
    application_deadline TEXT,
    application_start TEXT,
    application_method TEXT,
    extracted_at TIMESTAMP DEFAULT NOW(),
    confidence FLOAT,
    UNIQUE(foundation_id, source_id)
);
```

**Benefits:**
- Track data provenance - know where each piece of data came from
- Pre-parse aggregator sites once, use for multiple foundations
- Compare data from multiple sources for same foundation
- Build reliability scores over time based on accuracy

**Implementation Steps:**
1. Create Alembic migration for new tables
2. Update enrichment worker to save source information
3. Add admin UI to view sources and their data
4. Implement source reliability scoring based on user feedback
