import pytest

from src.scoring import ScoringInputs, compute_priority_score, compute_priority_breakdown, tier_for_score


def make_inputs(**overrides):
    defaults = dict(
        is_existing_customer=False,
        estimated_value_eur=500_000,
        reactor_fleet_size_for_operator=1,
        days_until_outage=200,
        service_category_typical_value_eur=500_000,
    )
    defaults.update(overrides)
    return ScoringInputs(**defaults)


class TestComputePriorityScore:
    def test_existing_customer_scores_higher_than_otherwise_identical_new_customer(self):
        existing = compute_priority_score(make_inputs(is_existing_customer=True))
        new = compute_priority_score(make_inputs(is_existing_customer=False))
        assert existing > new

    def test_higher_estimated_value_relative_to_category_scores_higher(self):
        low_value = compute_priority_score(make_inputs(estimated_value_eur=200_000, service_category_typical_value_eur=500_000))
        high_value = compute_priority_score(make_inputs(estimated_value_eur=900_000, service_category_typical_value_eur=500_000))
        assert high_value > low_value

    def test_value_ratio_contribution_is_capped_so_extreme_outliers_dont_dominate(self):
        # A deal worth 20x the category's typical value should not score
        # dramatically higher than one worth 2x -- the cap should kick in.
        moderate = compute_priority_score(make_inputs(estimated_value_eur=1_000_000, service_category_typical_value_eur=500_000))  # 2x
        extreme = compute_priority_score(make_inputs(estimated_value_eur=10_000_000, service_category_typical_value_eur=500_000))  # 20x
        assert extreme == moderate  # both should hit the same capped contribution

    def test_larger_operator_fleet_scores_higher(self):
        small_fleet = compute_priority_score(make_inputs(reactor_fleet_size_for_operator=1))
        large_fleet = compute_priority_score(make_inputs(reactor_fleet_size_for_operator=8))
        assert large_fleet > small_fleet

    def test_fleet_size_contribution_is_capped(self):
        capped_at_ten = compute_priority_score(make_inputs(reactor_fleet_size_for_operator=10))
        way_above_cap = compute_priority_score(make_inputs(reactor_fleet_size_for_operator=50))
        assert capped_at_ten == way_above_cap

    def test_past_outage_scores_lower_than_a_realistic_future_one(self):
        past = compute_priority_score(make_inputs(days_until_outage=-10))
        realistic = compute_priority_score(make_inputs(days_until_outage=200))
        assert past < realistic

    def test_too_little_lead_time_scores_lower_than_realistic_window(self):
        too_soon = compute_priority_score(make_inputs(days_until_outage=10))
        realistic = compute_priority_score(make_inputs(days_until_outage=200))
        assert too_soon < realistic

    def test_far_future_scores_lower_than_the_realistic_preparation_window(self):
        far_future = compute_priority_score(make_inputs(days_until_outage=900))
        realistic = compute_priority_score(make_inputs(days_until_outage=300))
        assert far_future < realistic

    def test_score_is_always_non_negative(self):
        worst_case = compute_priority_score(make_inputs(
            is_existing_customer=False,
            estimated_value_eur=0,
            reactor_fleet_size_for_operator=0,
            days_until_outage=-100,
            service_category_typical_value_eur=500_000,
        ))
        assert worst_case >= 0


class TestComputePriorityBreakdown:
    def test_breakdown_sums_to_the_total_score(self):
        inputs = make_inputs(is_existing_customer=True, estimated_value_eur=700_000, reactor_fleet_size_for_operator=4)
        breakdown = compute_priority_breakdown(inputs)
        total = compute_priority_score(inputs)
        assert round(sum(breakdown.values()), 2) == total

    def test_breakdown_has_all_expected_factor_keys(self):
        breakdown = compute_priority_breakdown(make_inputs())
        expected_keys = {
            "existing_customer_relationship",
            "value_relative_to_category",
            "operator_fleet_size",
            "lead_time_fit",
        }
        assert set(breakdown.keys()) == expected_keys


class TestTierForScore:
    def test_high_tier_boundary(self):
        assert tier_for_score(55.0) == "High"
        assert tier_for_score(54.99) != "High"

    def test_medium_tier_boundary(self):
        assert tier_for_score(35.0) == "Medium"
        assert tier_for_score(34.99) == "Low"

    def test_low_tier_for_small_scores(self):
        assert tier_for_score(0.0) == "Low"

    @pytest.mark.parametrize("score", [0, 10, 34.9, 35, 54.9, 55, 80, 100])
    def test_every_score_maps_to_a_valid_tier(self, score):
        assert tier_for_score(score) in {"High", "Medium", "Low"}
