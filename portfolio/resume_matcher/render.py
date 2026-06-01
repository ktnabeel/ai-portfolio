"""Resume-to-job matching app powered by NVIDIA's OpenAI-compatible API."""

from __future__ import annotations

import json
import os
import re
import zipfile
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import gradio as gr


DEFAULT_NVIDIA_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

RM_TEXT = "var(--theme-ink, #101828)"
RM_MUTED = "var(--theme-muted, #667085)"
RM_PANEL = "var(--theme-panel, #ffffff)"
RM_LINE = "var(--theme-line, #d9e2ec)"
RM_GREEN = "var(--theme-green, #0f8f6e)"
RM_BLUE = "var(--theme-blue, #2563eb)"
RM_AMBER = "var(--theme-amber, #b7791f)"
RM_RED = "var(--theme-red, #dc2626)"


def _file_path(uploaded_file: Any) -> Path | None:
    if uploaded_file is None:
        return None
    if isinstance(uploaded_file, (str, Path)):
        return Path(uploaded_file)
    name = getattr(uploaded_file, "name", None)
    if name:
        return Path(name)
    if isinstance(uploaded_file, dict) and uploaded_file.get("path"):
        return Path(str(uploaded_file["path"]))
    return None


def _extract_text_from_file(uploaded_file: Any) -> str:
    path = _file_path(uploaded_file)
    if path is None or not path.exists():
        return ""

    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix == ".pdf":
        return _extract_pdf(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def _extract_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
    except (KeyError, OSError, zipfile.BadZipFile):
        return ""

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return ""

    return " ".join(node.text or "" for node in root.iter() if node.text).strip()


def _extract_pdf(path: Path) -> str:
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
            reader = module.PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _tokens(text: str) -> list[str]:
    stop_words = {
        "and", "the", "for", "with", "from", "that", "this", "will", "are", "you",
        "your", "our", "can", "have", "has", "job", "role", "resume", "candidate",
        "experience", "years", "work", "team", "teams", "using", "use", "used",
    }
    return [
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text.lower())
        if token not in stop_words
    ]


def _local_match(resume_text: str, job_text: str) -> dict[str, Any]:
    resume_tokens = set(_tokens(resume_text))
    job_counts = Counter(_tokens(job_text))
    required = [word for word, _ in job_counts.most_common(24)]
    present = [word for word in required if word in resume_tokens]
    missing = [word for word in required if word not in resume_tokens]
    coverage = len(present) / max(len(required), 1)
    score = round(max(20, min(88, coverage * 100)))

    return {
        "score": score,
        "summary": "Keyword and requirement coverage was estimated locally because NVIDIA analysis was unavailable.",
        "strengths": [f"Resume mentions {word}." for word in present[:5]] or ["Resume contains relevant baseline experience."],
        "gaps": [f"Job description emphasizes {word}, but it is not clearly reflected." for word in missing[:6]],
        "recommendations": [
            f"Add a concrete bullet showing hands-on {word} experience." for word in missing[:5]
        ] or ["Tighten bullets with quantified outcomes matched to the job description."],
        "source": "local",
    }


def _parse_ai_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if "```" in text:
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    data = json.loads(text)
    data["score"] = int(max(0, min(100, data.get("score", 0))))
    for key in ("strengths", "gaps", "recommendations"):
        value = data.get(key, [])
        data[key] = value if isinstance(value, list) else [str(value)]
    data["summary"] = str(data.get("summary", "")).strip()
    data["source"] = "nvidia"
    return data


def _nvidia_match(resume_text: str, job_text: str, api_key: str | None = None) -> dict[str, Any]:
    key = (api_key or os.environ.get("NVIDIA_API_KEY", "")).strip()
    if not key:
        return _local_match(resume_text, job_text)

    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=DEFAULT_NVIDIA_MODEL,
        temperature=0.1,
        base_url=NVIDIA_BASE_URL,
        openai_api_key=key,
    )
    prompt = f"""
You are an expert technical recruiter. Compare the resume to the job description.
Return only JSON with these keys:
score: integer 0-100,
summary: one concise paragraph,
strengths: list of 3-5 resume strengths,
gaps: list of 3-7 missing or weak requirements,
recommendations: list of 3-7 specific resume edits.

Resume:
{resume_text[:12000]}

Job description:
{job_text[:12000]}
""".strip()
    response = llm.invoke(prompt)
    return _parse_ai_json(str(response.content))


def _score_color(score: int) -> str:
    if score >= 80:
        return RM_GREEN
    if score >= 60:
        return RM_AMBER
    return RM_RED


def _render_result(result: dict[str, Any]) -> str:
    score = int(result.get("score", 0))
    color = _score_color(score)
    strengths = "".join(f"<li>{escape(str(item))}</li>" for item in result.get("strengths", [])[:5])
    gaps = "".join(f"<li>{escape(str(item))}</li>" for item in result.get("gaps", [])[:7])
    recs = "".join(f"<li>{escape(str(item))}</li>" for item in result.get("recommendations", [])[:7])
    source = "NVIDIA AI analysis" if result.get("source") == "nvidia" else "Local fallback analysis"

    return f"""
    <div class="rm-result">
      <div class="rm-score-card">
        <div class="rm-score-ring" style="--score-color:{color};">
          <span>{score}</span>
          <small>/100</small>
        </div>
        <div>
          <p class="rm-kicker">{source}</p>
          <h3>Resume Match Score</h3>
          <p>{escape(str(result.get("summary", "")))}</p>
        </div>
      </div>
      <div class="rm-grid">
        <section>
          <h4>Strong Matches</h4>
          <ul>{strengths}</ul>
        </section>
        <section>
          <h4>Gaps</h4>
          <ul>{gaps}</ul>
        </section>
        <section>
          <h4>Resume Adjustments</h4>
          <ul>{recs}</ul>
        </section>
      </div>
    </div>
    """


