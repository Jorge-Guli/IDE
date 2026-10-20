# Spec Delta: Bounded Memory

## ADDED Requirements

### Requirement: Cambio de Capacidad en Vida con Desalojo por Menor Utilidad
`BoundedMemory.resize(capacity, tick)` SHALL fijar la nueva capacidad y, mientras `len(memory) > capacity`, eliminar la creencia de menor utilidad en `tick` con el mismo criterio y desempate que el desalojo de $R_2$ (menor `last_updated_tick` y luego menor `pattern`), incluida la penalización de redundancia de $R_{18}$. El olvido forzado es parte declarada de $R_{24}$.

#### Scenario: Achicar la memoria
- **WHEN** una memoria de capacidad 3 contiene $k_1$ (`c=0.9`), $k_2$ (`c=0.2`) y $k_3$ (`c=0.6`), todas con `|v̂|=1.0` y `τ=10`, y se invoca `resize(1, 10)`
- **THEN** `capacity == 1` y la memoria conserva sólo $k_1$.

#### Scenario: Penalización de redundancia en el desalojo
- **WHEN** una memoria de capacidad 2 contiene $\rho_0$ (`c=0.9`) y $\rho_1$ (`c=0.5`), con `|v̂|=1.0` y la misma edad, $\rho_0$ está marcado redundante con `set_redundant_patterns(frozenset({ρ0}), 0.2)` y se invoca `resize(1, t)`
- **THEN** se desaloja $\rho_0$ (utilidad `0.18 < 0.5`) y se conserva $\rho_1$.

### Requirement: Agrandar la Capacidad sin Borrar y Rechazar Capacidades Inválidas
`BoundedMemory.resize(capacity, tick)` SHALL lanzar `ValueError` si `capacity < 1`, y SHALL NOT eliminar ninguna creencia cuando la nueva capacidad es mayor o igual que `len(memory)`.

#### Scenario: Agrandar la memoria
- **WHEN** una memoria de capacidad 2 con dos creencias invoca `resize(5, t)`
- **THEN** `capacity == 5`, conserva las dos creencias y admite tres inserciones más sin desalojo.

#### Scenario: Capacidad nula
- **WHEN** se invoca `resize(0, t)`
- **THEN** se lanza `ValueError` y la memoria no cambia.
