import json
import sqlite3
import time
from datetime import datetime, timezone

from pymodbus.client import ModbusTcpClient

PLC_HOST = "192.168.1.10"
PLC_PORT = 502
UNIT_ID = 1
START_ADDRESS = 0
REGISTER_COUNT = 10
POLL_SECONDS = 5
DATABASE = "plc_data.sqlite3"

def main():
    with sqlite3.connect(DATABASE) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                start_address INTEGER NOT NULL,
                registers_json TEXT NOT NULL
            )
        """)

        client = ModbusTcpClient(PLC_HOST, port=PLC_PORT)
        try:
            if not client.connect():
                raise ConnectionError(f"Could not connect to PLC at {PLC_HOST}:{PLC_PORT}")

            print(f"Logging PLC registers to {DATABASE}. Press Ctrl+C to stop.")
            while True:
                result = client.read_holding_registers(
                    address=START_ADDRESS,
                    count=REGISTER_COUNT,
                    unit=UNIT_ID,
                )

                if result.isError():
                    print(f"Modbus read error: {result}")
                else:
                    timestamp = datetime.now(timezone.utc).isoformat()
                    registers = result.registers
                    db.execute(
                        "INSERT INTO readings (timestamp, start_address, registers_json) "
                        "VALUES (?, ?, ?)",
                        (timestamp, START_ADDRESS, json.dumps(registers)),
                    )
                    db.commit()
                    print(timestamp, registers)

                time.sleep(POLL_SECONDS)
        finally:
            client.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
