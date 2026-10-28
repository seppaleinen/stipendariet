# PR: Phase 9 Pipeline Service Abstraction

## Summary

Introduces a `PipelineStage` abstraction layer that decouples the orchestrator from concrete stage implementations, enabling cleaner testing and future extensibility.

## Changes

### New Files

- `backend/app/pipeline/base.py` — `PipelineStage` ABC and `PipelineContext` dataclass
- `backend/tests/test_pipeline_abstraction.py` — comprehensive test coverage for the abstraction

### Modified Files

- `backend/app/pipeline/orchestrator.py`
  - Refactored to use `_get_default_stages()` mapping
  - Added runtime type validation for injected `stages` parameter
  - Executes stages via interface: `await stages["<key>"].run(ctx)`

- `backend/app/pipeline/discovery.py` — added `DiscoveryStage` class
- `backend/app/pipeline/validation.py` — added `UrlValidationStage` class
- `backend/app/pipeline/crawler.py` — added `CrawlStage` class
- `backend/app/pipeline/extraction.py` — added `ExtractionStage` class
- `backend/app/pipeline/service_area.py` — added `ServiceAreaStage` class

- `backend/tests/test_pipeline_failure_modes.py` — updated patch targets to source modules

### Key Implementation Details

**PipelineStage Interface:**
```python
class PipelineStage(ABC):
    name: ClassVar[str]
    
    @abstractmethod
    async def run(self, ctx: PipelineContext) -> None:
        pass
```

**PipelineContext:** Carries all inputs, intermediate state, and outputs through the pipeline stages.

**Dependency Injection:** The orchestrator's `run_foundation_pipeline_task()` accepts an optional `stages` dict for testing and customization.

## Testing

All existing tests pass. New tests added:

- `test_get_default_stages_returns_five_keys_with_matching_names` — validates stage mapping
- `test_stage_classes_instantiate_as_pipeline_stage` — interface compliance for all 5 stages
- `test_run_pipeline_uses_injected_stages` — demonstrates clean dependency injection
- `test_run_pipeline_falls_back_to_default_stages_when_omitted` — default behavior
- Per-stage delegation tests — each stage correctly calls its underlying function

Run tests:
```bash
cd backend
pytest tests/test_pipeline_abstraction.py
pytest tests/test_pipeline.py
pytest tests/test_pipeline_failure_modes.py
```

## Migration Notes for Developers

### Updating Existing Tests

If you have tests that patch pipeline functions, update patch targets from the orchestrator to the source modules:

**Before:**
```python
@patch("app.pipeline.orchestrator.discover_candidate_urls")
```

**After:**
```python
@patch("app.pipeline.discovery.discover_candidate_urls")
```

Apply this pattern to:
- `discovery.discover_candidate_urls`
- `validation.validate_candidate_url`
- `crawler.crawl_foundation_site`
- `extraction.extract_data_from_content`
- `service_area.extract_service_area`

### Custom Stage Implementations

You can now inject custom stage implementations:

```python
class CustomDiscoveryStage(PipelineStage):
    name = "discovery"
    
    async def run(self, ctx: PipelineContext) -> None:
        # Your custom logic here
        ctx.candidate_urls = [...]

stages = {
    "service_area": ServiceAreaStage(),
    "discovery": CustomDiscoveryStage(),  # Custom implementation
    "validation": UrlValidationStage(),
    "crawl": CrawlStage(),
    "extraction": ExtractionStage(),
}

await run_foundation_pipeline_task({}, foundation_id=1, stages=stages)
```

### Backward Compatibility

- Module-level functions remain public and callable directly
- No changes to the public API or pipeline behavior
- Existing integrations continue to work without modification

## Breaking Changes

None. The abstraction is fully backward compatible.

## Related

- ADR-0008: Pipeline Service Abstraction (Phase 9)
- Hindsight: Phase 9 Pipeline Service Abstraction initiative