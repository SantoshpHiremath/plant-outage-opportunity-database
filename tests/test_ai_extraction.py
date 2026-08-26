import pytest

from src.ai_extraction import MockExtractionClient, RealAnthropicExtractionClient


class TestMockExtractionClient:
    def setup_method(self):
        self.client = MockExtractionClient()

    def test_extracts_reactor_type_when_mentioned(self):
        result = self.client.extract("The Doel Nuclear Power Plant operates four PWR units in Belgium.")
        assert result.reactor_type_guess == "PWR"

    def test_extracts_a_different_reactor_type_correctly(self):
        result = self.client.extract("Fukushima Daini is a BWR facility operated by TEPCO.")
        assert result.reactor_type_guess == "BWR"

    def test_returns_none_reactor_type_when_not_mentioned(self):
        result = self.client.extract("A routine maintenance outage is scheduled for next spring.")
        assert result.reactor_type_guess is None

    def test_extracts_refueling_outage_type(self):
        result = self.client.extract("The plant will begin a refueling outage in March.")
        assert result.outage_type_guess == "Refueling"

    def test_extracts_major_overhaul_outage_type(self):
        result = self.client.extract("A major overhaul is planned to extend plant lifetime.")
        assert result.outage_type_guess == "Major Overhaul"

    def test_extracts_service_category_for_steam_generator(self):
        result = self.client.extract("Inspection of the steam generator tubing is required before restart.")
        assert result.service_category_guess == "Steam Generator Inspection"

    def test_extracts_plant_name_before_nuclear_keyword(self):
        result = self.client.extract("Gravelines Nuclear Power Plant will undergo a scheduled outage.")
        assert result.plant_name_guess == "Gravelines"

    def test_confidence_increases_with_more_signals_found(self):
        rich_text = "Gravelines Nuclear Power Plant, a PWR facility, will begin a refueling outage."
        sparse_text = "Some maintenance is planned."
        rich_result = self.client.extract(rich_text)
        sparse_result = self.client.extract(sparse_text)
        assert rich_result.confidence > sparse_result.confidence

    def test_different_inputs_produce_different_outputs(self):
        # Confirms this is a real parser, not a fixed stub -- two
        # different texts must not produce identical extraction results.
        result_a = self.client.extract("Gravelines Nuclear Power Plant is a PWR site.")
        result_b = self.client.extract("Some unrelated plain maintenance text with no signals.")
        assert result_a != result_b

    def test_raw_snippet_is_preserved_on_the_result(self):
        text = "A sample outage announcement."
        result = self.client.extract(text)
        assert result.raw_snippet == text


class TestRealAnthropicExtractionClient:
    def test_raises_immediately_without_an_api_key(self):
        # This class must never silently degrade to mock-like behavior --
        # confirms it fails loudly and immediately when no real key is given.
        with pytest.raises(RuntimeError, match="requires a real Anthropic API key"):
            RealAnthropicExtractionClient(api_key=None)

    def test_raises_immediately_with_an_empty_string_key(self):
        with pytest.raises(RuntimeError, match="requires a real Anthropic API key"):
            RealAnthropicExtractionClient(api_key="")
