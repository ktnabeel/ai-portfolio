from .models import Project


PROJECT_TEMPLATES = [
    Project(
        title="TradingAgents Manager",
        outcome="Multi-agent portfolio manager powered by LangGraph — FastAPI service orchestrating Security, Sentiment, Regime, Decision, and Execution agents for market analysis.",
        tech_stack="Python, FastAPI, LangGraph, yfinance, Pydantic",
        status="Built",
        tags=("Agents", "Finance", "FastAPI", "LangGraph"),
    ),
    Project(
        title="Trading Agents",
        outcome="Multi-agent trading research workflow for market analysis and decision support.",
        tech_stack="Python, LLM agents, financial data",
        status="Built",
        tags=("Agents", "Finance", "Research"),
    ),
    Project(
        title="Claim Processing",
        outcome="AI-assisted workflow for reviewing claims, extracting details, and routing decisions.",
        tech_stack="Python, document AI, workflow automation",
        status="Built",
        tags=("Insurance", "Automation", "Documents"),
    ),
    Project(
        title="Insurance Underwriting Agent",
        outcome="Agentic underwriting assistant for risk review, policy context, and recommendation support.",
        tech_stack="Python, LLM agents, underwriting rules",
        status="Template",
        tags=("Insurance", "Agents", "Risk"),
    ),
    Project(
        title="Product Review Sentiment Analyzer",
        outcome="Sentiment analysis app for summarizing customer reviews and product feedback patterns.",
        tech_stack="Python, NLP, sentiment analysis",
        status="Built",
        tags=("NLP", "Sentiment", "Analytics"),
    ),
    Project(
        title="Finance Planning",
        outcome="AI planning assistant for budgeting, scenario analysis, and financial goal tracking.",
        tech_stack="Python, analytics, LLM workflows",
        status="Built",
        tags=("Finance", "Planning", "Assistant"),
    ),
    Project(
        title="Movie Recommendations",
        outcome="AI-powered movie recommender combining two-tower embeddings, SVD collaborative filtering, and LLM-style preference extraction from TMDB data.",
        tech_stack="Python, scikit-learn, TMDB API, Gradio",
        status="Built",
        tags=("Recommendations", "ML", "NLP"),
    ),
]

