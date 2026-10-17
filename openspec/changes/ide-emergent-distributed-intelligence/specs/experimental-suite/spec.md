# Spec Delta: Experimental Suite

## Purpose
Proveer el sistema de medición científica (`MetricsCollector`) para las métricas M1 a M7 y el ejecutor reproducible de los protocolos del Experimento 001 (001-A Base, 001-B Falsificación, 001-C Daño/Persistencia) con parámetros y reportes tipados exactos.

## ADDED Requirements

### Requirement: Cálculo Exacto de las Métricas Formales M1 a M7
El módulo `src/ide/experiments/metrics.py` SHALL calcular en cada tick un `TickMetrics` que contenga:
- **M1 (`individual_coverage_mean`, `collective_coverage`):** Cobertura epistémica individual media ($\le C_{\max}/N$) y cobertura colectiva de los $N$ patrones del mundo.
- **M2 (`decision_accuracy`, `cumulative_decision_accuracy`):** Ratio de decisiones correctas sobre el total de oportunidades de decisión en la celda actual (`is_reachable_now == True`). Una decisión se contabiliza como correcta si: (a) el agente ejecuta `INTERACT` sobre un recurso con `true_value > 0`, o (b) en la celda actual existen exclusivamente recursos dañinos (`true_value < 0`) y el agente decide evitarlos (`MOVE` o `IDLE`). Se contabiliza como incorrecta si: (c) ejecuta `INTERACT` sobre un recurso con `true_value < 0`, o (d) ignora una celda que contenía al menos un recurso benéfico (`true_value > 0`) sin consumir ninguno. Si una celda no tiene recursos alcanzables, no suma al denominador de oportunidades de decisión.
- **M3 (`pattern_prevalence`):** Diccionario con la fracción de agentes que sostienen conocimiento válido por cada patrón $\rho$.
- **M6 (`false_belief_prevalence`):** Fracción de agentes activos que sostienen una creencia con signo opuesto al valor real $F(\rho)$ y confianza $\ge c_{\text{umbral}}$.
- **M7 (`messages_per_agent`):** Total de mensajes transmitidos en el tick dividido entre el número de agentes activos.

#### Scenario: Invariante de límite superior en cobertura individual
- **WHEN** `MetricsCollector` evalúa cualquier población con $C_{\max} = 3$ y $N = 12$
- **THEN** `individual_coverage_mean` es siempre $\le 0.25$, mientras que `collective_coverage` puede alcanzar `1.0`.

#### Scenario: Contabilización exacta de acierto por evitación de recurso tóxico en M2
- **WHEN** un agente se encuentra en una celda que sólo contiene un recurso con `true_value = -1.0` y el agente ejecuta `ActionType.MOVE` sin interactuar con él
- **THEN** el evento se registra como 1 oportunidad de decisión y 1 decisión correcta (`decision_accuracy = 1.0`).

### Requirement: Ejecutor Automatizado de los Tres Protocolos del Experimento 001 con Firmas y Parámetros Exactos
El módulo `src/ide/experiments/exp001_runner.py` SHALL implementar tres funciones de protocolo reproducibles que retornen reportes `@dataclass(frozen=True)` serializables a JSON:
1. `run_protocol_001a_emergence(config: SimulationConfig, total_ticks: int = 300) -> EmergenceReport`: Compara una corrida con `comm_enabled=True` frente a `comm_enabled=False` y calcula `emergence_surplus = collective_accuracy - isolated_accuracy`.
2. `run_protocol_001b_falsification(config: SimulationConfig, total_ticks: int = 300, injection_tick: int = 80, injection_fraction: float = 0.25) -> FalsificationReport`: Inyecta una creencia falsa con confianza `0.95` sobre `Pattern((("id", "p_0"),))` (`false_value = -1.0` cuando el real es `+1.0`) en `injection_tick` y mide prevalencia en el momento de inyección, prevalencia pico y prevalencia final en `total_ticks`.
3. `run_protocol_001c_resilience(config: SimulationConfig, warmup_ticks: int = 150, post_ablation_ticks: int = 100, ablation_levels: tuple[float, ...] = (0.10, 0.30, 0.50, 0.70)) -> ResilienceReport`: Ejecuta ablación para cada fracción en `ablation_levels` (en corridas independientes clonadas de la misma semilla) y una corrida adicional invocando `ablate_discoverers(Pattern((("id", "p_0"),)), retire_stimulus=True)` para medir la persistencia extra-individual pura.

#### Scenario: Verificación de emergencia colectiva en Protocolo 001-A
- **WHEN** se ejecuta `run_protocol_001a_emergence(SimulationConfig(seed=42), total_ticks=300)`
- **THEN** `report.collective_coverage > report.isolated_coverage` y `report.emergence_surplus > 0.0`.

#### Scenario: Extinción o contención de creencia falsa en Protocolo 001-B
- **WHEN** se ejecuta `run_protocol_001b_falsification(SimulationConfig(seed=42), total_ticks=300, injection_tick=80, injection_fraction=0.25)`
- **THEN** `report.final_false_prevalence < report.initial_injected_prevalence`.
