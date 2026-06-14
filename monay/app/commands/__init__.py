"""Spec-driven command registry: parser + autocomplete + help + execution."""

from .registry import CommandRegistry, CommandSpec, Result
from .specs import REGISTRY, build_registry

__all__ = ["CommandRegistry", "CommandSpec", "Result", "REGISTRY", "build_registry"]