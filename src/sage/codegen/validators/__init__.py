"""SAGE codegen validators package."""

from .base import ValidationIssue, ValidationResult, Validator, ValidatorRegistry
from .ast_validator import ASTValidator
from .security_validator import SecurityValidator
from .quality_validator import QualityValidator

__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "Validator",
    "ValidatorRegistry",
    "ASTValidator",
    "SecurityValidator",
    "QualityValidator",
]


def create_default_registry() -> ValidatorRegistry:
    """Create a registry with all default validators."""
    registry = ValidatorRegistry()
    registry.register(ASTValidator())
    registry.register(SecurityValidator())
    registry.register(QualityValidator())
    return registry
