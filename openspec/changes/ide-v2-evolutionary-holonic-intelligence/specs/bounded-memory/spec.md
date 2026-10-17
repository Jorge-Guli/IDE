# Spec Delta: Bounded Memory

## MODIFIED Requirements

### Requirement: Índice de Utilidad Epistémica
`compute_utility(unit, t)` SHALL devolver $U(k,t) = \psi \cdot c \cdot \max(|\hat{v}|, 0.1) \cdot e^{-\lambda \cdot \max(0,\, t - \tau)}$, con $\lambda$ = `lambda_decay` de la memoria, $\psi$ = `penalty` si `unit.pattern` está en los patrones de la última llamada a `set_redundant_patterns(patterns: frozenset[Pattern], penalty: float = 1.0)` (cada llamada reemplaza a la anterior; `ValueError` si `penalty` no está en $(0, 1]$), y $\psi = 1$ si no. Por defecto no hay patrones redundantes.

#### Scenario: Valor numérico exacto
- **WHEN** `lambda_decay = 0.005`, la creencia tiene `confidence = 0.2`, `predicted_value = 1.0`, `last_updated_tick = 1` y `t = 10`
- **THEN** `compute_utility` devuelve `0.2 * exp(-0.045)` con tolerancia `1e-12`.

#### Scenario: Piso de relevancia
- **WHEN** la creencia tiene `predicted_value = 0.0`, `confidence = 1.0` y `t == last_updated_tick`
- **THEN** `compute_utility` devuelve `0.1`.

#### Scenario: Utilidad modulada para patrón redundante en el holón
- **WHEN** se configura `memory.set_redundant_patterns(frozenset({p_0}), penalty=0.25)` y se evalúa `compute_utility` sobre $k(\rho_0)$ y $k(\rho_1)$ con iguales parámetros `(c=0.8, v̂=1.0, τ=10)` en `t=10`
- **THEN** la utilidad de $k(\rho_0)$ es `0.20` y la de $k(\rho_1)$ es `0.80` (con tolerancia `1e-12`), y sin llamar a `set_redundant_patterns` ambas valen `0.80`, bit a bit igual que en Fase I.
