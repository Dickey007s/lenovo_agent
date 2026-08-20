from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

import httpx
import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo


ADMIN_DSN_ENV = "OFFICE_AGENT_POSTGRES_ADMIN_DSN"
OWNER_HEADERS = {"X-User-Id": "postgres_restart_user"}
OFFICIAL_SOURCE = "fixture:crm/customer-a:official-revenue-v3"
ROUND_ONE_KEY = "system-demo-round-001"
ROUND_TWO_KEY = "system-demo-round-002"
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ApiProcess:
    process: subprocess.Popen[bytes]
    port: int
    stdout_path: Path
    stderr_path: Path
    stdout_handle: BinaryIO
    stderr_handle: BinaryIO

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        self.stdout_handle.close()
        self.stderr_handle.close()

    def diagnostics(self) -> str:
        chunks = []
        for label, path in (("stdout", self.stdout_path), ("stderr", self.stderr_path)):
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="replace")
                chunks.append(f"{label}:\n{text[-4000:]}")
        return "\n".join(chunks)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _database_dsn(admin_dsn: str, database_name: str) -> str:
    params = conninfo_to_dict(admin_dsn)
    params["dbname"] = database_name
    return make_conninfo(**params)


@pytest.fixture
def isolated_postgres_database() -> Iterator[str]:
    admin_dsn = os.getenv(ADMIN_DSN_ENV, "").strip()
    if not admin_dsn:
        pytest.skip(
            f"set {ADMIN_DSN_ENV} to a PostgreSQL 16 maintenance database to run this test"
        )

    database_name = f"oa_restart_{uuid4().hex[:16]}"
    created = False
    try:
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            server_version = connection.info.server_version
            assert 160000 <= server_version < 170000, (
                f"PostgreSQL 16 is required, server_version={server_version}"
            )
            connection.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
            )
            created = True
        yield _database_dsn(admin_dsn, database_name)
    finally:
        if created:
            with psycopg.connect(admin_dsn, autocommit=True) as connection:
                connection.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                        sql.Identifier(database_name)
                    )
                )


def _start_api(database_dsn: str, tmp_path: Path, label: str) -> ApiProcess:
    port = _free_port()
    stdout_path = tmp_path / f"api-{label}.stdout.log"
    stderr_path = tmp_path / f"api-{label}.stderr.log"
    stdout_handle = stdout_path.open("wb")
    stderr_handle = stderr_path.open("wb")
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "system-test",
            "API_PORT": str(port),
            "DATABASE_DSN": database_dsn,
            "LANGGRAPH_CHECKPOINT_DSN": "",
            "LLM_BASE_URL": "",
            "LLM_API_KEY": "",
            "PERMIT_PRIVATE_KEY_PATH": "",
            "PERMIT_PUBLIC_KEY_PATH": "",
            "PYTHONUNBUFFERED": "1",
        }
    )
    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "services.api.run"],
            cwd=REPO_ROOT,
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=creation_flags,
        )
    except Exception:
        stdout_handle.close()
        stderr_handle.close()
        raise
    api = ApiProcess(
        process=process,
        port=port,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        stdout_handle=stdout_handle,
        stderr_handle=stderr_handle,
    )
    try:
        _wait_for_api(api)
    except Exception:
        api.stop()
        raise AssertionError(f"API {label} failed to start\n{api.diagnostics()}") from None
    return api


def _wait_for_api(api: ApiProcess) -> None:
    deadline = time.monotonic() + 45
    last_error = "health endpoint did not respond"
    while time.monotonic() < deadline:
        if api.process.poll() is not None:
            raise RuntimeError(f"API exited with code {api.process.returncode}")
        try:
            response = httpx.get(f"{api.base_url}/v1/health", timeout=1)
            if response.status_code == 200:
                health = response.json()
                assert health["status"] == "ok"
                assert health["task_store"] == "postgres"
                assert health["checkpoint"] == "memory"
                return
            last_error = f"health returned {response.status_code}: {response.text}"
        except (httpx.HTTPError, ValueError, AssertionError) as exc:
            last_error = str(exc)
        time.sleep(0.2)
    raise TimeoutError(last_error)


@contextmanager
def _running_api(
    database_dsn: str, tmp_path: Path, label: str
) -> Iterator[ApiProcess]:
    api = _start_api(database_dsn, tmp_path, label)
    try:
        yield api
    finally:
        api.stop()


