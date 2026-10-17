# Spec Delta: Bounded Memory

## Purpose
Proveer el subsistema de memoria local acotada (`BoundedMemory`) de cada micro-agente, garantizando el cumplimiento estricto de la capacidad máxima $C_{\max}$, el cálculo del índice de utilidad epistémica $U(k, t)$ para reemplazo selectivo y el decaimiento pasivo de confianza.

## ADDED Requirements

### Requirement: Límite Estricto de Capacidad Individual
La clase `BoundedMemory` en `src/ide/agent/memory.py` SHALL almacenar como máximo `capacity` ($C_{\max}$) instancias de `KnowledgeUnit` indexadas por `Pattern`.

#### Scenario: Inserción dentro del límite de capacidad
- **WHEN** `BoundedMemory(capacity=3)` contiene menos de 3 creencias y se inserta un nuevo `KnowledgeUnit` con un `Pattern` no existente
- **THEN** la creencia se almacena y `len(memory)` se incrementa en 1 sin exceder `capacity`.

#### Scenario: Actualización de patrón ya existente en memoria llena
- **WHEN** `BoundedMemory(capacity=3)` ya contiene 3 creencias y se ejecuta `upsert` de un `KnowledgeUnit` cuyo `Pattern` ya existe en la memoria
- **THEN** la entrada existente se reemplaza con la versión actualizada y `len(memory)` permanece exactamente en 3.

### Requirement: Índice de Utilidad Epistémica y Política de Reemplazo
Cuando `BoundedMemory` esté llena (`len(memory) == capacity`) y reciba un `KnowledgeUnit` con un patrón nuevo, SHALL calcular la utilidad epistémica de cada creencia según la fórmula:
$$U(k, t) = c \cdot \max(|\hat{v}|, 0.1) \cdot e^{-\lambda (t - \tau)}$$
y sólo reemplazará la creencia de menor utilidad si $U(k_{\text{nueva}}, t) > \min_{k \in \mathcal{M}} U(k, t)$. En caso de empate en utilidad mínima, desempatará eliminando la creencia con menor `last_updated_tick` ($\tau$).

#### Scenario: Reemplazo de creencia obsoleta y de baja confianza por una nueva de alta utilidad
- **WHEN** una memoria de capacidad 2 contiene $k_1$ ($c=0.9, |\hat{v}|=1.0, \tau=10$) y $k_2$ ($c=0.2, |\hat{v}|=1.0, \tau=1$) y en el tick $t=10$ intenta ingresar $k_3$ ($c=0.85, |\hat{v}|=1.0, \tau=10$)
- **THEN** $k_2$ es expulsada de la memoria, $k_3$ ocupa su lugar y $k_1$ se conserva intacta.

#### Scenario: Rechazo de rumor débil frente a memoria saturada de alta certeza
- **WHEN** todas las creencias en una memoria llena tienen utilidad $U(k, t) > 0.8$ y se intenta insertar una creencia nueva con baja utilidad $U(k_{\text{nueva}}, t) = 0.25$
- **THEN** `upsert` devuelve `False` y la memoria conserva sus creencias originales sin cambios.

### Requirement: Decaimiento Pasivo y Purga por Umbral Mínimo
El método `decay_step(current_tick: int, passive_decay: float, min_confidence: float)` SHALL reducir en cada tick la confianza de toda creencia que no haya sido actualizada en `current_tick` en `passive_decay` unidades, eliminando automáticamente aquellas cuya confianza caiga por debajo de `min_confidence`.

#### Scenario: Eliminación de creencia degradada por falta de revalidación
- **WHEN** una creencia tiene `confidence = 0.06`, `min_confidence = 0.05`, `passive_decay = 0.02` y no fue actualizada en el tick actual
- **THEN** tras invocar `decay_step`, su confianza cae a `0.04` y es purgada automáticamente de `BoundedMemory`.
