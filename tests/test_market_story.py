"""Unit tests for the shared live market-story helpers."""

from __future__ import annotations

import json

import market_story


class _FakeHeaders:
    def get_content_charset(self) -> str:
        return "utf-8"


class _FakeResponse:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")
        self.headers = _FakeHeaders()

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_sentiment_parsing_and_technical_breakout(monkeypatch) -> None:
    cnn_html = """
    <html>
      <body>
        <div>Fear &amp; Greed Index 67 Greed</div>
        <div>Previous close 64</div>
        <div>1 week ago 60</div>
        <div>1 month ago 58</div>
        <div>1 year ago 45</div>
      </body>
    </html>
    """
    chart_json = json.dumps(
        {
            "chart": {
                "result": [
                    {
                        "timestamp": list(range(60)),
                        "indicators": {
                            "quote": [
                                {
                                    "close": [
                                        170.0,
                                        171.0,
                                        172.0,
                                        173.0,
                                        174.0,
                                        175.0,
                                        176.0,
                                        177.0,
                                        178.0,
                                        179.0,
                                        180.0,
                                        181.0,
                                        182.0,
                                        183.0,
                                        184.0,
                                        185.0,
                                        186.0,
                                        187.0,
                                        188.0,
                                        189.0,
                                        190.0,
                                        191.0,
                                        192.0,
                                        193.0,
                                        194.0,
                                        195.0,
                                        196.0,
                                        197.0,
                                        198.0,
                                        199.0,
                                        200.0,
                                        201.0,
                                        202.0,
                                        203.0,
                                        204.0,
                                        205.0,
                                        206.0,
                                        207.0,
                                        208.0,
                                        209.0,
                                        210.0,
                                        211.0,
                                        212.0,
                                        213.0,
                                        214.0,
                                        215.0,
                                        216.0,
                                        217.0,
                                        218.0,
                                        219.0,
                                        220.0,
                                        221.0,
                                        222.0,
                                        223.0,
                                        224.0,
                                        225.0,
                                        226.0,
                                        227.0,
                                        228.0,
                                        229.0,
                                    ],
                                    "volume": [1_000_000.0] * 59 + [1_400_000.0],
                                }
                            ]
                        },
                    }
                ]
            }
        }
    )

    payloads = [cnn_html, chart_json]

    def fake_urlopen(request, timeout=12):  # noqa: ANN001
        return _FakeResponse(payloads.pop(0))

    monkeypatch.setattr(market_story, "urlopen", fake_urlopen)

    sentiment = market_story.fetch_sentiment_snapshot()
    technical = market_story.fetch_technical_snapshot("AAPL")
    decision = market_story.build_security_decision("AAPL", sentiment, technical)

    assert sentiment.value == 67
    assert sentiment.zone == "Greed"
    assert technical.signal == "Bullish breakout"
    assert technical.bullish_stack is True
    assert decision.side == "BUY"
    assert "EMA 8 and EMA 21" in decision.rationale
    assert "20-day high" in decision.rationale
