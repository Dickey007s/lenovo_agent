import asyncio


def selector_loop_factory() -> asyncio.AbstractEventLoop:
    """Always use SelectorEventLoop so psycopg async works on Windows."""
    return asyncio.SelectorEventLoop()
