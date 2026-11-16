"""
legal_tools.py — functions the legal assistant calls instead of doing arithmetic itself.

A language model must not compute taxes in its head: every sum in an answer comes from one of these functions
or from a knowledge-base fact. `make_tools()` returns plain Python functions (the Gemini SDK reads their names,
type hints and docstrings as the tool declarations) that remember what was called and what they returned, so the
answer can be checked afterwards (services/legal_ai.py: check_amounts).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from services.legal_calc import calculate
from services.legal_kb import kb

TOOL_NAMES = ("calc_tax", "social_tax", "check_threshold", "get_fact", "self_employed_allowed")

_EXCLUDED_WORDS = ("парикмахер", "косметолог", "визаж", "фото", "видеосъ", "видеосъёмк", "sartarosh", "kosmetolog", "foto", "video")
_RESALE_WORDS = ("перепрод", "китай", "опт", "рынок", "закуп", "qayta sot", "xitoy", "ulgurji", "bozor")
_OWN_WORDS = ("ручн", "хэндмейд", "handmade", "пошив", "шить", "вышив", "выпечк", "кулинар", "своё производство", "изготов", "qo'lda", "tikuv", "pazanda")


@dataclass
class ToolRecorder:
    """What the model asked for and what the functions answered."""
    calls: List[str] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)

    def record(self, name: str, output: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self.calls:
            self.calls.append(name)
        self.outputs.append(output)
        return output

    def numbers(self) -> List[float]:
        out: List[float] = []

        def walk(value: Any) -> None:
            if isinstance(value, bool):
                return
            if isinstance(value, (int, float)):
                out.append(float(value))
            elif isinstance(value, dict):
                for v in value.values():
                    walk(v)
            elif isinstance(value, (list, tuple)):
                for v in value:
                    walk(v)

        for o in self.outputs:
            walk(o)
        return out


def _calc(sale_price: float, cost_price: float, business_type: str, trade_regime: str, category: str) -> Dict[str, Any]:
    r = calculate(sale_price=max(0.0, float(sale_price)), cost_price=max(0.0, float(cost_price)), lang="ru",
                  category=category, business_type=business_type, trade_regime=trade_regime)
    return {
        "sale_price": r.sale_price, "cost_price": r.cost_price, "gross_profit": r.gross_profit, "margin_pct": r.margin_pct,
        "self_employed_allowed": r.self_employed_allowed, "self_employed_tax_per_item": r.self_employed_tax,
        "yatt_turnover_tax_per_item": r.yatt_turnover_tax, "yatt_social_tax_monthly": r.yatt_social_tax_monthly,
        "uzum_commission": r.uzum_commission_amount, "uzum_logistics": r.uzum_logistics_fee, "uzum_net_profit_per_item": r.uzum_net,
        "net_profit_per_item": r.net_profit,
    }


def _social(status: str, months: int) -> Dict[str, Any]:
    brv = kb.value("brv")
    months = max(1, min(int(months), 120))
    if status in ("yatt", "ятт", "ip", "yatt_production"):
        return {"status": "yatt", "months": months, "monthly_uzs": brv, "total_uzs": brv * months, "basis": kb.facts["social_tax_yatt"]["legal_basis"], "mandatory": True}
    return {"status": "self_employed", "yearly_uzs": brv, "months": months, "total_uzs": brv, "basis": kb.facts["social_tax_self_employed"]["legal_basis"], "mandatory": False}


def _threshold(annual_turnover: float) -> Dict[str, Any]:
    limit = kb.value("threshold_uzs")
    turnover = max(0.0, float(annual_turnover))
    return {"threshold_brv": kb.value("threshold_brv"), "threshold_uzs": limit, "annual_turnover_uzs": turnover,
            "percent_of_threshold": round(turnover / limit * 100, 2), "exceeds": turnover > limit,
            "remaining_uzs": max(0.0, limit - turnover), "basis": kb.facts["threshold_brv"]["legal_basis"]}


def _allowed(activity: str) -> Dict[str, Any]:
    a = (activity or "").casefold()
    if any(w in a for w in _EXCLUDED_WORDS):
        verdict, ids = "not_allowed", ["self_employed_list"]
    elif any(w in a for w in _RESALE_WORDS):
        verdict, ids = "only_via_electronic_platform_or_yatt", ["self_employed_item33", "uzum_self_employed_rule"]
    elif any(w in a for w in _OWN_WORDS):
        verdict, ids = "likely_allowed_check_list", ["self_employed_list", "self_employed_item33"]
    else:
        verdict, ids = "check_in_soliq_app", ["self_employed_list"]
    return {"activity": activity, "verdict": verdict, "fact_ids": ids, "note": "The exact list is checked in the Soliq app."}


def make_tools(recorder: ToolRecorder, lang: str = "ru") -> List[Callable[..., Dict[str, Any]]]:
    """The tool functions bound to one recorder."""

    def calc_tax(sale_price: float, cost_price: float, business_type: str = "resale", trade_regime: str = "ecommerce", category: str = "craft") -> Dict[str, Any]:
        """Profit and taxes for ONE item. business_type: resale | production | services. trade_regime: ecommerce | standard. category: craft | clothing | food | beauty | decor. All amounts in UZS."""
        return recorder.record("calc_tax", _calc(sale_price, cost_price, business_type, trade_regime, category))

    def social_tax(status: str, months: int = 1) -> Dict[str, Any]:
        """Social tax in UZS. status: yatt (mandatory, per month) or self_employed (voluntary, per year)."""
        return recorder.record("social_tax", _social(status, months))

    def check_threshold(annual_turnover: float) -> Dict[str, Any]:
        """Compare the annual turnover (UZS) with the threshold of the general tax regime (VAT and profit tax)."""
        return recorder.record("check_threshold", _threshold(annual_turnover))

    def get_fact(fact_id: str) -> Dict[str, Any]:
        """The text, legal basis, source and check date of one fact of the knowledge base by its id, for example brv or turnover_rate."""
        fact = kb.facts.get(fact_id)
        if not fact:
            return recorder.record("get_fact", {"error": "unknown fact", "known_ids": sorted(kb.facts)})
        out = {"id": fact_id, "text": kb.fact_text(fact_id, lang), "legal_basis": fact["legal_basis"], "source_url": fact["source_url"],
               "verified_at": fact["verified_at"], "status": fact["status"]}
        if kb.number_values().get(fact_id) is not None:
            out["value"] = kb.value(fact_id)
        return recorder.record("get_fact", out)

    def self_employed_allowed(activity: str) -> Dict[str, Any]:
        """Whether an activity (for example hairdresser, handmade, reselling goods from China) is allowed for the self-employed."""
        return recorder.record("self_employed_allowed", _allowed(activity))

    return [calc_tax, social_tax, check_threshold, get_fact, self_employed_allowed]
