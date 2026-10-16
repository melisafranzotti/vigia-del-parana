# Aportes de vecinos

Cuando el río está en alerta en su puerto, quien usa **Usar mi ubicación** ve el botón
**Aportar datos a la comunidad** y puede contar hasta dónde llegó el agua en su lugar.
Los aportes llegan a una planilla privada de Google. La app publica solo un resumen por
cuadrados de unos 250 m, y solo cuando un cuadrado tiene al menos 3 aportes de celulares
distintos. Nunca se publica un punto ni una casa.

## Qué se guarda

En la planilla privada (hoja `aportes`) se guardan estos datos de cada aporte:

- fecha
- punto del GPS y su margen de error
- respuesta (`no`, `calle`, `terreno`, `casa`)
- puerto y altura del río en ese momento
- un código al azar del celular, para contar un aporte por día

No se guardan nombres, teléfonos ni otros datos personales.

## Puesta en marcha (una sola vez)

1. En Google Drive, creá una planilla nueva. Por ejemplo, "Vigía del Paraná · aportes".
2. En la planilla, entrá a **Extensiones > Apps Script**.
3. Borrá lo que aparece y pegá todo el contenido de [`apps-script.gs`](apps-script.gs). Guardá con el ícono del disquete.
4. Tocá **Implementar > Nueva implementación**.
5. En el engranaje, elegí el tipo **Aplicación web**.
6. Configurá la implementación así:
   - **Descripción:** aportes
   - **Ejecutar como:** Yo
   - **Quién tiene acceso:** Cualquier persona
7. Tocá **Implementar** y aceptá los permisos que pide Google:
   - Elegí tu cuenta.
   - Si aparece "Google no verificó esta app", tocá **Configuración avanzada** y después **Ir a … (no seguro)**. Es tu propio programa.
8. Copiá la **URL de la aplicación web**. Termina en `/exec`.
9. En `app.js`, poné esa URL en `APORTES_URL`.

## Para probar sin que el río esté en alerta

Abrí la app con `?aportar=prueba` al final de la dirección:

```
https://vigia-del-parana.github.io/?aportar=prueba
```

Ese modo tiene estas diferencias:

- Muestra el botón aunque el puerto no esté en alerta.
- Marca el aporte como prueba. Queda en la planilla con "sí" en la columna `prueba`.
- No cuenta para el mapa ni para el límite de un aporte por día.

## Reglas

| Regla | Valor |
|---|---|
| Ubicación | Solo GPS, con un margen de error de hasta 50 m |
| Cuándo aparece el botón | Desde el nivel de alerta del puerto |
| Aportes por celular | Uno por día |
| Celda del mapa | 250 m |
| Aportes mínimos para mostrar una celda | 3 aportes de celulares distintos |
| Color de la celda | La respuesta que más se repite (en empate, la más grave) |
| Límite general | 60 aportes por minuto |
