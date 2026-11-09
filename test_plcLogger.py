import json
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import plcLogger


class FakeResult:
    def __init__(self, registers=None, error=False):
        self.registers = registers or []
        self._error = error

    def isError(self):
        return self._error


class FakeClient:
    def __init__(self, result):
        self.result = result
        self.kwargs = None

    def read_holding_registers(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    plcLogger.init_db(conn)
    yield conn
    conn.close()


def test_poll_stores_reading(db):
    client = FakeClient(FakeResult(list(range(10))))
    plcLogger.poll_once(client, db)
    rows = db.execute("SELECT start_address, registers_json FROM readings").fetchall()
    assert rows == [(plcLogger.START_ADDRESS, json.dumps(list(range(10))))]


def test_poll_uses_device_id_keyword(db):
    client = FakeClient(FakeResult([1] * 10))
    plcLogger.poll_once(client, db)
    assert client.kwargs["device_id"] == plcLogger.UNIT_ID
    assert "unit" not in client.kwargs


def test_modbus_error_raises_and_stores_nothing(db):
    with pytest.raises(ConnectionError):
        plcLogger.poll_once(FakeClient(FakeResult(error=True)), db)
    assert db.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 0


def test_socket_error_raises_connection_error(db):
    with pytest.raises(ConnectionError):
        plcLogger.poll_once(FakeClient(OSError("boom")), db)
