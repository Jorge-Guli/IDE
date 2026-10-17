# Spec Delta: Evolutionary Dynamics

## Purpose

Proveer la dinámica darwiniana y lamarckiana acotada del sistema: metabolismo energético individual con costo cerebral cuadrático ($C_{\max}^2$), muerte por inanición, reproducción diferencial con partición conservativa de energía ($R_{12}$), genoma mutable `AgentGenome` ($R_{13}$) y transferencia cultural vertical de creencias madre-hijo con descuento intergeneracional $\gamma_{\text{gen}}$ ($R_{14}$).

## ADDED Requirements

### Requirement: Metabolismo Energético con Penalización Cuadrática de Capacidad y Radios
Cuando `enable_evolution=True`, cada `MicroAgent` SHALL iniciar con energía `initial_energy` ($E_0$), descontar por tick el costo basal $c_{\text{fijo}} + c_{\text{mem}} C_{\max, i}^2 + c_{\text{sens}}(r_{\text{perc}, i}^2 + r_{\text{com}, i}^2)$ más $c_{\text{move}}$ (si se movió) y $c_{\text{msg}} m_i$, y sumar $\eta_E \cdot v$ al consumir un recurso de valor $v$.

#### Scenario: Penalización cuadrática del cerebro individual
- **WHEN** dos agentes en reposo y sin emitir mensajes tienen capacidades $C_{\max} = 3$ y $C_{\max} = 6$ respectivamente, con `metabolic_base_cost = 0.02`, `memory_capacity_cost = 0.005` y `sensory_radius_cost = 0.0`
- **THEN** tras un tick el primero pierde `0.02 + 0.005 * 9 = 0.065` de energía y el segundo pierde `0.02 + 0.005 * 36 = 0.200` de energía (con tolerancia `1e-9`).

#### Scenario: Ganancia y pérdida por interacción con recursos
- **WHEN** un agente con energía `1.0` consume un recurso benéfico de valor `+1.0` con `energy_gain_scale = 0.5`
- **THEN** antes del descuento basal su energía aumenta a `1.5`, y si consume uno dañino de valor `-1.0` disminuye a `0.5`.

### Requirement: Muerte por Agotamiento Energético
En la Fase 5 de cada tick con `enable_evolution=True`, todo `MicroAgent` cuya energía resultante cumpla $E_i(t) \le 0$ SHALL ser eliminado del motor, del entorno espacial y podado de cualquier árbol holónico antes de la fase de reproducción, incrementando el contador `deaths_this_tick`.

#### Scenario: Eliminación por inanición
- **WHEN** la energía de un agente cae a `0.0` o a un valor negativo al finalizar el cobro metabólico de la Fase 5
- **THEN** el agente deja de figurar en `engine.agents` y en `env.get_active_agent_ids()` en ese mismo tick.

### Requirement: Reproducción Diferencial con Partición Conservativa y Límite de Un Evento por Tick (R12)
En la Fase 5 con `enable_evolution=True`, todo `MicroAgent` sobreviviente no reproducido aún en ese tick cuya energía cumpla $E_i(t) \ge E_{\text{reprod}}$ SHALL engendrar a lo sumo un hijo (en orden ascendente de `agent_id`) si `len(agents) < max_population`, reteniendo $(1 - \kappa_{\text{part}}) E_i(t)$ y transfiriendo $\kappa_{\text{part}} E_i(t)$ al hijo.

#### Scenario: Partición exacta de energía y linaje
- **WHEN** el agente 4 con generación `g = 2` alcanza energía `2.4` con `reproduction_threshold = 2.0`, `offspring_energy_share = 0.5` y hay cupo bajo `max_population`
- **THEN** nace un nuevo agente con `parent_id == 4`, `generation == 3`, `energy == 1.2`, y el agente 4 queda con `energy == 1.2` (con tolerancia `1e-9`), conservando la suma total `2.4`.

#### Scenario: Respeto estricto de la capacidad de carga
- **WHEN** la población activa ya tiene `len(engine.agents) == max_population` y un agente supera `reproduction_threshold`
- **THEN** no nace ningún descendiente y el agente conserva su energía íntegra.

### Requirement: Herencia Genética con Mutación Acotada (R13)
Al reproducirse un agente con `mutation_rate > 0` o `discrete_mutation_prob > 0`, el `AgentGenome` del hijo SHALL derivarse del parental aplicando ruido normal $\mathcal{N}(0, \sigma_{\text{mut}}^2)$ a los rasgos continuos y saltos en $\{-1, 0, +1\}$ a los discretos dentro de sus cotas válidas; si ambos son `0.0`, SHALL clonarse sin consumir extracciones del RNG.

#### Scenario: Clonación exacta bajo ablación de mutación
- **WHEN** un agente se reproduce con `mutation_rate = 0.0` y `discrete_mutation_prob = 0.0`
- **THEN** `child.genome == parent.genome`.

#### Scenario: Mutación acotada dentro de invariantes de dominio
- **WHEN** se muta repetidamente un `AgentGenome` durante 500 eventos reproductivos con `mutation_rate = 0.2` y `discrete_mutation_prob = 0.5`
- **THEN** todos los coeficientes continuos permanecen en `[0.0, 1.0]` (`alpha_learning` en `[0.01, 1.0]`), `memory_capacity` permanece en `[1, max_genome_memory_capacity]` y además `< num_world_patterns` cuando `enforce_memory_constraint=True`, y los radios permanecen en `[1, (min(grid_width, grid_height) - 1) // 2]`, de modo que `SimulationConfig` acepta el genoma del hijo.

### Requirement: Herencia Cultural Vertical con Descuento Intergeneracional (R14)
Con `enable_cultural_inheritance=True` e `inheritance_discount > 0`, el motor SHALL entregar al hijo, por `assimilate_testimony` con `sender_id = parent_id`, hasta $\min(C_{\max, \text{hijo}}, |\mathcal{M}_{\text{padre}}|)$ creencias parentales en orden descendente de $U(k, t)$, con confianza `gamma_gen * k.confidence` antes del descuento social, sólo si `gamma * gamma_gen * k.confidence >= c_min`.

#### Scenario: Transferencia epigénica con invariante no empírico
- **WHEN** un padre con creencia directa $k(\rho_1, \hat{v}=+1.0, c=0.80, n=5, \text{direct}=True)$ se reproduce en `tick = 50` con `enable_cultural_inheritance=True`, `inheritance_discount = 0.5`, `gamma_social_discount = 0.75` y confianza uniforme en el emisor
- **THEN** el hijo nace con $k_{\text{hijo}}(\rho_1)$ en su memoria con `predicted_value == 1.0`, `confidence == 0.30` (`0.75 * 0.5 * 0.80`, con tolerancia `1e-9`), `evidence_count == 1`, `last_updated_tick == 50` y `from_direct_experience == False`.

#### Scenario: Ablación de herencia cultural (Tabula Rasa)
- **WHEN** `enable_cultural_inheritance=False` o `inheritance_discount == 0.0`
- **THEN** la `BoundedMemory` del recién nacido está vacía (`len(child.memory) == 0`).
