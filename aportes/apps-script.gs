/**
 * Vigía del Paraná — receptor de aportes de vecinos (Google Apps Script).
 *
 * Se pega en una planilla de Google (Extensiones > Apps Script) y se publica como
 * "Aplicación web" (Ejecutar como: yo · Quién tiene acceso: cualquier persona).
 *
 * - POST: recibe un aporte {lat, lng, acc, resp, est, h, hFecha, did, prueba} y lo agrega
 *   como fila a la hoja "aportes". Los puntos exactos quedan solo en esta planilla privada.
 * - GET ?accion=mapa: devuelve el resumen público por cuadrados de ~250 m, solo de los
 *   cuadrados con al menos 3 aportes de celulares distintos. Nunca devuelve puntos.
 */

var HOJA = "aportes";
var CELDA_M = 250;          // lado del cuadrado del mapa, en metros
var MINIMO = 3;             // aportes de celulares distintos para mostrar un cuadrado
var ACC_MAX = 50;           // margen de error máximo del GPS, en metros
var MAX_POR_MINUTO = 60;    // freno general contra envíos masivos
var RESPUESTAS = ["no", "calle", "terreno", "casa"];
var SEVERIDAD = { no: 0, calle: 1, terreno: 2, casa: 3 };
var COLUMNAS = ["recibido", "fecha_local", "lat", "lng", "precision_m", "respuesta", "estacion", "altura_rio_m", "fecha_dato_rio", "celular", "prueba"];

function hoja_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(HOJA);
  if (!sh) {
    sh = ss.insertSheet(HOJA);
    sh.appendRow(COLUMNAS);
    sh.setFrozenRows(1);
  }
  return sh;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function hoyLocal_() {
  return Utilities.formatDate(new Date(), "America/Argentina/Buenos_Aires", "yyyy-MM-dd");
}

function doPost(e) {
  var d;
  try { d = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false, motivo: "invalido" }); }

  var lat = Number(d.lat), lng = Number(d.lng), acc = Number(d.acc), h = Number(d.h), est = parseInt(d.est, 10);
  var did = String(d.did || "");
  if (!(lat < -24.5 && lat > -35 && lng < -53 && lng > -62.5)) return json_({ ok: false, motivo: "fuera_de_zona" });
  if (!(acc > 0 && acc <= ACC_MAX)) return json_({ ok: false, motivo: "precision" });
  if (RESPUESTAS.indexOf(d.resp) < 0) return json_({ ok: false, motivo: "invalido" });
  if (!/^[a-z0-9-]{8,40}$/.test(did)) return json_({ ok: false, motivo: "invalido" });
  if (!(h > -2 && h < 40) || !(est > 0)) return json_({ ok: false, motivo: "invalido" });
  var prueba = d.prueba === true;

  var lock = LockService.getScriptLock();
  try { lock.waitLock(10000); } catch (err) { return json_({ ok: false, motivo: "saturado" }); }
  try {
    // freno general por minuto
    var cache = CacheService.getScriptCache();
    var minuto = "m" + Math.floor(Date.now() / 60000);
    var n = Number(cache.get(minuto) || 0);
    if (n >= MAX_POR_MINUTO) return json_({ ok: false, motivo: "saturado" });
    cache.put(minuto, String(n + 1), 120);

    // un aporte por día por celular (los de prueba no cuentan)
    var hoy = hoyLocal_();
    var props = PropertiesService.getScriptProperties();
    if (!prueba) {
      if (props.getProperty("d_" + did) === hoy) return json_({ ok: false, motivo: "ya_aportaste" });
    }

    hoja_().appendRow([new Date(), hoy, lat, lng, Math.round(acc), d.resp, est, h, String(d.hFecha || ""), did, prueba ? "sí" : ""]);
    if (!prueba) props.setProperty("d_" + did, hoy);
    cache.remove("mapa");
    return json_({ ok: true });
  } finally {
    lock.releaseLock();
  }
}

function doGet(e) {
  var accion = (e && e.parameter && e.parameter.accion) || "";
  if (accion !== "mapa") return json_({ ok: true, servicio: "Vigía del Paraná · aportes de vecinos" });

  var cache = CacheService.getScriptCache();
  var hit = cache.get("mapa");
  if (hit) return ContentService.createTextOutput(hit).setMimeType(ContentService.MimeType.JSON);

  var datos = hoja_().getDataRange().getValues();
  var celdas = {};
  var dLat = CELDA_M / 111320;
  for (var i = 1; i < datos.length; i++) {
    var r = datos[i];
    var lat = Number(r[2]), lng = Number(r[3]), resp = r[5], est = r[6], h = Number(r[7]), dia = String(r[1]), did = String(r[9]), prueba = r[10];
    if (prueba || RESPUESTAS.indexOf(resp) < 0 || isNaN(lat) || isNaN(lng)) continue;
    var cy = Math.floor(lat / dLat), latc = (cy + 0.5) * dLat;
    var dLng = CELDA_M / (111320 * Math.cos(latc * Math.PI / 180));
    var cx = Math.floor(lng / dLng);
    var k = cy + ":" + cx;
    var c = celdas[k];
    if (!c) c = celdas[k] = { s: cy * dLat, n: (cy + 1) * dLat, w: cx * dLng, e: (cx + 1) * dLng, cel: {}, r: { no: 0, calle: 0, terreno: 0, casa: 0 }, est: {}, hmin: null, hmax: null, desde: dia, hasta: dia };
    c.cel[did] = true;
    c.r[resp]++;
    c.est[est] = (c.est[est] || 0) + 1;
    if (!isNaN(h)) { c.hmin = c.hmin == null ? h : Math.min(c.hmin, h); c.hmax = c.hmax == null ? h : Math.max(c.hmax, h); }
    if (dia < c.desde) c.desde = dia;
    if (dia > c.hasta) c.hasta = dia;
  }

  var out = [];
  for (var key in celdas) {
    var c2 = celdas[key], n = Object.keys(c2.cel).length;
    if (n < MINIMO) continue;
    var modo = "no", best = -1;
    RESPUESTAS.forEach(function (x) { if (c2.r[x] > best || (c2.r[x] === best && SEVERIDAD[x] > SEVERIDAD[modo])) { best = c2.r[x]; modo = x; } });
    var estMas = null, estN = -1;
    for (var s in c2.est) { if (c2.est[s] > estN) { estN = c2.est[s]; estMas = Number(s); } }
    out.push({ s: +c2.s.toFixed(6), w: +c2.w.toFixed(6), n: +c2.n.toFixed(6), e: +c2.e.toFixed(6), aportes: n, r: c2.r, modo: modo, est: estMas, hmin: c2.hmin, hmax: c2.hmax, desde: c2.desde, hasta: c2.hasta });
  }
  var txt = JSON.stringify({ ok: true, actualizado: new Date().toISOString(), celda_m: CELDA_M, minimo: MINIMO, celdas: out });
  if (txt.length < 90000) cache.put("mapa", txt, 300);
  return ContentService.createTextOutput(txt).setMimeType(ContentService.MimeType.JSON);
}
