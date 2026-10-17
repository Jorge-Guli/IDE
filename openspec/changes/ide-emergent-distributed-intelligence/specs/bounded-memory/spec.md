# Spec Delta: Bounded Memory

## Purpose
Proveer la memoria local acotada (`BoundedMemory`) de cada micro-agente, garantizando la capacidad máxima $C_{\max}$, el reemplazo selectivo por utilidad epistémica $U(k, t)$ y el decaimiento pasivo de confianza.

## ADDED Requirements

### Requirement: Límite Estricto de Capacidad
`BoundedMemory` en `src/ide/agent/memory.py` SHALL almacenar como máximo `capacity` instancias de `KnowledgeUnit`, a lo sumo una por `Pattern`.

#### Scenario: Inserción con espacio disponible
- **WHEN** `BoundedMemory(capacity=3)` contiene 2 creencias y se inserta una con patrón nuevo
- **THEN** `upsert` devuelve `True` y `len(memory) == 3`.

#### Scenario: Actualización de patrón existente con memoria llena
- **WHEN** la memoria de capacidad 3 está llena y se ejecuta `upsert` de un `KnowledgeUnit` cuyo patrón ya está almacenado
- **THEN** la entrada se reemplaza por la nueva versión, `upsert` devuelve `True` y `len(memory)` sigue siendo 3.

### Requirement: Índice de Utilidad Epistémica
`compute_utility(unit, t)` SHALL devolver $U(k,t) = c \cdot \max(|\hat{v}|, 0.1) \cdot e^{-\lambda \cdot \max(0,\, t - \tau)}$, con $\lambda$ = `lambda_decay` de la memoria.

#### Scenario: Valor numérico exacto
- **WHEN** `lambda_decay = 0.005`, la creencia tiene `confidence = 0.2`, `predicted_value = 1.0`, `last_updated_tick = 1` y `t = 10`
- **THEN** `compute_utility` devuelve `0.2 * exp(-0.045)` con tolerancia `1e-12`.

#### Scenario: Piso de relevancia
- **WHEN** la creencia tiene `predicted_value = 0.0`, `confidence = 1.0` y `t == last_updated_tick`
- **THEN** `compute_utility` devuelve `0.1`.

### Requirement: Reemplazo por Menor Utilidad
Con la memoria llena y un patrón nuevo, `upsert` SHALL elegir como víctima la creencia de menor utilidad (desempate por menor `last_updated_tick` y luego por menor `pattern`) y reemplazarla sólo si la utilidad de la nueva es estrictamente mayor; si no, SHALL devolver `False` sin modificar la memoria.

#### Scenario: Expulsión de creencia obsoleta y débil
- **WHEN** una memoria de capacidad 2 contiene $k_1$ (`c=0.9`, `|v̂|=1.0`, `τ=10`) y $k_2$ (`c=0.2`, `|v̂|=1.0`, `τ=1`) y en `t=10` se inserta $k_3$ (`c=0.85`, `|v̂|=1.0`, `τ=10`)
- **THEN** $k_2$ es expulsada, $k_3$ ocupa su lugar y $k_1$ se conserva intacta.

#### Scenario: Rechazo de rumor débil
- **WHEN** todas las creencias de una memoria llena tienen utilidad mayor a `0.8` y se intenta insertar una creencia nueva de utilidad `0.25`
- **THEN** `upsert` devuelve `False` y la memoria no cambia.

#### Scenario: Desempate determinista
- **WHEN** dos creencias empatan en la utilidad mínima y en `last_updated_tick`
- **THEN** la víctima es la de menor `pattern` según el orden de `Pattern`.

### Requirement: Inserción Forzada
`upsert(unit, t, force=True)` SHALL insertar la creencia aunque su utilidad no supere a la víctima, expulsando a la víctima definida por la regla de reemplazo, y devolver `True`.

#### Scenario: Forzar una creencia de baja utilidad
- **WHEN** la memoria está llena de creencias con utilidad mayor a `0.8` y se ejecuta `upsert` de una creencia de utilidad `0.25` con `force=True`
- **THEN** la nueva creencia queda almacenada, `len(memory)` no cambia y `upsert` devuelve `True`.

### Requirement: Decaimiento Pasivo y Purga
`decay_step(t, passive_decay, min_confidence)` SHALL restar `passive_decay` a la confianza de cada creencia con `last_updated_tick < t` sin modificar su `last_updated_tick`, purgar las que queden por debajo de `min_confidence` y devolver los patrones purgados ordenados.

#### Scenario: Purga de creencia degradada
- **WHEN** una creencia tiene `confidence = 0.06`, `last_updated_tick < t`, y se invoca `decay_step(t, 0.02, 0.05)`
- **THEN** su confianza cae a `0.04`, se elimina de la memoria y su patrón aparece en la lista devuelta.

#### Scenario: Creencia validada en el tick actual
- **WHEN** una creencia tiene `last_updated_tick == t` y se invoca `decay_step(t, 0.02, 0.05)`
- **THEN** su confianza no cambia.

### Requirement: Iteración Determinista
`all_units()` SHALL devolver las creencias ordenadas por `pattern`, independientemente del orden de inserción y de `PYTHONHASHSEED`.

#### Scenario: Orden de salida
- **WHEN** se insertan creencias de `p_2`, `p_0` y `p_1`, en ese orden
- **THEN** `[u.pattern.label for u in memory.all_units()] == ["id=p_0", "id=p_1", "id=p_2"]`.
