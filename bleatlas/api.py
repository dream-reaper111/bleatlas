"""Loopback inventory dashboard API."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .hardware import capabilities
from .storage import Inventory


HTML = """<!doctype html><html><head><meta charset='utf-8'><title>BLEAtlas</title>
<style>body{font:16px system-ui;margin:2rem;background:#101820;color:#e7f2f5}button,input,select{padding:.5rem;margin:.25rem}table{border-collapse:collapse;width:100%}td,th{padding:.5rem;border-bottom:1px solid #40545d;text-align:left}small{color:#a8c2c9}</style></head>
<body><h1>BLEAtlas</h1><p>Authorized BLE advertisement inventory</p>
<label>Filter <input id='filter' aria-label='Filter devices'></label><button id='refresh'>Refresh</button>
<small id='status'></small><table><thead><tr><th>Address</th><th>Name</th><th>Seen</th><th>RSSI median</th><th>Services</th><th>Change</th></tr></thead><tbody id='rows'></tbody></table>
<script>let devices=[];async function load(){let r=await fetch('/api/devices');devices=await r.json();render();document.getElementById('status').textContent=devices.length+' inventory entries';}
function render(){let q=document.getElementById('filter').value.toLowerCase();let body=document.getElementById('rows');body.replaceChildren();for(let d of devices.filter(x=>JSON.stringify(x).toLowerCase().includes(q))){let tr=document.createElement('tr');for(let v of [d.address,d.name||'',d.last_seen,d.rssi_median_dbm??'',d.service_uuids.join(', '),d.advertisement_changed?'Observed':'']){let td=document.createElement('td');td.textContent=String(v);tr.appendChild(td)}body.appendChild(tr)}}
document.getElementById('filter').oninput=render;document.getElementById('refresh').onclick=load;load();</script></body></html>"""


def create_app(path: Path, retention_days: int = 7, max_records: int = 100_000) -> FastAPI:
    app = FastAPI(title="BLEAtlas", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTML

    @app.get("/api/devices")
    def devices():
        db = Inventory(path, retention_days, max_records)
        try:
            return db.devices()
        finally:
            db.close()

    @app.get("/api/hardware")
    def hardware():
        return capabilities()

    return app
