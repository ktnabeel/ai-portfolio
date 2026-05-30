"""Lean Trading Agent deployment entrypoint."""

from __future__ import annotations

import os

from portfolio.trading.deploy import build_gradio_app, create_fastapi_app, runtime_mode


demo = build_gradio_app()
app = create_fastapi_app()


def main() -> None:
    mode = runtime_mode()
    if mode == "fastapi":
        import uvicorn

        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        uvicorn.run(app, host=host, port=port, log_level="info")
        return

    demo.launch(
        server_name=os.getenv("HOST", "0.0.0.0"),
        server_port=int(os.getenv("PORT", "7860")),
        show_api=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
