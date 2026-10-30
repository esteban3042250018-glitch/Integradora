# Artefacto Python — Bloque C (CPM, PERT y Monte Carlo)

**Universidad Tecnológica de Durango · 4B · Proyecto Integrador**  
Proyecto: Sistema de Control de Correspondencia del CVDR Unidad Durango.  
Responsable de programación: **Juan Fernando Ramírez Ramos (Persona 1)**.  
Cálculo CPM: Omar Gabriel Flores Castro (Persona 3).  
PERT y escenarios: Jaime Cruz Rodríguez (Persona 4).

## Qué incluye

El programa `artefacto_corregido_4B.py` conserva las funciones principales del artefacto original: validación de la red, cálculo de ruta crítica con pasadas hacia adelante y atrás, holguras total/libre, PERT analítico, Monte Carlo con distribuciones beta-PERT o triangular, tabla CSV, histograma y diagrama de red. Además, compara escenarios de retraso de **3 días en Q (crítica)** y **3 días en N (no crítica, holgura de 1 día)**.

**Datos utilizados:** las **18 actividades A–S (sin O)**, predecesoras y estimaciones optimista / más probable / pesimista de `Persona4_PERT_Analisis_Escenarios_Correspondencia.docx`. Son los mismos datos y actividades del documento final de CPM de la Persona 3 (`A03B_BloqueC_Persona3_Red_Actividades_CPM_CORREGIDO_PERFECTO.docx`). Las duraciones siguen siendo **estimaciones que el equipo debe validar**.

## Requisitos

- Python **3.10 o posterior**.
- `numpy` y `matplotlib`.
- Funciona en Windows y en Google Colab, ejecutándolo como archivo `.py`.

En la terminal o PowerShell:

```powershell
python -m pip install -r requirements_artefacto_4B.txt
```

## Cómo ejecutar

Desde la carpeta que contiene los archivos:

```powershell
python artefacto_corregido_4B.py --verificar
python artefacto_corregido_4B.py --iteraciones 100000 --semilla 42 --salida resultados
```

Los valores por defecto son **inicio 2026-10-21** y **Expo 2026-12-11**, fechas **provisionales**, sin descontar festivos. Se cuentan lunes a viernes e incluye el día de la Expo como fecha límite.

Para usar fechas oficiales cuando estén confirmadas:

```powershell
python artefacto_corregido_4B.py --inicio 2026-10-21 --expo 2026-12-11 --iteraciones 100000 --salida resultados
```

Para probar con distribución triangular (en vez de beta-PERT):

```powershell
python artefacto_corregido_4B.py --distribucion triangular --iteraciones 10000
```

**No reduzcas las simulaciones por debajo de 10,000**, ya que es el mínimo de la actividad.

## Resultados validados con la red acordada

Con las fechas provisionales anteriores, 100,000 iteraciones, distribución beta-PERT y semilla 42:

| Resultado | Valor aproximado |
| --- | ---: |
| Actividades / predecesoras | 18, red P3/P4 |
| Duración esperada por CPM con `te` | 40.83 días laborables |
| Ruta crítica representativa | A → B → G → K → M → P → Q → R → S |
| Actividades no críticas | D, E, H, I, N |
| Probabilidad de acabar antes de la Expo, PERT normal | 9.15 % |
| Probabilidad de acabar antes de la Expo, Monte Carlo | 2.12 % |
| Promedio de duración simulada | 42.32 días |
| Percentil 90 simulado | 45.14 días |
| Retraso en Q de 3 días | Duración CPM esperada +3 días |
| Retraso en N de 3 días | Duración CPM esperada +2 días (1 de holgura) |

Los valores Monte Carlo fluctúan al cambiar la semilla, el número de iteraciones o la distribución. La diferencia con el PERT analítico se debe principalmente a la existencia de rutas críticas paralelas; el analítico aproxima una única ruta, mientras que Monte Carlo simula toda la red.

La fecha calculada a partir del P90 se redondea **hacia arriba a días laborables completos**. Por eso el resultado de calendario conservador puede diferir un día respecto de fechas **aproximadas** obtenidas redondeando el percentil al día más próximo.

## Archivos de salida

Al ejecutar el programa se crea una carpeta `resultados/` con:

- `actividades.csv`: 18 actividades, predecesoras, valores `a`, `m`, `b`, `te`, justificación y varianza.
- `cpm_modal.csv`: CPM con duración más probable `m`.
- `cpm_pert.csv`: CPM con tiempos esperados de PERT; ES, EF, LS, LF, holguras y criticidad Monte Carlo.
- `simulaciones.csv`: una fila por iteración, duración completa, duración de una ruta fija y cumplimiento del plazo.
- `resumen.json`: probabilidad analítica y simulada, percentil 90, rutas, holguras y escenarios.
- `histograma_comparativo.png`: distribución Monte Carlo superpuesta con PERT normal.
- `red_cpm.png`: red de actividades con tareas críticas destacadas.

## Errores reparados frente al archivo original

1. Se solucionó el problema de `from __future__` después de dos cadenas de texto.
2. Se sustituyó la red anterior de 12 actividades en cadena por la **red de 18 actividades de la Persona 4**, con las estimaciones exactas de su tabla PERT.
3. `argparse` ahora respeta los parámetros que escribes en la terminal; antes se ignoraban.
4. Las pruebas incorporan valores de referencia **40.83 días**, holguras y escenarios **Q/N**.
5. Se obtienen probabilidades de escenarios con Monte Carlo (además de los retrasos CPM).

## Consideraciones importantes

Este modelo estima **duración de red**, pero no comprueba disponibilidad real de recursos ni carga horaria del equipo. La fecha de Expo no está confirmada y las cifras de PERT y Monte Carlo **no son garantías**. Antes de entregar, confirmen fecha oficial, festivos, tareas y duraciones finales. Las simulaciones del archivo de ejemplo se guardaron con parámetros visibles en `resumen.json`.

**IA:** Este artefacto fue revisado y adaptado con asistencia de IA; el equipo debe declarar ese uso en el Anexo C, revisar el código y poder explicarlo durante la exposición.
