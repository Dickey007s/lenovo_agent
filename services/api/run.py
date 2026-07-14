import asyncio
import os
import sys

import uvicorn


def main() -> None:
    # psycopg async connections require a selector loop on Windows. This must
    # happen before uvicorn creates its event loop, not during FastAPI import.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run(
        "services.api.app.main:app",
        host="127.0.0.1",
        port=int(os.getenv("API_PORT", "8010")),
        reload=False,
        loop="services.api.selector_loop:selector_loop_factory",
    )


if __name__ == "__main__":
    main()
