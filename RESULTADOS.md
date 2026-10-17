# Registro de resultados empíricos

Resultados tal cual se obtuvieron, positivos o negativos, **sin ajustar parámetros** a la vista de los datos (Decisión 10 de `design.md`). Cada entrada indica el commit del código que la produjo.

## Experimento 001: expectativas funcionales (bloque 9.5)

- **Código:** el commit que agrega esta entrada (bloque 9 de `tasks.md`; `git log -- RESULTADOS.md`).
- **Comando:** `python -m pytest -m empirical` (16 tests, `SimulationConfig()` por defecto, perfil `quick`: 300 ticks; 001-B con inyección en el tick 80 al 25 %).
- **Resultado:** 16 de 16 pasan.
- **Alcance (regla de atribución):** H1 verifica que los mecanismos de comunicación programados cumplen su propósito. **No** es evidencia de emergencia: C1 y C2 son programadas por construcción (ver 001-D).

| Semilla | Precisión colectiva | Precisión aislada | Superávit | Cob. accesible colectiva | Cob. accesible aislada | Mensajes/agente | Rumor inicial | Rumor pico | Rumor final | Ticks a extinción |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 42 | 0.7998 | 0.5716 | +0.2282 | 0.3469 | 0.1427 | 1.455 | 0.2500 | 0.6000 | 0.0000 | 123 |
| 43 | 0.8480 | 0.6068 | +0.2412 | 0.3302 | 0.1469 | 1.400 | 0.2500 | 0.5250 | 0.0000 | 183 |
| 44 | 0.7849 | 0.5463 | +0.2385 | 0.3625 | 0.1354 | 1.435 | 0.2500 | 0.4500 | 0.0000 | 81 |
| 45 | 0.8224 | 0.5860 | +0.2364 | 0.3312 | 0.1448 | 1.463 | 0.2500 | 0.6750 | 0.0000 | 141 |
| 46 | 0.8314 | 0.5897 | +0.2417 | 0.3000 | 0.1500 | 1.428 | 0.2500 | 0.3625 | 0.0000 | 195 |

- **H1 (superávit):** positivo en las 5 semillas; prueba de signo unilateral `p = 0.03125 < 0.05`. La cobertura accesible colectiva supera a la aislada en las 5.
- **Contención del rumor (001-B):** el rumor falso se extingue por completo en las 5 semillas, entre 81 y 195 ticks después de la inyección.
- **Observación no prevista:** antes de extinguirse, el rumor **se propaga**. La prevalencia pico (0.36 a 0.68) es de 1.5 a 2.7 veces la inicial (0.25). La contención no es inmediata: la población primero amplifica la falsedad y luego la elimina. Si esa dinámica depende de los filtros diseñados (R3, R4, R6, R7) lo decide C3 en 001-D.
