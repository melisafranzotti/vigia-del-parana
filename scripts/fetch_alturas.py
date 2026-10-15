#!/usr/bin/env python3
"""Descarga las alturas diarias de todas las estaciones desde la API pública del INA
(Sistema de Información y Alerta Hidrológico, escalas de Prefectura Naval) y escribe
data/alturas.json. Corre dos veces por día desde GitHub Actions.

Fuente: https://alerta.ina.gob.ar/a5/  (endpoint getObservaciones)
"""
import json, sys, urllib.request, urllib.parse, datetime as dt, time, os

BASE = "https://alerta.ina.gob.ar/a5/getObservaciones"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAS = 35

def fetch(serie_id, start, end, marea=False):
    q = urllib.parse.urlencode({"tipo": "puntual", "series_id": serie_id, "timestart": start,
                                "timeend": end, "format": "csvless", "no_id": "true"})
    req = urllib.request.Request(BASE + "?" + q, headers={"User-Agent": "VigiaDelParana/1.0 (app comunitaria; github.com)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        txt = r.read().decode("utf-8", "replace")
    serie = {}
    for line in txt.splitlines():
        parts = line.strip().split(",")
        if len(parts) < 3 or not parts[0][:4].isdigit():
            continue
        try:
            v = float(parts[2])
        except ValueError:
            continue
        # Los registros de las 03:00Z corresponden a las 00 h de Argentina
        fecha = (dt.datetime.fromisoformat(parts[0].replace("Z", "+00:00")) - dt.timedelta(hours=3)).date().isoformat()
        if marea and fecha in serie:
            serie[fecha] = max(serie[fecha], v)   # puertos con marea: la lectura más alta del día
        else:
            serie[fecha] = v
    return sorted(serie.items())

def main():
    est = json.load(open(os.path.join(ROOT, "data/estaciones.json"), encoding="utf-8"))["estaciones"]
    prev_path = os.path.join(ROOT, "data/alturas.json")
    prev = {}
    if os.path.exists(prev_path):
        try:
            prev = {e["id"]: e for e in json.load(open(prev_path, encoding="utf-8")).get("estaciones", [])}
        except Exception:
            prev = {}
    hoy = dt.date.today()
    start, end = (hoy - dt.timedelta(days=DIAS)).isoformat(), (hoy + dt.timedelta(days=1)).isoformat()
    out, fallos = [], []
    for e in est:
        try:
            serie = fetch(e["serie_id"], start, end, e.get("marea", False))
            if not serie:
                raise RuntimeError("sin datos")
            out.append({"id": e["id"], "serie": serie, "ok": True})
        except Exception as ex:
            fallos.append(f'{e["nombre"]}: {ex}')
            p = prev.get(e["id"])
            if p and p.get("serie"):
                out.append({"id": e["id"], "serie": p["serie"], "ok": False, "nota": "sin actualizar: " + str(ex)[:80]})
        time.sleep(0.4)
    doc = {"actualizado": dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).isoformat(timespec="minutes"),
           "fuente": "INA - Alerta Hidrológico Cuenca del Plata (alerta.ina.gob.ar), escalas de Prefectura Naval Argentina",
           "estaciones": out, "fallos": fallos}
    json.dump(doc, open(prev_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"ok {len(out)} estaciones, {len(fallos)} fallos")
    for f in fallos:
        print("  -", f)
    if len(out) < len(est) // 2:
        sys.exit(1)

if __name__ == "__main__":
    main()
