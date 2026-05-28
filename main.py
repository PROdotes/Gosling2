import sys
import uvicorn

if __name__ == "__main__":
    frozen = getattr(sys, "frozen", False)
    if frozen:
        from src.engine_server import app

        uvicorn.run(app, host="127.0.0.1", port=8000)
    else:
        uvicorn.run(
            "src.engine_server:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            reload_dirs=["src"],
        )
