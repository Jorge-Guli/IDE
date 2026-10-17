# Spec Delta: Bounded Memory

## ADDED Requirements

### Requirement: Modulación de Utilidad por Penalización de Redundancia Intra-Holón (R18)
`BoundedMemory` SHALL permitir configurar un conjunto de patrones redundantes `set_redundant_patterns(patterns: frozenset[Pattern], penalty: float = 1.0)` tal que `compute_utility(unit, t)` multiplique el valor basal $c \cdot \max(|\hat{v}|, 0.1) \cdot e^{-\lambda \cdot \max(0,\, t - \tau)}$ por `penalty` ($\psi_{\text{red}} \in (0, 1]$) si `unit.pattern` pertenece a `redundant_patterns`, y por `1.0` en caso contrario; por defecto `redundant_patterns` es vacío y `penalty = 1.0`, preservando bit a bit el cálculo de Fase I.

#### Scenario: Utilidad modulada para patrón redundante en el holón
- **WHEN** se configura `memory.set_redundant_patterns(frozenset({p_0}), penalty=0.25)` y se evalúa `compute_utility` sobre $k(\rho_0)$ y $k(\rho_1)$ con iguales parámetros `(c=0.8, v̂=1.0, τ=10)` en `t=10`
- **THEN** la utilidad de $k(\rho_0)$ es exactamente `0.20` y la de $k(\rho_1)$ es `0.80` (con tolerancia `1e-12`).
