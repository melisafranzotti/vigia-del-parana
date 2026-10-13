# Vigía del Paraná

App comunitaria, gratuita y sin fines de lucro para seguir la crecida de los ríos Paraná y Paraguay en Argentina y saber **cómo actuar hoy** según tu ubicación. Pensada para que la use cualquier persona desde el celular, sin cuenta ni instalación.

**No es una aplicación oficial.** Reúne y ordena información publicada por organismos oficiales. Ante una emergencia, manda lo que indiquen Defensa Civil (103) y cada municipio.

## Qué hace

- Detecta tu zona por GPS, marcando tu casa en el mapa, escribiendo tu dirección o pegando lo que te da Google Maps.
- Muestra la altura actual del puerto más cercano, el ritmo de subida, los niveles oficiales de alerta y evacuación, y un estado en cuatro niveles: **Normal, Atención, Preparación, Salida**.
- En el Gran Santa Fe distingue zonas finas (dentro o fuera del terraplén, lado río o lado Setúbal) con umbrales y señales de vigilancia propias.
- Lista qué hacer hoy según el nivel, qué pasa aguas arriba, el estado de Itaipú y Yacyretá, el pronóstico del INA y noticias de la cuenca con enlace a la fuente.
- Se instala como app (PWA) y abre sin conexión con los últimos datos vistos.

## De dónde salen los datos

| Dato | Fuente |
|---|---|
| Alturas diarias de 33 puertos, niveles de alerta y evacuación | [INA, Alerta Hidrológico Cuenca del Plata](https://alerta.ina.gob.ar/a5/diario/reporte_diario) (API `getObservaciones`), escalas de [Prefectura Naval Argentina](https://contenidosweb.prefecturanaval.gob.ar/alturas/) |
| Pronósticos (tramo medio: martes a 7 y 14 días, viernes a 4 y 11) | [INA](https://www.ina.gob.ar/alerta/) |
| Represas | [Entidad Binacional Yacyretá](https://www.eby.gov.py), [Itaipú Binacional](https://www.itaipu.gov.py) |
| Clima | [Servicio Meteorológico Nacional](https://www.smn.gob.ar) |
| Noticias | Medios de la región, resumidas con enlace a la nota original |

## Cómo se actualiza

- `data/alturas.json`: un GitHub Action (`.github/workflows/alturas.yml`) descarga las alturas del INA dos veces por día (07:20 y 19:20 hora Argentina).
- `data/contexto.json`: resumen del día, represas, pronósticos y noticias. Lo actualiza una tarea programada que revisa las fuentes y publica al repositorio dos veces por día.
- `data/estaciones.json`: catálogo de estaciones (fijo).
- `data/zonas.geojson`: zonas finas del Gran Santa Fe. **Los polígonos son aproximados**; se ajustan en [geojson.io](https://geojson.io) con conocimiento local.

## Cómo se calcula el estado

- Para las zonas finas del Gran Santa Fe, cada zona tiene tres umbrales en la regla del puerto de Santa Fe (atención, preparación, salida) definidos con las crecidas anteriores y el estado de las defensas.
- Para el resto de las ciudades: atención = alerta oficial − 1 m, preparación = alerta − 0,5 m, salida = alerta oficial. La evacuación oficial se muestra siempre.
- La "tendencia" y los "días hasta cada umbral" prolongan el ritmo de la última semana. No son pronóstico oficial.

## Limitaciones

- El dato de altura es el diario de las 00 h; no es tiempo real.
- Las zonas finas existen solo para el Gran Santa Fe. En las demás ciudades el estado es por ciudad, con los niveles oficiales.
- Los links cortos de Google Maps (`maps.app.goo.gl`) no traen la ubicación. La app pide usar el GPS, el mapa o la dirección. Opcional: configurar `RESOLVER_URL` en `app.js` apuntando a un servicio que resuelva esos links.
- Lo que no está en la app: el río Salado, el río Uruguay, y la situación cuadra por cuadra.

## Colaborar

Correcciones de zonas, umbrales, referencias o textos: abrí un issue o un pull request. Si vivís en la Costa santafesina y conocés hasta dónde llegó el agua en crecidas anteriores, ese dato vale más que cualquier estimación.

## Licencia

MIT. Hecho en Santa Fe, Argentina.
