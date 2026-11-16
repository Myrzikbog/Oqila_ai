"""The legal knowledge base: one source of facts for the calculator, the AI, the FAQ and the bot."""
import json
import re
from datetime import date, datetime
from pathlib import Path

import pytest

from services import legal_calc
from services.legal_faq import get_faq
from services.legal_kb import STATUSES, KnowledgeBase, kb

ROOT = Path(__file__).resolve().parent.parent
FACTS = sorted(kb.facts)


@pytest.mark.parametrize("fact_id", FACTS)
def test_every_fact_has_a_source_a_date_and_both_texts(fact_id):
    fact = kb.facts[fact_id]
    assert kb.is_allowed_domain(fact["source_url"]), f"{fact_id}: {fact['source_url']} is not on the allowlist"
    assert datetime.strptime(fact["verified_at"], "%Y-%m-%d").date() <= date.today()
    assert fact["status"] in STATUSES and fact["legal_basis"] and fact["tags"]
    for lang in ("ru", "uz"):
        text = kb.fact_text(fact_id, lang)
        assert len(text) > 20 and "{" not in text, f"{fact_id}/{lang}: unresolved placeholder in {text!r}"
    assert fact["source_url"].startswith("https://")


def test_confirmed_facts_come_from_lex_uz():
    for fact in kb.facts.values():
        if fact["status"] == "confirmed":
            assert kb.is_allowed_domain(fact["source_url"]) and "lex.uz" in fact["source_url"], fact["id"]


def test_open_questions_are_marked_unverified():
    """docs/LEGAL_VERIFICATION.md, 'what remains to check by hand': the model must say 'needs checking' about these."""
    unverified = {f["id"] for f in kb.facts.values() if f["status"] == "unverified"}
    assert unverified == {"rate_1_to_5bn", "uzum_self_employed_rule", "hunarmand", "ofd_receipts_click_payme"}
    assert all("NOT VERIFIED" in line for line in kb.render_prompt("ru", ids=unverified).splitlines())
    assert all("value" not in kb.facts[i] or kb.facts[i]["value"] is None for i in unverified)


def test_values_and_derived_values():
    assert kb.value("brv") == 440_000 and kb.value("threshold_brv") == 12_000 and kb.value("threshold_uzs") == 5_280_000_000
    assert kb.value("ecp_person") == 30_800 and kb.value("ecp_legal") == 44_000 and kb.value("fee_yatt_online") == 396_000
    assert kb.value("fee_yatt_cgu") == 440_000 and kb.value("social_tax_yatt") == 440_000
    assert kb.fmt("brv") == "440 000" and kb.fmt("threshold_uzs_bn") == "5,28" and kb.fmt("turnover_rate") == "1"
    with pytest.raises(KeyError):
        kb.value("hunarmand")  # a text fact without a number


def test_the_calculator_reads_its_constants_from_the_base():
    assert legal_calc.BRV_UZS == kb.value("brv")
    assert legal_calc.GENERAL_REGIME_THRESHOLD_BRV == kb.value("threshold_brv")
    assert legal_calc.ANNUAL_TURNOVER_LIMIT == kb.value("threshold_uzs")
    assert legal_calc.UNIFIED_TURNOVER_TAX_RATE == kb.value("turnover_rate") / 100
    assert legal_calc.YATT_MANDATORY_SOCIAL_TAX == kb.value("social_tax_yatt")
    assert legal_calc.SELF_EMPLOYED_PENSION_TAX == kb.value("social_tax_self_employed")


def test_a_changed_fact_changes_every_reader(tmp_path, monkeypatch):
    data = json.loads((ROOT / "services" / "legal_kb.json").read_text(encoding="utf-8"))
    for fact in data["facts"]:
        if fact["id"] == "brv":
            fact["value"] = 500_000
    path = tmp_path / "kb.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    other = KnowledgeBase(path)
    assert other.value("social_tax_yatt") == 500_000 and "500 000" in other.fact_text("brv", "ru") and "7%" in other.fact_text("ecp_person", "ru")
    assert other.value("ecp_person") == 35_000 and other.fmt("threshold_uzs_bn") == "6"


NAKED = re.compile(r"440\s?000|5,28")


