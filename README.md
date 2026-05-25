---
title: AI Portfolio
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 5.23.0
app_file: app.py
pinned: false
python_version: "3.10"
---

# AI Project Portfolio

Python-based portfolio landing page for public AI project tiles. The live app is built with Gradio for Hugging Face Spaces, and the same project data can be exported as static HTML for Vercel.

## Tabs

- **Portfolio** — Landing page with project tiles, capability strip, glassmorphism UI
- **Financial Agent** — Multi-agent portfolio decisions (Market Data, Technical, Fundamental, Sentiment, Risk, Orchestrator)
- **Claim Processing** — Insurance claim automation pipeline
- **Movie Recommendations** — Two-tower embeddings + SVD collaborative filtering + LLM-style preference parsing (TMDB)
- **Sentiment Analyzer** — Product-review sentiment analysis on Amazon reviews
- **Trading** — Multi-agent options trading via LangGraph + MCP paper-trading server + Black-Scholes pricing

## Run Locally

```powershell
cd C:\projects\ai-portfolio
uv sync
uv run python app.py
```

## Configure the Site

Edit `portfolio.yaml` to change the app port, public text, LinkedIn URL, stats, and capability labels.

```yaml
server:
  host: 127.0.0.1
  port: 7860
```

`start.bat`, the Gradio app, and the static exporter all read from this file.

## Add a Real Project

Seed the six starter project templates:

```powershell
uv run python scripts\seed_templates.py
uv run python scripts\export_static.py
```

```powershell
uv run python scripts\add_project.py `
  --title "Trading Agents Research App" `
  --outcome "Runs multi-agent stock analysis with OpenAI chat models." `
  --tech-stack "Python, OpenAI, LangGraph" `
  --status "Built" `
  --tags "Agents, Finance, OpenAI" `
  --github-url "https://github.com/your-name/your-repo" `
  --demo-url "https://your-demo-url"
```

## Export for Vercel

```powershell
uv run python scripts\export_static.py
```

Deploy the generated `dist` folder with Vercel. The included `vercel.json` points Vercel at `dist`.

## Deploy to Hugging Face Spaces

Create a Space using the Gradio SDK, then include:

- `app.py`
- `requirements.txt`
- `portfolio/`
- `portfolio.db` if you want the Space to ship with existing projects

If `portfolio.db` is not present, the app starts with the empty state.
