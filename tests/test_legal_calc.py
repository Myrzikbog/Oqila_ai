"""Tax and marketplace economics calculator."""
import pytest

from services.legal_calc import (
    BRV_UZS,
    UNIFIED_TURNOVER_TAX_RATE,
    UZUM_CATEGORY_RATES,
    UZUM_LOGISTICS_BASE_UZS,
    calculate,
)


def test_turnover_tax_is_one_percent_of_sale_price():
    r = calculate(sale_price=300_000, cost_price=100_000)
    assert UNIFIED_TURNOVER_TAX_RATE == 0.01
    assert r.yatt_turnover_tax == 3_000
    assert r.tax_payable_100 == 300_000
    assert r.yatt_net == 300_000 - 100_000 - 3_000


def test_gross_profit_and_margin():
    r = calculate(sale_price=200_000, cost_price=150_000)
    assert r.gross_profit == 50_000
    assert r.margin_pct == 25.0


@pytest.mark.parametrize("category", list(UZUM_CATEGORY_RATES))
def test_uzum_net_subtracts_commission_logistics_and_tax(category):
    sale, cost = 500_000, 200_000
    r = calculate(sale_price=sale, cost_price=cost, category=category)
    rate = UZUM_CATEGORY_RATES[category]["rate"]
    expected = (sale - cost) - round(sale * rate) - UZUM_LOGISTICS_BASE_UZS - round(sale * 0.01)
    assert r.uzum_commission_rate == rate
    assert r.uzum_net == expected


def test_uzum_min_price_breaks_even():
    r = calculate(sale_price=100_000, cost_price=80_000, category="craft")
    rate = UZUM_CATEGORY_RATES["craft"]["rate"]
    # At the minimum price, commission + tax + logistics + cost consume the whole price (±1 sum rounding)
    price = r.min_price_uzum
    leftover = price - price * (rate + 0.01) - UZUM_LOGISTICS_BASE_UZS - 80_000
    assert abs(leftover) <= 1


def test_unknown_category_falls_back_to_other():
    r = calculate(sale_price=100_000, cost_price=50_000, category="no-such-category")
    assert r.uzum_commission_rate == UZUM_CATEGORY_RATES["other"]["rate"]


def test_resale_forbids_self_employment():
    assert calculate(sale_price=100_000, cost_price=50_000, business_type="resale").self_employed_allowed is False
    assert calculate(sale_price=100_000, cost_price=50_000, business_type="production").self_employed_allowed is True
    assert calculate(sale_price=100_000, cost_price=50_000, business_type="services").self_employed_allowed is True


def test_social_tax_is_one_brv():
    r = calculate(sale_price=100_000, cost_price=50_000)
    assert r.yatt_social_tax_monthly == BRV_UZS


def test_zero_cost_is_allowed():
    r = calculate(sale_price=100_000, cost_price=0, business_type="services")
    assert r.cost_price == 0
    assert r.gross_profit == 100_000


def test_break_even_units():
    r = calculate(sale_price=300_000, cost_price=100_000, business_type="production", fixed_costs=1_000_000)
    assert r.break_even_units_self == -(-1_000_000 // r.self_employed_net)
    assert r.break_even_units_uzum is not None


def test_zero_sale_price_does_not_crash():
    r = calculate(sale_price=0, cost_price=10_000)
    assert r.margin_pct == 0.0
    assert r.net_share_pct == 0.0


def test_calculate_endpoint_rejects_negative_values(client):
    res = client.post("/api/calculate", json={"sale_price": -1, "cost_price": 10})
    assert res.status_code == 400
    ok = client.post("/api/calculate", json={"sale_price": 300000, "cost_price": 100000, "lang": "uz"})
    assert ok.status_code == 200
    assert ok.json()["yatt_turnover_tax"] == 3000
