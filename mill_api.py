"""Independent simulated mill system. Run: uvicorn mill_api:app --reload --port 8000"""
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
import hashlib
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

DB = Path(__file__).with_name('simulated_mill.db')
API_KEY = os.getenv('ZWARK_DEMO_API_KEY', 'local-demo-key')
app = FastAPI(title='Simulated Mill Production API', version='0.1')

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS shift_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mill_order_ref TEXT NOT NULL,
            shift_date TEXT NOT NULL,
            shift TEXT NOT NULL,
            yarn_used REAL NOT NULL CHECK(yarn_used >= 0),
            yarn_waste REAL NOT NULL CHECK(yarn_waste >= 0),
            fabric_m REAL NOT NULL CHECK(fabric_m >= 0),
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL)''')
init_db()

class ShiftRecord(BaseModel):
    mill_order_ref: str = Field(min_length=1, max_length=100)
    shift_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    shift: str = Field(min_length=1, max_length=40)
    yarn_used: float = Field(ge=0)
    yarn_waste: float = Field(ge=0)
    fabric_m: float = Field(ge=0)
    notes: str = ''

def require_key(key):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail='Invalid demo API key')

@app.get('/health')
def health():
    return {'status': 'ok', 'system': 'independent simulated mill'}

@app.post('/mill/shift-records', status_code=201)
def create_record(record: ShiftRecord, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    with connect() as db:
        cursor = db.execute('''INSERT INTO shift_records
            (mill_order_ref,shift_date,shift,yarn_used,yarn_waste,fabric_m,notes,created_at)
            VALUES (?,?,?,?,?,?,?,?)''',
            (record.mill_order_ref, record.shift_date, record.shift,
             record.yarn_used, record.yarn_waste, record.fabric_m, record.notes,
             datetime.now(timezone.utc).isoformat()))
        return {'id': cursor.lastrowid, 'message': 'Stored in mill system'}

@app.get('/mill/orders/{mill_order_ref}/shift-records')
def get_records(mill_order_ref: str, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    with connect() as db:
        data = db.execute('SELECT * FROM shift_records WHERE mill_order_ref=? ORDER BY id', (mill_order_ref,)).fetchall()
    return {'mill_order_ref': mill_order_ref, 'records': [dict(r) for r in data]}


@app.post('/mill/orders/{mill_order_ref}/simulate-next-shift')
def simulate_next_shift(mill_order_ref: str, x_api_key: str | None = Header(default=None)):
    """Create one NEW shift in the independent mill database per click.
    Repeated calls advance Morning -> Evening -> Night -> next date.
    """
    require_key(x_api_key)
    with connect() as db:
        previous = db.execute(
            'SELECT shift_date, shift FROM shift_records WHERE mill_order_ref=? '
            'ORDER BY shift_date DESC, CASE shift WHEN "Morning" THEN 1 WHEN "Evening" THEN 2 WHEN "Night" THEN 3 ELSE 0 END DESC LIMIT 1',
            (mill_order_ref,)).fetchone()
        if previous:
            old_date = date.fromisoformat(previous['shift_date'])
            old_shift = previous['shift']
            if old_shift == 'Morning':
                shift_date, shift = old_date, 'Evening'
            elif old_shift == 'Evening':
                shift_date, shift = old_date, 'Night'
            else:
                shift_date, shift = old_date + timedelta(days=1), 'Morning'
        else:
            shift_date, shift = datetime.now().date(), 'Morning'
        # Stable, illustrative values based on order/date/shift, not real sensor readings.
        digest = hashlib.sha256(f'{mill_order_ref}|{shift_date}|{shift}'.encode()).digest()
        used = float(55 + digest[0] % 36)
        waste = round(1.0 + (digest[1] % 25) / 10, 1)
        fabric = float(used * 4)
        cur = db.execute('INSERT INTO shift_records (mill_order_ref,shift_date,shift,yarn_used,yarn_waste,fabric_m,notes,created_at) VALUES (?,?,?,?,?,?,?,?)',
            (mill_order_ref,str(shift_date),shift,used,waste,fabric,
             'AUTO-GENERATED DEMO SHIFT; illustrative data',datetime.now(timezone.utc).isoformat()))
        return {'created': True, 'record': {'id': cur.lastrowid, 'mill_order_ref': mill_order_ref,
            'shift_date': str(shift_date), 'shift': shift, 'yarn_used': used,
            'yarn_waste': waste, 'fabric_m': fabric}}
