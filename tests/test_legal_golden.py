"""Golden set of the legal assistant (tests/legal_golden.json).

Offline (CI): the cases are consistent with the knowledge base, the tools and the classifier, and the pipeline
handles every case without errors. Live (by hand, real Gemini):

    OQILA_LIVE=1 GEMINI_API_KEY=... python -m pytest -m live tests/test_legal_golden.py -s

The live run prints the pass rate; the release threshold is the file's `threshold_percent` (90).
"""
import asyncio
import json
import os
import re
from pathlib import Path

import pytest

from services import legal_ai
from services.legal_kb import kb
from services.legal_safety import classify
from services.legal_tools import ToolRecorder, make_tools

GOLDEN = json.loads((Path(__file__).parent / "legal_golden.json").read_text(encoding="utf-8"))
CASES = GOLDEN["cases"]
PLACEHOLDER = re.compile(r"\{fact:(\w+)\}")


def expand(text: str) -> str:
    """{fact:brv} -> "440 000": the expected numbers come from the knowledge base, never from literals."""
    return PLACEHOLDER.sub(lambda m: kb.fmt(m.group(1)), text)


def norm(text: str) -> str:
    """Numbers compare as digits only (440 000 == 440000 == 440 000), everything else by lower case."""
    text = text.replace(" ", " ").replace("’", "'").replace("ʻ", "'").casefold()
    return re.sub(r"(?<=\d)[ ](?=\d{3}\b)", "", text)


def must_items(case):
    return [[expand(a) for a in (item if isinstance(item, list) else [item])] for item in case["must_contain"]]


def test_the_set_is_big_enough_and_bilingual():
    assert len(CASES) >= 30 and sum(1 for c in CASES if c["lang"] == "uz") >= 10
    assert len({c["id"] for c in CASES}) == len(CASES)
    assert GOLDEN["threshold_percent"] >= 90


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_case_is_consistent_with_the_base(case):
    for alternatives in must_items(case):
        for text in alternatives:
            assert "{" not in text, f"unresolved placeholder in {text!r}"
    prompt = norm(kb.render_prompt(case["lang"]))
    for match in PLACEHOLDER.findall(" ".join(i for i in case["must_contain"] if isinstance(i, str))):
        assert norm(kb.fmt(match)) in prompt, f"{match} is not in the facts the model gets"


@pytest.mark.parametrize("case", [c for c in CASES if c.get("expect_refusal") or c.get("expect_escalate")], ids=lambda c: c["id"])
def test_classifier_cases(case):
    kind = classify(case["question"])
    if case.get("expect_refusal"):
        assert kind == case["expect_refusal"]
        result = legal_ai.refusal(kind, case["lang"])
        assert result.ai_used is False and result.answer["short_answer"]
        assert all(w not in result.answer["short_answer"].lower() for w in case["must_not_contain"])
    else:
        assert kind == "sensitive" and legal_ai.refusal(kind, case["lang"]).answer["escalate"] is True


@pytest.mark.parametrize("case", [c for c in CASES if c.get("expect_tool")], ids=lambda c: c["id"])
def test_tool_cases(case):
    rec = ToolRecorder()
    tools = {f.__name__: f for f in make_tools(rec, case["lang"])}
    out = tools[case["expect_tool"]](**case["tool_args"])
    assert rec.calls == [case["expect_tool"]] and out
    if case["expect_tool"] == "social_tax":
        assert out["monthly_uzs"] == kb.value("brv")
    if case["expect_tool"] == "check_threshold":
        assert out["exceeds"] is False and out["percent_of_threshold"] < 100
    if case["expect_tool"] == "self_employed_allowed":
        assert out["verdict"] == "not_allowed"


def test_every_case_runs_through_the_pipeline_without_errors(fake_legal):
    from services.ai_service import ai_service

    for case in CASES:
        if case.get("expect_refusal"):
            continue
        result = asyncio.run(legal_ai.run_legal(ai_service, case["question"], case["lang"], profile=case["profile"]))
        assert result.fallback is None and result.answer["short_answer"], case["id"]
        assert result.answer["escalate"] is bool(case.get("expect_escalate", False)), case["id"]


# --- live ------------------------------------------------------------------------------------------------

@pytest.mark.live
def test_live_golden_set(capsys):
    if os.getenv("OQILA_LIVE") != "1" or not os.getenv("GEMINI_API_KEY"):
        pytest.skip("set OQILA_LIVE=1 and GEMINI_API_KEY to call the real Gemini API")
    from services.ai_service import AIService

    service = AIService()
    assert not service.is_mock, "the service did not get the key (is AI_MODE=mock set?)"
    passed, report = 0, []
    for case in CASES:
        result = asyncio.run(legal_ai.run_legal(service, case["question"], case["lang"], profile=case["profile"]))
        answer = result.answer
        text = norm(json.dumps(answer, ensure_ascii=False))
        problems = []
        if result.fallback:
            problems.append(f"fallback {result.fallback}")
        for alternatives in must_items(case):
            if not any(norm(a) in text for a in alternatives):
                problems.append(f"missing any of {alternatives}")
        for bad in case["must_not_contain"]:
            if norm(expand(bad)) in text:
                problems.append(f"contains {bad!r}")
        if "expect_tool" in case and case["expect_tool"] not in result.used_tools:
            problems.append(f"tool {case['expect_tool']} not used (used {result.used_tools})")
        if "expect_escalate" in case and answer["escalate"] is not case["expect_escalate"]:
            problems.append("escalate flag")
        if case.get("expect_refusal") and result.ai_used:
            problems.append("was not refused")
        for source in result.sources:
            if source.get("official") and not kb.is_allowed_domain(source["url"]):
                problems.append(f"official source off the allowlist: {source['url']}")
        for url in re.findall(r"https?://[^\s\"')]+", json.dumps(answer, ensure_ascii=False)):
            if not any(url.rstrip("/") == s["url"].rstrip("/") for s in result.sources) and not kb.is_allowed_domain(url):
                problems.append(f"unknown url {url}")
        if result.calc_warning:
            problems.append("sums not explained by tools or facts")
        passed += not problems
        report.append((case["id"], problems))
    percent = round(100 * passed / len(CASES), 1)
    with capsys.disabled():
        print(f"\nlegal golden set: {passed}/{len(CASES)} = {percent}%")
        for case_id, problems in report:
            if problems:
                print(f"  FAIL {case_id}: {'; '.join(problems)}")
    assert percent >= GOLDEN["threshold_percent"], f"{percent}% is below the release threshold"