def _response_json(response: httpx.Response, expected_status: int = 200) -> dict:
    assert response.status_code == expected_status, (
        f"{response.request.method} {response.request.url} returned "
        f"{response.status_code}: {response.text}"
    )
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


def _advance_until_waiting(client: httpx.Client, task: dict) -> dict:
    snapshot = task
    for index in range(4):
        snapshot = _response_json(
            client.post(
                f"/v1/tasks/{task['task_id']}/advance",
                json={
                    "expected_task_version": snapshot["version"],
                    "idempotency_key": f"system-advance-{index:03d}",
                },
            )
        )
    return snapshot


def _database_counts(database_dsn: str, task_id: str) -> tuple[int, int, int, int, int, int]:
    with psycopg.connect(database_dsn) as connection:
        row = connection.execute(
            """
            SELECT
                (SELECT count(*) FROM agent_tasks WHERE task_id = %s),
                (SELECT count(*) FROM agent_task_events WHERE task_id = %s),
                (SELECT count(*) FROM agent_task_artifact_versions WHERE task_id = %s),
                (SELECT count(*) FROM agent_task_events
                    WHERE task_id = %s AND idempotency_key = 'system-start-001'),
                (SELECT count(*) FROM agent_task_events
                    WHERE task_id = %s AND idempotency_key = 'system-resolve-001'),
                (SELECT count(*) FROM agent_task_events
                    WHERE task_id = %s AND event_type = 'TASK_COMMITTED')
            """,
            (task_id, task_id, task_id, task_id, task_id, task_id),
        ).fetchone()
    assert row is not None
    return tuple(int(item) for item in row)


