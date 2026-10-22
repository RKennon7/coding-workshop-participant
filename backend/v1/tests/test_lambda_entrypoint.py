# function.handler: only a direct `aws lambda invoke` may run the database init, never an HTTP request
import asyncio
import json

import pytest

import function
import scripts.init_db


@pytest.fixture
def calls(monkeypatch):
    seen = {"http": 0, "init": []}

    def fake_http(event, context):
        seen["http"] += 1
        return {"statusCode": 200}

    async def fake_init(sample_data, seed_password):
        seen["init"].append((sample_data, seed_password))
        return {"ok": True}

    monkeypatch.setattr(function, "http_handler", fake_http)
    monkeypatch.setattr(scripts.init_db, "init_db", fake_init)
    return seen

@pytest.mark.parametrize("event", [
    {"body": json.dumps({"action": "init_db"}), "requestContext": {"http": {"method": "POST"}}},
    {"queryStringParameters": {"action": "init_db"}, "requestContext": {}},
    {"headers": {"action": "init_db"}, "requestContext": {}},
])
def test_http_requests_cannot_trigger_database_init(calls, event):
    function.handler(event, None)
    assert calls == {"http": 1, "init": []}

def test_direct_invoke_runs_database_init(calls, monkeypatch):
    loop = asyncio.new_event_loop()
    monkeypatch.setattr(function.asyncio, "get_event_loop", lambda: loop)
    try:
        assert function.handler({"action": "init_db", "sample_data": False, "seed_password": "pw"}, None) == {"ok": True}
    finally:
        loop.close()
    assert calls == {"http": 0, "init": [(False, "pw")]}
