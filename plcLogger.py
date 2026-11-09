import json
import sqlite3
import time
from datetime import datetime, timezone

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

PLC_HOST = "192.168.1.10"
PLC_PORT = 502
UNIT_ID = 1
START_ADDRESS = 0
REGISTER_COUNT = 10
POLL_SECONDS = 5
RECONNECT_SECONDS = 5
DATABASE = "plc_data.sqlite3"


def init_db(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            start_address INTEGER NOT NULL,
            registers_json TEXT NOT NULL
        )
    """)
    db.commit()


def poll_once(client, db):
    """Read the registers once and store them. Returns the registers.

    Raises ConnectionError if the read fails, so the caller can reconnect.
    """
    try:
        result = client.read_holding_registers(
            address=START_ADDRESS,
            count=REGISTER_COUNT,
            device_id=UNIT_ID,  # pymodbus >= 3.10 (was slave= / unit= in older versions)
        )
    except (ModbusException, OSError) as exc:
        raise ConnectionError(f"Modbus read failed: {exc}") from exc

    if result.isError():
        raise ConnectionError(f"Modbus read error: {result}")

    timestamp = datetime.now(timezone.utc).isoformat()
    registers = list(result.registers)
    db.execute(
        "INSERT INTO readings (timestamp, start_address, registers_json) "
        "VALUES (?, ?, ?)",
        (timestamp, START_ADDRESS, json.dumps(registers)),
    )
    db.commit()
    print(timestamp, registers)
    return registers


def main():
    with sqlite3.connect(DATABASE) as db:
        init_db(db)
        client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)
        print(f"Logging PLC registers to {DATABASE}. Press Ctrl+C to stop.")
        try:
            while True:
                if not client.connected and not client.connect():
                    print(f"Could not connect to PLC at {PLC_HOST}:{PLC_PORT}; "
                          f"retrying in {RECONNECT_SECONDS}s")
                    time.sleep(RECONNECT_SECONDS)
                    continue
                try:
                    poll_once(client, db)
                except ConnectionError as exc:
                    print(f"{exc}; reconnecting in {RECONNECT_SECONDS}s")
                    client.close()
                    time.sleep(RECONNECT_SECONDS)
                    continue
                time.sleep(POLL_SECONDS)
        finally:
            client.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