def test_postgres_task_survives_api_restart_and_replays_original_mutation(
    isolated_postgres_database: str,
    tmp_path: Path,
) -> None:
    database_dsn = isolated_postgres_database

    with _running_api(database_dsn, tmp_path, "a") as api_a:
        api_a_pid = api_a.process.pid
        with httpx.Client(
            base_url=api_a.base_url,
            headers=OWNER_HEADERS,
            timeout=15,
        ) as client:
            created = _response_json(
                client.post(
                    "/v1/demo1/tasks",
                    headers={"Idempotency-Key": ROUND_ONE_KEY},
                ),
                201,
            )
            initial_started = _response_json(
                client.post(
                    f"/v1/tasks/{created['task_id']}/start",
                    json={
                        "expected_task_version": created["version"],
                        "idempotency_key": "system-start-001",
                    },
                )
            )
            started = _advance_until_waiting(client, initial_started)

        assert initial_started["status"] == "running"
        assert initial_started["phase"] == "observe"
        assert started["status"] == "waiting_input"
        assert started["phase"] == "verify"
        assert started["version"] == 6
        assert len(started["branches"]) == 3
        assert len(started["artifact_versions"]) == 5
        waiting_branch = next(
            branch for branch in started["branches"] if branch["status"] == "waiting_evidence"
        )
        branch_heads = {
            branch["branch_id"]: branch["artifact_heads"] for branch in started["branches"]
        }
        assert _database_counts(database_dsn, started["task_id"]) == (
            1,
            started["last_event_sequence"],
            5,
            1,
            0,
            0,
        )

    assert api_a.process.returncode is not None

    with _running_api(database_dsn, tmp_path, "b") as api_b:
        api_b_pid = api_b.process.pid
        with httpx.Client(
            base_url=api_b.base_url,
            headers=OWNER_HEADERS,
            timeout=15,
        ) as client:
            replayed_round_one = _response_json(
                client.post(
                    "/v1/demo1/tasks",
                    headers={"Idempotency-Key": ROUND_ONE_KEY},
                ),
                201,
            )
            round_two = _response_json(
                client.post(
                    "/v1/demo1/tasks",
                    headers={"Idempotency-Key": ROUND_TWO_KEY},
                ),
                201,
            )
            restored = _response_json(client.get(f"/v1/tasks/{started['task_id']}"))
            listed_response = client.get("/v1/tasks")
            assert listed_response.status_code == 200
            listed = listed_response.json()

            assert replayed_round_one == started
            assert round_two["task_id"] != started["task_id"]
            assert round_two["status"] == "ready"
            assert round_two["version"] == 1
            assert restored == started
            assert {item["task_id"] for item in listed} == {
                started["task_id"],
                round_two["task_id"],
            }
            assert {
                branch["branch_id"]: branch["artifact_heads"]
                for branch in restored["branches"]
            } == branch_heads

            committed = _response_json(
                client.post(
                    f"/v1/tasks/{started['task_id']}/controls",
                    json={
                        "kind": "resolve_evidence",
                        "branch_id": waiting_branch["branch_id"],
                        "resolution_option_id": "use-official-crm-revenue",
                        "selected_source_ref": OFFICIAL_SOURCE,
                        "expected_task_version": started["version"],
                        "idempotency_key": "system-resolve-001",
                    },
                )
            )
            assert committed["status"] == "committed"
            assert committed["phase"] == "commit"
            assert committed["version"] == 7
            assert committed["last_event_sequence"] > started["last_event_sequence"]
            assert len(committed["artifact_versions"]) == 7
            assert committed["last_commit"]["state_hash"].startswith("sha256:")

            counts_before_replay = _database_counts(database_dsn, started["task_id"])
            assert counts_before_replay == (
                1,
                committed["last_event_sequence"],
                7,
                1,
                1,
                1,
            )

    assert api_b.process.returncode is not None

    with _running_api(database_dsn, tmp_path, "c") as api_c:
        api_c_pid = api_c.process.pid
        with httpx.Client(
            base_url=api_c.base_url,
            headers=OWNER_HEADERS,
            timeout=15,
        ) as client:
            restored_committed = _response_json(
                client.get(f"/v1/tasks/{started['task_id']}")
            )
            restored_round_two = _response_json(
                client.get(f"/v1/tasks/{round_two['task_id']}")
            )
            committed_list_response = client.get("/v1/tasks")
            assert committed_list_response.status_code == 200
            committed_list = committed_list_response.json()

            assert restored_committed == committed
            assert restored_round_two == round_two
            assert {
                item["task_id"]: item for item in committed_list
            } == {
                committed["task_id"]: committed,
                round_two["task_id"]: round_two,
            }

            replayed_round_one = _response_json(
                client.post(
                    "/v1/demo1/tasks",
                    headers={"Idempotency-Key": ROUND_ONE_KEY},
                ),
                201,
            )
            replayed_round_two = _response_json(
                client.post(
                    "/v1/demo1/tasks",
                    headers={"Idempotency-Key": ROUND_TWO_KEY},
                ),
                201,
            )

            replayed_start = _response_json(
                client.post(
                    f"/v1/tasks/{started['task_id']}/start",
                    json={
                        "expected_task_version": created["version"],
                        "idempotency_key": "system-start-001",
                    },
                )
            )
            replayed_resolve = _response_json(
                client.post(
                    f"/v1/tasks/{started['task_id']}/controls",
                    json={
                        "kind": "resolve_evidence",
                        "branch_id": waiting_branch["branch_id"],
                        "resolution_option_id": "use-official-crm-revenue",
                        "selected_source_ref": OFFICIAL_SOURCE,
                        "expected_task_version": started["version"],
                        "idempotency_key": "system-resolve-001",
                    },
                )
            )
            latest = _response_json(client.get(f"/v1/tasks/{started['task_id']}"))

        assert replayed_round_one == committed
        assert replayed_round_two == round_two
        assert replayed_start == initial_started
        assert replayed_resolve == committed
        assert latest == committed
        assert _database_counts(database_dsn, started["task_id"]) == counts_before_replay
        assert _database_counts(database_dsn, round_two["task_id"]) == (
            1,
            1,
            0,
            0,
            0,
            0,
        )

    assert api_c.process.returncode is not None

    with psycopg.connect(database_dsn) as connection:
        postgres_version = connection.info.server_version
        owner_task_rows = connection.execute(
            "SELECT count(*) FROM agent_tasks WHERE owner_id = %s",
            (OWNER_HEADERS["X-User-Id"],),
        ).fetchone()
    assert owner_task_rows is not None
    assert int(owner_task_rows[0]) == 2
    print(
        json.dumps(
            {
                "api_a_pid": api_a_pid,
                "api_b_pid": api_b_pid,
                "api_c_pid": api_c_pid,
                "artifact_rows": counts_before_replay[2],
                "commit_rows": counts_before_replay[5],
                "event_rows": counts_before_replay[1],
                "postgres_server_version": postgres_version,
                "round_one_replay_task_id": replayed_round_one["task_id"],
                "round_two_task_id": replayed_round_two["task_id"],
                "round_task_rows": int(owner_task_rows[0]),
                "state_hash": committed["last_commit"]["state_hash"],
                "status": committed["status"],
                "task_id": committed["task_id"],
                "task_version": committed["version"],
            },
            sort_keys=True,
        )
    )
