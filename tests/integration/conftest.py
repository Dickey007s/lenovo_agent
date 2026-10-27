import asyncio
import sys

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    # Targeted PostgreSQL gates must not depend on another test module's import order.
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()
