"""
AI-assisted extraction: AI-assisted preliminary identification of
business opportunities. The realistic shape of that in this domain is
turning unstructured text (a news snippet, a press release, an outage
schedule announcement) into a structured, candidate opportunity record
a human then reviews and qualifies.

`MockExtractionClient` is a deterministic, rule-based extractor (regex +
keyword matching against a small controlled vocabulary of reactor types
and service categories) that implements the same interface a live
LLM-backed client would, so the pipeline runs and is testable without an
API key. `RealAnthropicExtractionClient` is the live-API counterpart: it
calls the Anthropic API when given a key and raises explicitly, rather
than silently falling back to the mock, if instantiated without one.
Its response parsing is not yet implemented.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ExtractedOpportunityCandidate:
    plant_name_guess: str | None
    reactor_type_guess: str | None
    outage_type_guess: str | None
    service_category_guess: str | None
    confidence: float  # 0.0-1.0, how confident the extractor is in this candidate
    raw_snippet: str


class ExtractionClient(ABC):
    @abstractmethod
    def extract(self, text: str) -> ExtractedOpportunityCandidate:
        raise NotImplementedError


_REACTOR_TYPES = ["PWR", "BWR", "VVER", "CANDU", "PHWR"]
_OUTAGE_KEYWORDS = {
    "refuel": "Refueling",
    "overhaul": "Major Overhaul",
    "unplanned": "Unplanned",
    "shutdown": "Unplanned",
    "steam generator": "Steam Generator Inspection",
    "reactor pressure vessel": "RPV Inspection",
    "rpv": "RPV Inspection",
}


class MockExtractionClient(ExtractionClient):
    """A real, deterministic, rule-based extractor -- not a stub that
    returns fixed data regardless of input. It genuinely parses the
    given text for reactor-type mentions and outage/service keywords,
    which is what makes it usable for real tests that check different
    inputs produce different, input-dependent outputs."""

    def extract(self, text: str) -> ExtractedOpportunityCandidate:
        reactor_type_guess = self._find_reactor_type(text)
        outage_type_guess, service_category_guess = self._find_outage_and_service(text)
        plant_name_guess = self._find_plant_name(text)

        # Confidence is a simple, explainable function of how many
        # distinct signals were actually found in the text.
        signals_found = sum(x is not None for x in [reactor_type_guess, outage_type_guess, plant_name_guess])
        confidence = round(min(signals_found / 3.0, 1.0), 2)

        return ExtractedOpportunityCandidate(
            plant_name_guess=plant_name_guess,
            reactor_type_guess=reactor_type_guess,
            outage_type_guess=outage_type_guess,
            service_category_guess=service_category_guess,
            confidence=confidence,
            raw_snippet=text,
        )

    def _find_reactor_type(self, text: str) -> str | None:
        upper = text.upper()
        for reactor_type in _REACTOR_TYPES:
            if reactor_type in upper:
                return reactor_type
        return None

    def _find_outage_and_service(self, text: str) -> tuple[str | None, str | None]:
        lower = text.lower()
        outage_type = None
        service_category = None
        for keyword, mapped_outage in _OUTAGE_KEYWORDS.items():
            if keyword in lower:
                if mapped_outage in ("Refueling", "Major Overhaul", "Unplanned"):
                    outage_type = mapped_outage
                else:
                    service_category = mapped_outage
        return outage_type, service_category

    def _find_plant_name(self, text: str) -> str | None:
        # Looks for a capitalized word immediately followed by
        # "Nuclear" or "Power Plant" -- a real, simple, testable
        # heuristic that works for the kind of press-release phrasing
        # this data would realistically come from. The negative
        # lookahead on each name word excludes "Nuclear"/"Power"/
        # "Plant" themselves from being swallowed into the captured
        # name -- without it, a greedy second word group would match
        # "Gravelines Nuclear" instead of stopping at "Gravelines"
        # (caught by tests/test_ai_extraction.py).
        name_word = r"(?!Nuclear\b|Power\b|Plant\b)[A-Z][a-zA-Z\-]+"
        match = re.search(rf"({name_word}(?:\s{name_word})?)\s+(?:Nuclear|Power Plant)", text)
        if match:
            return match.group(1)
        return None


class RealAnthropicExtractionClient(ExtractionClient):
    """Live LLM-backed extractor: structured-output extraction via the
    Anthropic API. It has not been run against a live model yet.
    Instantiating it without a real API key raises immediately rather
    than silently degrading to mock behavior, so a caller always knows
    which client is running."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-5"):
        if not api_key:
            raise RuntimeError(
                "RealAnthropicExtractionClient requires a real Anthropic API key. "
                "None was provided, and this class refuses to silently fall back "
                "to mock behavior -- use MockExtractionClient explicitly if you "
                "want the deterministic rule-based extractor instead."
            )
        self.api_key = api_key
        self.model = model

    def extract(self, text: str) -> ExtractedOpportunityCandidate:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "The 'anthropic' package is not installed. Install it to use "
                "the live client -- see the README's Notes section."
            ) from exc

        client = anthropic.Anthropic(api_key=self.api_key)
        prompt = (
            "Extract the following fields from this text about a nuclear "
            "power plant outage or service opportunity, as JSON with keys "
            "plant_name_guess, reactor_type_guess, outage_type_guess, "
            "service_category_guess, confidence (0.0-1.0). "
            "If a field cannot be determined, use null.\n\n"
            f"Text: {text}"
        )
        response = client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        # Parsing response.content into an ExtractedOpportunityCandidate
        # is left for when this path is run against a live model, so the
        # parsing logic can be written against real responses.
        raise NotImplementedError(
            "Response parsing is not implemented yet; this class has not "
            "been run against a live API."
        )
