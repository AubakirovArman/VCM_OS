"""API smoke tests for VCM-OS."""
import tempfile

import httpx

BASE_URL = "http://localhost:8123"


async def api_smoke_tests() -> bool:
    print("\n=== Running API Smoke Tests ===")
    async with httpx.AsyncClient(timeout=60.0) as client:
        ok = True

        # Health
        r = await client.get(f"{BASE_URL}/health")
        assert r.status_code == 200, f"Health failed: {r.text}"
        assert r.json()["version"] == "0.3.0"
        print("✓ Health check")

        # Create session
        r = await client.post(
            f"{BASE_URL}/session/create",
            json={"project_id": "proj_verify", "title": "Verify Session", "branch": "main"},
        )
        assert r.status_code == 200
        sess = r.json()
        session_id = sess["session_id"]
        print(f"✓ Session created: {session_id}")

        # Write events
        events = [
            {
                "project_id": "proj_verify",
                "session_id": session_id,
                "event_type": "user_message",
                "raw_text": "Decision: use PostgreSQL for main DB. Must support replication.",
            },
            {
                "project_id": "proj_verify",
                "session_id": session_id,
                "event_type": "error",
                "raw_text": "ConnectionError: PostgreSQL replica lag exceeds 5s",
                "payload": {"error_kind": "runtime_error"},
            },
            {
                "project_id": "proj_verify",
                "session_id": session_id,
                "event_type": "code_change",
                "raw_text": "Added connection pooling with pgbouncer.",
                "payload": {"file_path": "src/db/pool.py"},
            },
        ]
        for ev in events:
            r = await client.post(f"{BASE_URL}/events", json=ev)
            assert r.status_code == 200
        print("✓ Events written")

        # Read memory
        r = await client.post(
            f"{BASE_URL}/memory/read",
            json={
                "project_id": "proj_verify",
                "session_id": session_id,
                "query": "PostgreSQL replication error",
                "task_type": "debugging",
            },
        )
        assert r.status_code == 200
        mems = r.json()
        assert len(mems) > 0
        print(f"✓ Memory retrieval: {len(mems)} objects")

        # Context build
        r = await client.post(
            f"{BASE_URL}/context/build",
            json={
                "project_id": "proj_verify",
                "session_id": session_id,
                "query": "How do I fix the replication lag?",
                "task_type": "debugging",
                "token_budget": 8000,
                "check_sufficiency": True,
            },
        )
        assert r.status_code == 200
        pack = r.json()
        assert pack["token_estimate"] > 0
        print(f"✓ Context pack: {pack['token_estimate']} tokens")

        # Decisions
        r = await client.get(f"{BASE_URL}/project/proj_verify/decisions")
        assert r.status_code == 200
        decisions = r.json()
        assert len(decisions) > 0
        print(f"✓ Decision ledger: {len(decisions)} decisions")

        # Errors
        r = await client.get(f"{BASE_URL}/project/proj_verify/errors")
        assert r.status_code == 200
        errors = r.json()
        assert len(errors) > 0
        print(f"✓ Error ledger: {len(errors)} errors")

        # Decay
        r = await client.post(f"{BASE_URL}/memory/decay", json={"project_id": "proj_verify"})
        assert r.status_code == 200
        print("✓ Decay engine ran")

        # Stale check
        with tempfile.TemporaryDirectory() as tmpdir:
            r = await client.post(
                f"{BASE_URL}/memory/stale",
                json={"project_id": "proj_verify", "workspace_root": tmpdir},
            )
            assert r.status_code == 200
            print("✓ Stale check ran")

        # Graph expand
        if mems:
            r = await client.post(
                f"{BASE_URL}/memory/graph/expand",
                json={"memory_ids": [mems[0]["memory_id"]], "max_hops": 2},
            )
            assert r.status_code == 200
            print("✓ Graph expansion")

        # Query rewrite
        r = await client.post(
            f"{BASE_URL}/query/rewrite",
            json={"query": "fix replication lag", "task_type": "debugging"},
        )
        assert r.status_code == 200
        print("✓ Query rewrite")

        # Session restore
        r = await client.post(
            f"{BASE_URL}/session/{session_id}/restore",
            params={"query": "continue debugging replication"},
        )
        assert r.status_code == 200
        print("✓ Session restore")

        # Verifier
        r = await client.post(
            f"{BASE_URL}/verify",
            json={
                "query": "Which DB should we use?",
                "answer": "We should use MySQL instead of PostgreSQL.",
                "project_id": "proj_verify",
                "session_id": session_id,
                "use_llm": False,
            },
        )
        assert r.status_code == 200
        verdict = r.json()
        print(f"✓ Verifier: consistent={verdict.get('consistent')}, score={verdict.get('score'):.2f}")

        # Codebase index (index our own code)
        r = await client.post(
            f"{BASE_URL}/codebase/index",
            json={"project_id": "proj_verify", "directory": "./vcm_os"},
        )
        assert r.status_code == 200
        idx_result = r.json()
        assert idx_result["symbols_found"] > 0
        print(f"✓ Codebase index: {idx_result['symbols_found']} symbols")

        # Symbol search
        r = await client.post(
            f"{BASE_URL}/codebase/symbols/search",
            json={"name": "MemoryWriter"},
        )
        assert r.status_code == 200
        print("✓ Symbol search")

        return ok
