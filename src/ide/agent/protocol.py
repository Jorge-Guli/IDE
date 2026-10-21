"""Semántica de comunicación por defecto (Decisión 14): única fuente de `Message`."""

from typing import TYPE_CHECKING

from ide.agent.epistemology import is_known
from ide.domain.types import Message, MessageType, Observation, Pattern

if TYPE_CHECKING:
    from ide.agent.micro_agent import MicroAgent

_TESTIMONY_TYPES = (MessageType.BROADCAST_BELIEF, MessageType.QUERY_RESPONSE)


class BeliefExchangeProtocol:
    """Consultas en vivo (R9) y difusión de creencias confiables (R8), sin estado propio.

    Puerta de comunicación (R32, D46.6): un agente con `communicates == False` no emite ni
    responde consultas, pero sigue recibiendo y asimilando testimonios. No consume generadores.
    """

    def emit(self, agent: "MicroAgent", obs: Observation, tick: int) -> list[Message]:
        """Primero las consultas por patrones visibles no conocidos; luego los broadcasts."""
        if not obs.neighbor_ids or not agent.communicates:
            return []
        config = agent.config

        nearest: dict[Pattern, int] = {}
        for res in obs.visible_resources:
            nearest[res.pattern] = min(nearest.get(res.pattern, res.distance), res.distance)
        unknown = sorted(
            (distance, pattern)
            for pattern, distance in nearest.items()
            if not is_known(agent.get_effective_belief(pattern), config)
        )
        queries = [
            Message(MessageType.QUERY_PATTERN, agent.agent_id, None, pattern)
            for _, pattern in unknown[: config.max_queries_per_tick]
        ]

        memory = agent.memory
        reliable = sorted(
            (unit for unit in memory.all_units() if is_known(unit, config)),
            key=lambda u: (-memory.compute_utility(u, tick), u.pattern),
        )
        broadcasts = [
            Message(MessageType.BROADCAST_BELIEF, agent.agent_id, None, unit.pattern, unit)
            for unit in reliable[: config.max_broadcast_per_tick]
        ]
        return queries + broadcasts

    def receive(self, agent: "MicroAgent", messages: list[Message], tick: int) -> list[Message]:
        """Responde consultas desde memoria y luego asimila testimonios, en el orden recibido."""
        inbox = [
            msg
            for msg in messages
            if msg.sender_id != agent.agent_id
            and (msg.recipient_id is None or msg.recipient_id == agent.agent_id)
        ]
        # Las consultas se responden antes de asimilar nada: el orden de la bandeja sigue la
        # permutación del tick y no debe alterar el contenido de una respuesta (Decisión 15).
        # El caché efímero no se re-difunde: sólo responde lo que el agente sostiene en memoria.
        responses: list[Message] = []
        queries = inbox if agent.communicates else []  # puerta de D46.6: sin respuestas
        for msg in queries:
            if msg.msg_type is not MessageType.QUERY_PATTERN:
                continue
            unit = agent.memory.get(msg.pattern)
            if is_known(unit, agent.config):
                responses.append(
                    Message(
                        MessageType.QUERY_RESPONSE, agent.agent_id, msg.sender_id, msg.pattern, unit
                    )
                )
        for msg in inbox:
            if msg.msg_type in _TESTIMONY_TYPES and msg.belief is not None:
                agent.assimilate_testimony(msg.belief, msg.sender_id, tick)
        return responses
