---
title: AI Portfolio
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 5.23.0
app_file: app_deploy.py
pinned: false
python_version: "3.12"
---

# AI Project Portfolio

Python-based portfolio landing page for public AI project tiles. The live local app is built with Gradio, and the same project data can be exported as static HTML for Vercel.

## Tabs

- **Portfolio** — Landing page with project tiles and floating-window UI
- **Portfolio Manager** — Multi-agent portfolio decisions
- **Insurance Underwriting** — Agentic underwriting assistant
- **Claim Processing** — Insurance claim automation pipeline
- **Movie Recommendations** — Embeddings, collaborative filtering, and preference parsing
- **Sentiment Analyzer** — Local business review sentiment analysis
- **Financial Agent** — Multi-agent stock and portfolio analysis
- **Trading Desk** — Options workflow with hoverable agent pipeline traces, human-in-the-loop paper execution, and simulated account tracking

## Run Locally

```powershell
cd C:\projects\ai-portfolio
uv sync
uv run python app.py
```

Or use the service helper:

```powershell
.\start.bat start
```

## Configure the Site

Edit `portfolio.yaml` to change the app port, public text, LinkedIn URL, stats, tab labels, and Project Index titles/descriptions.

```yaml
server:
  host: 127.0.0.1
  port: 7860
```

`start.bat`, the Gradio app, and the static exporter read from this file.

## Export for Vercel

```powershell
uv run python scripts\export_static.py
```

Deploy the generated `dist` folder with Vercel. The lightweight FastAPI entrypoint remains in `api/index.py`.
