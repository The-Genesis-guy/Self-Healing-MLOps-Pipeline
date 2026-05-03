"""Module entrypoint to run the FastAPI app via: `python -m api`.

This uses Uvicorn to serve the ASGI app defined in `api.main:app`.
"""
from __future__ import annotations

import uvicorn


def main() -> None:
    """Run the API using Uvicorn."""
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
