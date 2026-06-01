from __future__ import annotations

import os
import sys
import types
from typing import Any

from portfolio.trading._llm import PROVIDER_MODELS, get_default_model
from portfolio.trading.graph.trading_graph import _is_deterministic_mode, _make_llm
from portfolio.trading.ui.trading_ui import _is_deterministic as ui_is_deterministic
from portfolio.trading_agents_manager.models import AnalysisRequest
from portfolio.trading_agents_manager.render import _run_analysis as manager_run_analysis
from portfolio.trading_agents_manager.manager import PortfolioManager


def test_nvidia_provider_registry_and_default() -> None:
    assert "nvidia" in PROVIDER_MODELS
    assert len(PROVIDER_MODELS["nvidia"]) == 3
    assert get_default_model("nvidia") == "nvidia/llama-3.1-nemotron-70b-instruct"


def test_graph_uses_nvidia_env_for_deterministic_resolution(monkeypatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    state = {"llm_provider": "nvidia", "openai_api_key": ""}
    assert _is_deterministic_mode(state) is True
    monkeypatch.setenv("NVIDIA_API_KEY", "x-key")
    assert _is_deterministic_mode(state) is False


def test_graph_make_llm_none_without_key_and_calls_factory_with_key(monkeypatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    state = {"llm_provider": "nvidia", "llm_model": "", "openai_api_key": ""}
    assert _make_llm(state) is None

    captured: dict[str, Any] = {}

    def _fake_create_llm(provider: str, model: str | None, api_key: str | None):
        captured["provider"] = provider
        captured["model"] = model
        captured["api_key"] = api_key
        return object()

    monkeypatch.setattr("portfolio.trading.graph.trading_graph.create_llm", _fake_create_llm)
    monkeypatch.setenv("NVIDIA_API_KEY", "session-key")
    llm = _make_llm(state)
    assert llm is not None
    assert captured["provider"] == "nvidia"
    assert captured["api_key"] == "session-key"


def test_ui_deterministic_checks_nvidia_env(monkeypatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    assert ui_is_deterministic("", "nvidia") is True
    monkeypatch.setenv("NVIDIA_API_KEY", "x")
    assert ui_is_deterministic("", "nvidia") is False


def test_analysis_request_accepts_provider_model_key() -> None:
    req = AnalysisRequest(symbol="NVDA", llm_provider="nvidia", llm_model="meta/llama", api_key="secret")
    assert req.llm_provider == "nvidia"
    assert req.llm_model == "meta/llama"
    assert req.api_key == "secret"


def test_manager_render_passes_provider_model_key(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class _Result:
        decision = None
        agent_cards = []
        execution_log = []

    def _fake_analyze(symbol: str, **kwargs):
        captured["symbol"] = symbol
        captured.update(kwargs)
        return _Result()

    monkeypatch.setattr("portfolio.trading_agents_manager.render._manager.analyze", _fake_analyze)
    manager_run_analysis("NVDA", "nvidia", "model-id", " raw-key ")
    assert captured["symbol"] == "NVDA"
    assert captured["llm_provider"] == "nvidia"
    assert captured["llm_model"] == "model-id"
    assert captured["api_key"] == "raw-key"


def test_manager_direct_arg_path(monkeypatch) -> None:
    class GraphDirect:
        called_kwargs = None

        def propagate(self, symbol: str, date: str, llm_provider: str, llm_model: str, api_key: str):
            GraphDirect.called_kwargs = {
                "symbol": symbol,
                "date": date,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "api_key": api_key,
            }
            return {}

    mod = types.ModuleType("tradingagents.graph")
    mod.TradingAgentsGraph = GraphDirect
    pkg = types.ModuleType("tradingagents")
    monkeypatch.setitem(sys.modules, "tradingagents", pkg)
    monkeypatch.setitem(sys.modules, "tradingagents.graph", mod)

    pm = PortfolioManager()
    pm.analyze("NVDA", llm_provider="nvidia", llm_model="m1", api_key="k1")
    assert GraphDirect.called_kwargs["llm_provider"] == "nvidia"
    assert GraphDirect.called_kwargs["llm_model"] == "m1"
    assert GraphDirect.called_kwargs["api_key"] == "k1"


def test_manager_env_overlay_fallback_and_restore(monkeypatch) -> None:
    class GraphLegacy:
        saw_env = ""

        def propagate(self, symbol: str, date: str):
            GraphLegacy.saw_env = os.environ.get("NVIDIA_API_KEY", "")
            return {}

    mod = types.ModuleType("tradingagents.graph")
    mod.TradingAgentsGraph = GraphLegacy
    pkg = types.ModuleType("tradingagents")
    monkeypatch.setitem(sys.modules, "tradingagents", pkg)
    monkeypatch.setitem(sys.modules, "tradingagents.graph", mod)

    monkeypatch.setenv("NVIDIA_API_KEY", "original-env")
    pm = PortfolioManager()
    pm.analyze("NVDA", llm_provider="nvidia", llm_model="m1", api_key="temp-session")
    assert GraphLegacy.saw_env == "temp-session"
    assert os.environ.get("NVIDIA_API_KEY") == "original-env"
