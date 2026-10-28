# ADR-0008: Pipeline Service Abstraction (Phase 9)

## Status

Accepted

## Context

The enrichment pipeline orchestrator in `backend/app/pipeline/orchestrator.py` was directly coupled to concrete module-level functions across five pipeline stages:

- `discover_candidate_urls` (discovery module)
- `validate_candidate_url` (validation module)
- `crawl_foundation_site` (crawler module)
- `extract_data_from_content` (extraction module)
- `extract_service_area` (service_area module)

This tight coupling created several problems:

1. **Testing complexity**: Unit tests had to patch functions at their call sites within the orchestrator, creating fragile test setups that broke when implementation details changed.

2. **Limited extensibility**: Swapping or customizing individual stages required modifying the orchestrator itself, violating the open-closed principle.

3. **Hidden dependencies**: The orchestrator's dependencies on each stage were implicit, making it unclear what capabilities were required for the pipeline to function.

4. **Difficulty injecting mocks**: Integration testing and experimentation with alternative implementations required invasive patches rather than clean dependency injection.

The Phase 9 initiative aimed to introduce an abstraction layer that decouples the orchestrator from concrete stage implementations while preserving all existing behavior and test coverage.

## Decision

Introduce a `PipelineStage` abstract base class and `PipelineContext` dataclass in `backend/app/pipeline/base.py`:

### PipelineStage Interface

```python
class PipelineStage(ABC):
    """Abstract base class for pipeline stages."""

    name: ClassVar[str]

    @abstractmethod
    async def run(self, ctx: PipelineContext) -> None:
        """Execute the stage with the given context."""
        pass
```

### PipelineContext Dataclass

A unified context object that carries all input parameters, intermediate state, and outputs through the pipeline:

```python
@dataclass
class PipelineContext:
    # Input parameters
    foundation_id: int
    foundation_name: str
    foundation_orgnr: str | None = None
    purpose: str | None = None
    description: str | None = None
    registered_county_code: str | None = None
    registered_municipality_code: str | None = None
    validation_sys_prompt: str | None = None
    validation_usr_prompt: str | None = None
    extraction_sys_prompt: str | None = None
    extraction_usr_prompt: str | None = None

    # Pipeline state
    candidate_urls: list[dict] = field(default_factory=list)
    validated_sources: list[dict] = field(default_factory=list)
    parsed_service_area: dict | None = None
    service_area_status: str | None = None

    # Per-source state
    active_source: dict | None = None
    crawled_pages: list[dict] = field(default_factory=list)
    extracted_data: dict | None = None

    # Output/trace
    trace: dict = field(default_factory=dict)
```

### Five Concrete Stage Classes

Each existing module-level function is wrapped in a stage class that implements the `PipelineStage` interface:

- `ServiceAreaStage` in `service_area.py`
- `DiscoveryStage` in `discovery.py`
- `UrlValidationStage` in `validation.py`
- `CrawlStage` in `crawler.py`
- `ExtractionStage` in `extraction.py`

Each stage class:
- Defines a `name` class variable matching its stage key
- Implements `run(ctx: PipelineContext)` to read inputs from and write outputs to the context
- Delegates to the existing module-level function, preserving all original logic

### Orchestrator Refactoring

The orchestrator's `_get_default_stages()` helper returns a mapping of stage instances:

```python
def _get_default_stages() -> dict:
    """Return the default pipeline stages mapping."""
    return {
        "service_area": ServiceAreaStage(),
        "discovery": DiscoveryStage(),
        "validation": UrlValidationStage(),
        "crawl": CrawlStage(),
        "extraction": ExtractionStage(),
    }
```

The main `run_foundation_pipeline_task()` function:
- Accepts an optional `stages: dict` parameter for dependency injection
- Falls back to `_get_default_stages()` when no stages are provided
- Validates that all injected stages implement `PipelineStage`
- Validates that all five required stage keys are present
- Executes stages via `await stages["<key>"].run(pctx)` instead of calling module functions directly

### Migration Rule for Tests

All `mock.patch` decorators in pipeline tests must target functions in their source modules, not the orchestrator:

- `app.pipeline.orchestrator.discover_candidate_urls` → `app.pipeline.discovery.discover_candidate_urls`
- `app.pipeline.orchestrator.validate_candidate_url` → `app.pipeline.validation.validate_candidate_url`
- `app.pipeline.orchestrator.crawl_foundation_site` → `app.pipeline.crawler.crawl_foundation_site`
- `app.pipeline.orchestrator.extract_data_from_content` → `app.pipeline.extraction.extract_data_from_content`
- `app.pipeline.orchestrator.extract_service_area` → `app.pipeline.service_area.extract_service_area`

## Consequences

### Positive

1. **Decoupled orchestrator**: The orchestrator no longer references concrete stage implementations, only the `PipelineStage` interface. This makes the pipeline architecture clearer and more maintainable.

2. **Cleaner testing**: Tests can now inject stub stages that implement the interface, avoiding complex patching of internal function calls. The test `test_run_pipeline_uses_injected_stages` demonstrates this pattern.

3. **Stage extensibility**: New stage implementations can be developed and injected without modifying the orchestrator. This enables A/B testing of stage algorithms, custom pipelines for specific foundation types, or experimental features.

4. **Explicit dependencies**: The `_get_default_stages()` function makes the pipeline's stage dependencies explicit and auditable.

5. **Unified context**: `PipelineContext` provides a single source of truth for pipeline state, making it easier to trace data flow and debug issues.

6. **Backward compatibility**: All existing behavior is preserved. The module-level functions remain public and callable directly, ensuring no breaking changes for external callers.

### Negative

1. **Added abstraction layer**: The stage classes introduce an additional level of indirection. Developers must understand both the interface and the concrete implementations.

2. **Boilerplate code**: Each stage class requires a small amount of boilerplate (class definition, `name` attribute, `run` method that delegates to the underlying function).

3. **Test migration required**: Existing tests that patch functions at the orchestrator level must be updated to patch at the source module level. This is a one-time cost but requires careful review.

4. **Slight performance overhead**: The additional method call layer introduces negligible but non-zero overhead. This is not expected to impact production performance given the I/O-bound nature of pipeline stages.

## Implementation Notes

- Files modified:
  - `backend/app/pipeline/base.py` (new) — `PipelineStage` ABC and `PipelineContext` dataclass
  - `backend/app/pipeline/orchestrator.py` — refactored to use stages
  - `backend/app/pipeline/discovery.py` — added `DiscoveryStage`
  - `backend/app/pipeline/validation.py` — added `UrlValidationStage`
  - `backend/app/pipeline/crawler.py` — added `CrawlStage`
  - `backend/app/pipeline/extraction.py` — added `ExtractionStage`
  - `backend/app/pipeline/service_area.py` — added `ServiceAreaStage`

- Tests added:
  - `backend/tests/test_pipeline_abstraction.py` — comprehensive test coverage for the abstraction layer
  - `backend/tests/test_pipeline_failure_modes.py` — updated to reflect new patch targets

- All existing tests pass without modification to their assertions, confirming backward compatibility.

## Related Documents

- [[Phase 9 Pipeline Service Abstraction]](kp-70b9ab3357a14f2da30114c3086c9353) — Hindsight knowledge page tracking this initiative
- [[Conventions and patterns]](kp-d507e1e61fe84bd89b77315f6d85f72b) — Project testing and refactoring conventions