def analyze_resume_match(resume_file: Any, job_description: str, api_key: str = "") -> str:
    resume_text = _extract_text_from_file(resume_file)
    jd_text = (job_description or "").strip()

    if not resume_text.strip():
        return f"<div class='rm-empty'>Upload a readable resume file (.txt, .md, .pdf, or .docx).</div>"
    if not jd_text:
        return f"<div class='rm-empty'>Paste the job description before running the match.</div>"

    try:
        result = _nvidia_match(resume_text, jd_text, api_key=api_key.strip() or None)
    except Exception as exc:
        result = _local_match(resume_text, jd_text)
        result["summary"] = f"NVIDIA analysis failed, so a local keyword match was used. Error: {exc}"
    return _render_result(result)


def render_resume_matcher_tab() -> gr.Blocks:
    with gr.Blocks(elem_id="resume-matcher-tab") as tab:
        with gr.Column(elem_classes=["app-floating-window", "rm-shell"]):
            gr.Markdown(
                """
                <div class="app-window-header">
                    <div>
                        <h1>Resume Match Analyzer</h1>
                        <p>Compare a resume against a job description with NVIDIA-backed AI scoring.</p>
                    </div>
                    <span class="app-window-badge">NVIDIA</span>
                </div>
                """
            )
            with gr.Row():
                with gr.Column(scale=1, min_width=330):
                    resume_input = gr.File(
                        label="Resume",
                        file_types=[".txt", ".md", ".pdf", ".docx"],
                        type="filepath",
                    )
                    api_key_input = gr.Textbox(
                        label="NVIDIA API Key (Optional)",
                        type="password",
                        placeholder="Uses NVIDIA_API_KEY when left blank",
                    )
                    run_btn = gr.Button("Score Resume Match", variant="primary", size="lg")
                with gr.Column(scale=2, min_width=480):
                    jd_input = gr.Textbox(
                        label="Job Description",
                        lines=14,
                        placeholder="Paste the job description here...",
                    )
            output = gr.HTML(
                "<div class='rm-empty'>Upload a resume and paste a job description to see match quality and targeted resume edits.</div>"
            )
            run_btn.click(
                fn=analyze_resume_match,
                inputs=[resume_input, jd_input, api_key_input],
                outputs=[output],
            )
    return tab


RESUME_MATCHER_CSS = """
#resume-matcher-tab {
  max-width: 1380px;
  margin: 18px auto 34px;
}
.rm-shell textarea {
  font-family: inherit !important;
}
.rm-empty {
  border: 1px dashed var(--theme-line, #d9e2ec);
  border-radius: 14px;
  padding: 28px;
  background: var(--theme-surface, #f8fafc);
  color: var(--theme-muted, #667085);
  text-align: center;
}
.rm-result {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}
.rm-score-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 20px;
  align-items: center;
  border: 1px solid var(--theme-line, #d9e2ec);
  border-radius: 14px;
  padding: 20px;
  background: var(--theme-panel, #fff);
  box-shadow: 0 16px 40px var(--theme-shadow, rgba(16,24,40,.08));
}
.rm-score-ring {
  width: 116px;
  height: 116px;
  display: grid;
  place-items: center;
  align-content: center;
  border-radius: 50%;
  border: 10px solid color-mix(in srgb, var(--score-color), transparent 62%);
  color: var(--score-color);
  background: color-mix(in srgb, var(--score-color), transparent 92%);
}
.rm-score-ring span {
  font-size: 38px;
  font-weight: 950;
  line-height: 1;
}
.rm-score-ring small {
  color: var(--theme-muted, #667085);
  font-weight: 800;
}
.rm-kicker {
  margin: 0 0 5px;
  color: var(--theme-blue, #2563eb);
  font-size: 12px;
  font-weight: 850;
  text-transform: uppercase;
}
.rm-score-card h3 {
  margin: 0 0 8px;
  color: var(--theme-ink, #101828);
  font-size: 24px;
}
.rm-score-card p {
  margin: 0;
  color: var(--theme-muted, #667085);
  line-height: 1.55;
}
.rm-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.rm-grid section {
  border: 1px solid var(--theme-line, #d9e2ec);
  border-radius: 14px;
  padding: 18px;
  background: var(--theme-panel, #fff);
  box-shadow: 0 14px 34px var(--theme-shadow, rgba(16,24,40,.08));
}
.rm-grid h4 {
  margin: 0 0 10px;
  color: var(--theme-ink, #101828);
  font-size: 16px;
}
.rm-grid ul {
  margin: 0;
  padding-left: 18px;
  color: var(--theme-muted, #667085);
  line-height: 1.5;
}
.rm-grid li {
  margin-bottom: 7px;
}
@media (max-width: 920px) {
  .rm-score-card,
  .rm-grid {
    grid-template-columns: 1fr;
  }
  .rm-score-ring {
    width: 96px;
    height: 96px;
  }
}
"""
