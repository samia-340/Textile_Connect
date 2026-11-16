# ZWARK Connect — Automatic shift simulation via mill API

## Start

Open this folder in VS Code. In terminal 1:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn mill_api:app --reload --port 8000
```

In terminal 2:

```powershell
python -m streamlit run app.py
```

## Demo steps

1. Supplier: create a contract, e.g. ZW-001 for 1000 kg.
2. Supplier: dispatch 1000 kg in Dispatch & QR.
3. Weaving Mill: confirm receipt of 1000 kg.
4. Supplier: API Integration → select contract → Save mapping (e.g. MILL-ZW-001).
5. Click **Generate next shift + synchronize from mill API**.
6. Each click creates one new shift in `simulated_mill.db`, then ZWARK imports it into `zwark_connect.db` through the API.
7. Supplier: Production Visibility → view one row for each shift and updated totals.

The simulation starts with today's Morning shift and advances to Evening, Night, then the next day's Morning shift. Each shift uses deterministic illustrative quantities. Do not use for real inventory or production accounting.

