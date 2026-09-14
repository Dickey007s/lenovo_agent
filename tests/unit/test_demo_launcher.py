from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]
START_DEMO = REPOSITORY_ROOT / "scripts" / "start-demo.ps1"


def test_memory_fallback_overrides_a_stale_dotenv_database_dsn() -> None:
    script = START_DEMO.read_text(encoding="utf-8")

    configured_index = script.index("if ($UseConfiguredPostgres)")
    memory_index = script.index('$env:STATE_STORE_MODE = "memory"', configured_index)
    warning_index = script.index("this session will use process-local memory", memory_index)

    assert configured_index < memory_index < warning_index
    assert script.count('$env:STATE_STORE_MODE = "memory"') == 1
    assert '$env:DATABASE_DSN = ""' not in script
