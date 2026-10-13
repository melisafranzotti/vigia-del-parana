#!/usr/bin/env python3
"""Calibra el modelo de propagación de Vigía del Paraná y escribe data/modelo.json.

Idea: la altura de un puerto responde, con algunos días de retraso, a lo que pasó en un
puerto de aguas arriba. Para cada estación se busca la estación de aguas arriba y el
retraso (lag) que mejor explican sus variaciones en los últimos años, y se mide el error
real de la proyección a 1..15 días con pruebas sobre el pasado (backtest).

Regla de proyección (la misma que usa la app):
  h_d(t+k) ≈ h_d(t) + b · [ h_u(t+k−L) − h_u(t−L) ]      si k ≤ L (el dato de arriba ya existe)
  para k > L, h_u se prolonga con su pendiente reciente amortiguada.

Fuente de datos: API pública del INA (alerta.ina.gob.ar).
"""
import json, os, sys, time, urllib.request, urllib.parse, datetime as dt, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://alerta.ina.gob.ar/a5/getObservaciones"
ANIOS = 3
H = 15            # horizonte en días
MAXLAG = 10
DECAY = 0.85      # amortiguación de la pendiente al prolongar aguas arriba

def fetch(serie_id, start, end):
    q = urllib.parse.urlencode({"tipo": "puntual", "series_id": serie_id, "timestart": start, "timeend": end, "format": "csvless", "no_id": "true"})
    req = urllib.request.Request(BASE + "?" + q, headers={"User-Agent": "VigiaDelParana/1.0 (app comunitaria)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        txt = r.read().decode("utf-8", "replace")
    out = {}
    for line in txt.splitlines():
        p = line.strip().split(",")
        if len(p) < 3 or not p[0][:4].isdigit():
            continue
        try:
            v = float(p[2])
        except ValueError:
            continue
        d = (dt.datetime.fromisoformat(p[0].replace("Z", "+00:00")) - dt.timedelta(hours=3)).date()
        out[d] = v
    return out

def daily(series, d0, d1):
    """Lista diaria continua entre d0 y d1; huecos cortos se interpolan, largos quedan None."""
    days = (d1 - d0).days + 1
    vals = [series.get(d0 + dt.timedelta(days=i)) for i in range(days)]
    i = 0
    while i < days:
        if vals[i] is None:
            j = i
            while j < days and vals[j] is None:
                j += 1
            if 0 < i and j < days and (j - i) <= 5:
                a, b = vals[i - 1], vals[j]
                for k in range(i, j):
                    vals[k] = a + (b - a) * (k - i + 1) / (j - i + 1)
            i = j
        else:
            i += 1
    return vals

CHAIN = {}      # id -> modelo elegido {"up","lag","b"}
SERIES = {}     # id -> lista diaria
MEMO = {}

def upstream_value(uid, t, k):
    """Valor (medido o proyectado en cadena) de la estación uid en t+k, usando datos hasta t."""
    hu = SERIES[uid]
    if k <= 0:
        return hu[t + k] if t + k >= 0 else None
    key = (uid, t, k)
    if key in MEMO:
        return MEMO[key]
    val = None
    m = CHAIN.get(uid)
    if m:
        val = project(hu, SERIES[m["up"]], m["up"], t, m["lag"], m["b"], k)
    if val is None:
        if hu[t] is not None and t - 5 >= 0 and hu[t - 5] is not None:
            slope = (hu[t] - hu[t - 5]) / 5.0
            ext, sl = hu[t], slope
            for _ in range(k):
                sl *= DECAY; ext += sl
            val = ext
    MEMO[key] = val
    return val

def project(hd, hu, uid, t, L, b, k):
    """Proyección a k días desde el índice t usando solo datos hasta t (en cadena)."""
    base = hd[t]
    if base is None:
        return None
    src = t - L
    if src < 0 or hu[src] is None:
        return None
    v = upstream_value(uid, t, k - L)
    if v is None:
        return None
    return base + b * (v - hu[src])

def fit(hd, hu, L):
    """b por mínimos cuadrados sobre variaciones: Δh_d(t) ~ b · Δh_u(t−L)."""
    xs, ys = [], []
    for t in range(L + 7, len(hd)):
        if None in (hd[t], hd[t - 7], hu[t - L], hu[t - L - 7]):
            continue
        xs.append(hu[t - L] - hu[t - L - 7]); ys.append(hd[t] - hd[t - 7])
    if len(xs) < 100:
        return None
    sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
    if sxx == 0:
        return None
    b = sxy / sxx
    sy = sum(y * y for y in ys)
    r2 = (sxy * sxy) / (sxx * sy) if sy else 0
    return b, r2, len(xs)

def backtest(hd, hu, uid, L, b):
    errs = [[] for _ in range(H + 1)]
    for t in range(L + 7, len(hd) - H):
        for k in range(1, H + 1):
            p = project(hd, hu, uid, t, L, b, k)
            if p is None or hd[t + k] is None:
                continue
            errs[k].append(p - hd[t + k])
    out = []
    for k in range(1, H + 1):
        e = errs[k]
        if len(e) < 50:
            out.append(None); continue
        rmse = math.sqrt(sum(x * x for x in e) / len(e))
        out.append(round(rmse, 3))
    return out

def persistence_error(hd):
    out = []
    for k in range(1, H + 1):
        e = [hd[t + k] - hd[t] for t in range(len(hd) - H) if hd[t] is not None and hd[t + k] is not None]
        out.append(round(math.sqrt(sum(x * x for x in e) / len(e)), 3) if e else None)
    return out

def main():
    est = json.load(open(os.path.join(ROOT, "data/estaciones.json"), encoding="utf-8"))["estaciones"]
    byid = {e["id"]: e for e in est}
    hoy = dt.date.today()
    d0, d1 = hoy - dt.timedelta(days=365 * ANIOS), hoy
    series = {}
    for e in est:
        try:
            series[e["id"]] = daily(fetch(e["serie_id"], d0.isoformat(), (d1 + dt.timedelta(days=1)).isoformat()), d0, d1)
            print("ok", e["nombre"], sum(v is not None for v in series[e["id"]]), "días", file=sys.stderr)
        except Exception as ex:
            print("fallo", e["nombre"], ex, file=sys.stderr)
        time.sleep(0.4)
    modelo = {}
    global SERIES
    SERIES = series
    for e in sorted(est, key=lambda x: x["orden"]):      # aguas arriba primero: la cadena ya está lista
        hd = series.get(e["id"])
        if not hd:
            continue
        cands = [u for u in est if u["id"] in series and u["orden"] < e["orden"] and (e["orden"] - u["orden"]) <= 5]
        best = None
        for u in cands:
            hu = series[u["id"]]
            for L in range(1, MAXLAG + 1):
                f = fit(hd, hu, L)
                if not f:
                    continue
                b, r2, n = f
                if b <= 0:
                    continue
                err = backtest(hd, hu, u["id"], L, b)
                vals = [x for x in err[:10] if x is not None]
                if len(vals) < 8:
                    continue
                score = sum(vals) / len(vals)
                if best is None or score < best["score"]:
                    best = {"up": u["id"], "up_nombre": u["nombre"], "lag": L, "b": round(b, 3), "r2": round(r2, 3), "n": n, "err": err, "score": score}
        pers = persistence_error(hd)
        if best and sum(best["err"][:7]) < sum(x for x in pers[:7] if x is not None):
            best["persistencia"] = pers
            del best["score"]
            modelo[str(e["id"])] = best
            CHAIN[e["id"]] = {"up": best["up"], "lag": best["lag"], "b": best["b"]}
            print(f'{e["nombre"]:22s} <- {best["up_nombre"]:20s} lag {best["lag"]:2d}d b={best["b"]:.2f} r2={best["r2"]:.2f} err3={best["err"][2]:.2f} err7={best["err"][6]:.2f} err15={best["err"][14]} (pers7 {pers[6]:.2f})', file=sys.stderr)
        else:
            modelo[str(e["id"])] = {"persistencia": pers}
            print(f'{e["nombre"]:22s} sin modelo mejor que persistencia', file=sys.stderr)
    doc = {"ajustado": hoy.isoformat(), "anios": ANIOS, "horizonte": H, "decay": DECAY,
           "cadena": True, "nota": "Modelo de propagación en cadena por estación: upstream (up), retraso en días (lag), ganancia (b), y error RMSE medido en backtest para 1..15 días (err). 'persistencia' es el error de suponer que el río no cambia, como referencia.",
           "estaciones": modelo}
    json.dump(doc, open(os.path.join(ROOT, "data/modelo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("modelo.json escrito:", len(modelo), "estaciones", file=sys.stderr)

if __name__ == "__main__":
    main()
