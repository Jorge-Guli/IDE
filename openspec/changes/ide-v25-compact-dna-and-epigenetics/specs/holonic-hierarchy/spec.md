# Spec Delta: Holonic Hierarchy

## ADDED Requirements

### Requirement: Roles Epigenéticos con la Regla Apagada (R25)
`assign_epigenetic_roles(holon, local_reach, config) -> dict[int, EpigeneticRole]`, en `holon.py`, SHALL validar `local_reach` con el contrato y la validación de D25.1 de la Fase II, lanzando `ValueError` también con la regla apagada, y SHALL devolver `NONE` para todas las hojas si `enable_epigenetic_roles=False` o `enable_compact_dna=False`.

#### Scenario: Regla apagada
- **WHEN** se invoca `assign_epigenetic_roles` sobre un holón de 3 hojas con `enable_epigenetic_roles=True` y `enable_compact_dna=False`
- **THEN** devuelve `NONE` para las 3 hojas.

#### Scenario: Validación del alcance local con la regla apagada
- **WHEN** se invoca `assign_epigenetic_roles` con `enable_epigenetic_roles=False` y un `local_reach` que viola el contrato de D25.1
- **THEN** se lanza `ValueError`.

### Requirement: Casta LIBRARIAN por Conocimiento Propio Único
Con la regla activa, sea $K(\ell)$ el conjunto de patrones de la memoria de $\ell$ con `confidence >= decision_conf_threshold` y `unique(ℓ)` $= |K(\ell) \setminus \bigcup_{\ell' \neq \ell} K(\ell')|$ sobre las hojas del holón; `assign_epigenetic_roles` SHALL asignar `LIBRARIAN` a la hoja que maximiza `(unique(ℓ), |K(ℓ)|, -agent_id)`, leyendo sólo memorias y sin conocer coordenadas.

#### Scenario: Desempate por conocimiento total y por identificador
- **WHEN** en un holón con hojas 1, 2 y 3 las hojas 2 y 3 tienen `unique == 2` y `|K| == 4`, y la hoja 1 tiene `unique == 1`
- **THEN** la hoja 2 recibe `LIBRARIAN`.

### Requirement: Castas EXPLORER y NERVE por Grado Interno
Con la regla activa y `deg(ℓ)` $= |\text{loc}(\ell) \setminus \{\ell\}|$, `assign_epigenetic_roles` SHALL asignar `EXPLORER` a la hoja restante que maximiza `(-deg(ℓ), -agent_id)`, luego `NERVE`, si quedan hojas, a la que maximiza `(deg(ℓ), -agent_id)` entre las restantes, y `NONE` a las demás.

#### Scenario: Holón de cuatro hojas
- **WHEN** en un holón con hojas 1, 2, 3 y 4 la hoja 1 es `LIBRARIAN` y los grados internos de 2, 3 y 4 son 1, 3 y 1
- **THEN** la hoja 2 recibe `EXPLORER`, la hoja 3 `NERVE` y la hoja 4 `NONE`.

#### Scenario: Holón de dos hojas
- **WHEN** se asignan roles en un holón de 2 hojas
- **THEN** una hoja recibe `LIBRARIAN`, la otra `EXPLORER` y ninguna recibe `NERVE`.

### Requirement: Asignación de Roles por el Motor al Cambiar la Composición
En la Fase 5, después de $R_{18}$, el motor SHALL asignar roles a cada `CompositeAgent` raíz, en orden de `node_id`, cuyo conjunto de hojas cambió desde su última asignación según `self._role_leaf_sets: dict[int, frozenset[int]]`, y SHALL escribir los roles con `set_epigenetic_role` después de calcularlos todos.

#### Scenario: Composición estable
- **WHEN** un holón raíz conserva las mismas hojas durante 10 ticks después de su asignación, aunque cambien sus memorias
- **THEN** el motor no vuelve a invocar `assign_epigenetic_roles` para ese holón y sus hojas conservan sus roles.

#### Scenario: Composición nueva
- **WHEN** una hoja nueva se fusiona por `BOND` a un holón raíz
- **THEN** en la Fase 5 de ese tick el motor reasigna los roles de todas las hojas del holón y actualiza `_role_leaf_sets`.

