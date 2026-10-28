from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class PipelineContext:
    """Context passed through pipeline stages with inputs/outputs."""

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


class PipelineStage(ABC):
    """Abstract base class for pipeline stages."""

    name: ClassVar[str]

    @abstractmethod
    async def run(self, ctx: PipelineContext) -> None:
        """Execute the stage with the given context."""
        pass
