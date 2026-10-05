"""
Priority scoring for business opportunities: a market-oriented way to
prioritize nuclear plant types and customers by likelihood of success.
This module is an explicit, testable scoring function that combines
multiple market-relevant signals into a single comparable priority
score, rather than leaving prioritization as an implicit,
undocumented judgment call.

The specific weights and signals below are an illustrative model of
what matters for prioritizing outage-service opportunities.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringInputs:
    is_existing_customer: bool
    estimated_value_eur: int
    reactor_fleet_size_for_operator: int   # how many plants this operator runs -- more plants, more repeat-business potential
    days_until_outage: int                 # lead time: too soon to realistically pursue, or plenty of runway
    service_category_typical_value_eur: int


def compute_priority_score(inputs: ScoringInputs) -> float:
    """Returns a 0-100 priority score. Higher is a better business
    opportunity to pursue. The scoring logic is intentionally simple
    and fully explainable (see compute_priority_breakdown for the
    per-factor contributions) rather than an opaque black box --
    exactly the property you'd want if a real team has to trust and
    override these scores.
    """
    breakdown = compute_priority_breakdown(inputs)
    return round(sum(breakdown.values()), 2)


def compute_priority_breakdown(inputs: ScoringInputs) -> dict:
    """Returns the individual, named contributions to the total score,
    so a user can see exactly *why* an opportunity scored the way it
    did -- not just the final number."""
    breakdown = {}

    # Existing customer relationship: real, repeat business is easier
    # to win than a cold approach to a new operator.
    breakdown["existing_customer_relationship"] = 25.0 if inputs.is_existing_customer else 5.0

    # Contract value relative to the service category's typical value:
    # meaningfully above-typical deals score higher, but this is capped
    # so a single outlier can't dominate the whole score.
    if inputs.service_category_typical_value_eur > 0:
        value_ratio = inputs.estimated_value_eur / inputs.service_category_typical_value_eur
    else:
        value_ratio = 1.0
    breakdown["value_relative_to_category"] = round(min(value_ratio, 2.0) * 15.0, 2)

    # Fleet size: an operator running more reactors represents more
    # potential repeat/follow-on business from a successful first win.
    breakdown["operator_fleet_size"] = round(min(inputs.reactor_fleet_size_for_operator, 10) * 2.0, 2)

    # Lead time: too little runway (can't realistically prepare a
    # competitive offer) or excessively far out (low near-term
    # certainty) both score lower than a realistic mid-range window.
    breakdown["lead_time_fit"] = _lead_time_score(inputs.days_until_outage)

    return breakdown


def _lead_time_score(days_until_outage: int) -> float:
    if days_until_outage < 0:
        return 0.0  # outage already in the past -- not a real opportunity
    if days_until_outage < 30:
        return 5.0   # too little runway to realistically compete
    if 90 <= days_until_outage <= 540:
        return 20.0  # realistic preparation and bidding window
    if days_until_outage < 90:
        return 12.0  # tight but possible
    return 8.0       # far out -- lower near-term certainty


def tier_for_score(score: float) -> str:
    """Converts a numeric score into the coarse High/Medium/Low tier
    stored alongside it in the opportunities table, since a sales or
    business-development reader often wants the tier for a quick scan
    even though the underlying score is what's actually compared."""
    if score >= 55.0:
        return "High"
    if score >= 35.0:
        return "Medium"
    return "Low"
