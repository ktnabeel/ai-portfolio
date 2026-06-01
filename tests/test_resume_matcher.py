from __future__ import annotations

import json

from portfolio.resume_matcher.render import (
    _local_match,
    _parse_ai_json,
    analyze_resume_match,
)


def test_local_match_scores_and_recommends_missing_terms() -> None:
    result = _local_match(
        resume_text="Python developer with FastAPI and data pipeline experience.",
        job_text="Need Python, FastAPI, LangChain, NVIDIA, and resume scoring experience.",
    )

    assert 0 <= result["score"] <= 100
    assert result["source"] == "local"
    assert result["recommendations"]
    assert any("langchain" in item.lower() or "nvidia" in item.lower() for item in result["recommendations"])


def test_parse_ai_json_normalizes_response() -> None:
    raw = json.dumps({
        "score": 92,
        "summary": "Strong match.",
        "strengths": ["Python"],
        "gaps": "No Kubernetes evidence.",
        "recommendations": ["Add deployment bullet."],
    })

    result = _parse_ai_json(raw)

    assert result["score"] == 92
    assert result["source"] == "nvidia"
    assert result["gaps"] == ["No Kubernetes evidence."]


def test_analyze_resume_match_uses_uploaded_text_file(tmp_path, monkeypatch) -> None:
    resume = tmp_path / "resume.txt"
    resume.write_text("Python FastAPI LangChain NVIDIA production APIs", encoding="utf-8")

    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    html = analyze_resume_match(
        str(resume),
        "Hiring for Python FastAPI LangChain NVIDIA API integration.",
    )

    assert "Resume Match Score" in html
    assert "Local fallback analysis" in html
    assert "NVIDIA API" not in html


def test_analyze_resume_match_validates_inputs() -> None:
    assert "Upload a readable resume" in analyze_resume_match(None, "Python role")
    assert "Paste the job description" in analyze_resume_match(__file__, "")
