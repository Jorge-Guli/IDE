"""Configuración global de la suite: perfil reproducible de Hypothesis."""

from hypothesis import settings

settings.register_profile("ci", derandomize=True, deadline=None, max_examples=200)
settings.load_profile("ci")