### Requirement: Regreso a NONE y Limpieza del Registro de Roles
El motor SHALL devolver a `NONE` las hojas que son su propia raíz y SHALL descartar de `_role_leaf_sets` las entradas de raíces que ya no existen.

#### Scenario: Hoja liberada por SPLIT
- **WHEN** un holón con roles asignados se disuelve por `SPLIT` y sus hojas quedan como raíces
- **THEN** al terminar la Fase 5 las hojas tienen `epigenetic_role is EpigeneticRole.NONE` y `_role_leaf_sets` no contiene el `node_id` del holón disuelto.

### Requirement: Impronta de Roles en la Reproducción Holónica
En la reproducción holónica ($R_{17}$), cada hoja hija SHALL recibir el rol de su progenitora y el motor SHALL registrar el conjunto de hojas de la réplica como ya asignado, de modo que la réplica conserva la impronta hasta que su composición cambie; sin $R_{17}$, un hijo individual nace solo y con `NONE`.

#### Scenario: Réplica con impronta
- **WHEN** con $R_{25}$ y $R_{17}$ activas se reproduce un holón cuyas hojas son `LIBRARIAN`, `EXPLORER` y `NERVE`
- **THEN** las hojas de la réplica nacen con esos mismos roles, en correspondencia con sus progenitoras, y la Fase 5 no los recalcula mientras la réplica conserve sus hojas.

### Requirement: Sello del Trinquete Simbiótico (R31)
`CompositeAgent` SHALL incorporar `is_locked: bool = False` y, con `enable_holonic_hierarchy` y `enable_symbiotic_ratchet` activas, un holón raíz SHALL quedar soldado al reproducirse por $R_{17}$ (el progenitor y su réplica) o, en el paso de coordinación de la Fase 5 y antes de evaluar `SPLIT`, si `cooperative_completions >= lock_composite_threshold`.

#### Scenario: Sello por compuestos resueltos
- **WHEN** con `lock_composite_threshold = 3` un holón raíz llega a `cooperative_completions == 3`
- **THEN** en el paso de coordinación de la Fase 5 de ese tick queda con `is_locked == True`, antes de evaluar `SPLIT`.

#### Scenario: Sello por reproducción
- **WHEN** con $R_{31}$ activa un holón raíz se reproduce por $R_{17}$
- **THEN** el progenitor y su réplica quedan con `is_locked == True`.

### Requirement: Efectos de un Holón Soldado
Con `enable_symbiotic_ratchet=True`, para un holón con `is_locked == True`, `should_split_holon` SHALL devolver `False`, por paciencia y por energía, y su costo de coordinación SHALL multiplicarse por `lock_coord_discount`. La estabilidad que produzca $R_{31}$ es por decreto, no un hallazgo.

#### Scenario: Holón soldado deficitario
- **WHEN** con `lock_coord_discount = 0.5` un holón soldado de 3 hojas y nivel 1 acumula `holon_split_patience` ticks sin superávit y su energía cae bajo $|U| \cdot E_{\text{min\_holon}}$
- **THEN** `should_split_holon` devuelve `False` y su costo de coordinación del tick es `0.5 * holon_coord_cost * 3 * 1` (con tolerancia `1e-9`).

### Requirement: Poda y Fusión de Holones Soldados
Un holón soldado SHALL seguir sujeto a la poda por muerte: conserva el sello si sobreviven dos o más hojas y colapsa como en la Fase II si queda una; SHALL poder fusionarse por `BOND` en un nivel superior y conservar su sello si después queda expuesto como raíz.

#### Scenario: Poda de un holón soldado
- **WHEN** en un holón soldado de 3 hojas muere una hoja, y después muere otra
- **THEN** tras la primera muerte el holón conserva `is_locked == True` con 2 hojas, y tras la segunda colapsa y la hoja restante queda como raíz.

#### Scenario: Sello conservado tras una fusión
- **WHEN** un holón soldado se fusiona por `BOND` en un holón de nivel superior que después se disuelve por `SPLIT`
- **THEN** el holón soldado vuelve a ser raíz con `is_locked == True`.