@pytest.mark.parametrize("path", ["frontend/src/components/TabLegal.jsx", "services/ai_service.py", "services/telegram_service.py", "services/legal_ai.py", "services/legal_tools.py"])
def test_no_naked_legal_amounts_outside_the_base(path):
    """A number that is a legal fact is written once, in services/legal_kb.json."""
    source = (ROOT / path).read_text(encoding="utf-8")
    assert not NAKED.search(source), f"{path} has a hard-coded amount"
    assert "440000" not in source


def test_the_legal_prompt_and_the_bot_read_the_base():
    from services.legal_ai import _rules
    from services.telegram_service import TAX_CALENDAR_TEXT_RU, TAX_CALENDAR_TEXT_UZ

    for text in (_rules("ru"), _rules("uz")):
        assert "[F:brv]" in text and "440 000" in text and "[F:threshold_brv]" in text and "NOT VERIFIED" in text
    assert "440 000" in TAX_CALENDAR_TEXT_RU and "5,28" in TAX_CALENDAR_TEXT_UZ and "12 000" in TAX_CALENDAR_TEXT_RU


def test_render_prompt_format_and_selection():
    line = kb.render_prompt("ru", ids=["turnover_rate"])
    assert line.startswith("[F:turnover_rate] Налог с оборота") and "ЗРУ-1108" in line and "checked 2026-11-05" in line and "confirmed" in line
    only_tax = kb.render_prompt("uz", tags=["ecp"])
    assert "[F:ecp_person]" in only_tax and "[F:brv]" not in only_tax and "ERI" in only_tax
    assert kb.render_prompt("ru").count("[F:") == len(kb.facts)


def test_facts_for_a_question():
    assert "ecp_person" in kb.facts_for("Сколько стоит ЭЦП?") and "ecp_person" in kb.facts_for("ERI qancha turadi?")
    top = kb.facts_for("Могу ли я самозанятой перепродавать товары из Китая на Uzum?")
    assert "self_employed_item33" in top[:2] and "uzum_self_employed_rule" in top
    assert kb.facts_for("абракадабра") == []


def test_stale_facts():
    assert kb.stale(90, today=date(2026, 11, 30)) == []
    old = kb.stale(90, today=date(2027, 3, 1))
    assert len(old) == len(kb.facts) and old[0]["age_days"] >= old[-1]["age_days"] > 90
    assert kb.stale(30, today=date(2026, 12, 20))[0]["id"] in kb.facts


def test_the_stale_script(tmp_path):
    import subprocess
    import sys

    res = subprocess.run([sys.executable, str(ROOT / "scripts" / "legal_kb_stale.py"), "--days", "9999"], capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0 and "UNVERIFIED" in res.stdout and "hunarmand" in res.stdout


def test_domain_allowlist():
    assert kb.is_allowed_domain("https://www.lex.uz/ru/docs/1") and kb.is_allowed_domain("my.soliq.uz") and kb.is_allowed_domain("fo.birdarcha.uz")
    assert not kb.is_allowed_domain("https://evil-lex.uz") and not kb.is_allowed_domain("https://lex.uz.evil.com") and not kb.is_allowed_domain("")


def test_offline_answer_is_a_structured_template_built_from_the_base():
    for lang in ("ru", "uz"):
        answer = kb.offline_answer(lang)
        assert answer["confidence"] == "low" and len(answer["steps"]) == 4 and answer["sources"] and not re.search(r"\{\w+\}", json.dumps(answer, ensure_ascii=False))
    ru = json.dumps(kb.offline_answer("ru"), ensure_ascii=False)
    assert "440 000" in ru and "шаблонный справочник" in ru and "1%" in ru


def test_faq_comes_from_the_base():
    for lang in ("ru", "uz"):
        items = get_faq(lang)
        assert len(items) == 9 and {"id", "icon", "title", "steps", "links", "law", "tip"} <= set(items[0])
        blob = json.dumps(items, ensure_ascii=False)
        assert not re.search(r"\{\w+\}", blob), "unresolved placeholder"
    ru = json.dumps(get_faq("ru"), ensure_ascii=False)
    assert "30 800" in ru and "396 000" in ru and "5,28" in ru and "440 000" in ru and "12 000 БРВ" in ru


def test_the_old_faq_is_gone_from_the_frontend():
    source = (ROOT / "frontend/src/components/TabLegal.jsx").read_text(encoding="utf-8")
    assert "FAQ_RU" not in source and "FAQ_UZ" not in source and "/api/legal-faq" in source
