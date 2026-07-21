"""SAGE Enhanced Code Generation System.

Provides intelligent code generation with:
- Pattern detection from codebase
- Style enforcement
- Deep context awareness
- AST-based validation
- Smart file reading
- Tool orchestration
- Safe code modification
"""

from .validators import (
    ValidationIssue,
    ValidationResult,
    Validator,
    ValidatorRegistry,
    ASTValidator,
    SecurityValidator,
    QualityValidator,
    create_default_registry,
)
from .pattern_detector import PatternDetector, DetectedPattern
from .style_enforcer import StyleEnforcer, StyleProfile, StyleViolation
from .context_builder import ContextBuilder, FileContext, ImportInfo, FunctionInfo, ClassInfo
from .smart_reader import SmartReader, ReadStrategy, ReadResult
from .tool_orchestrator import ToolOrchestrator, ToolPlan, ToolCall, ToolResult, ToolType
from .safe_modifier import SafeModifier, FileSnapshot, ModificationResult

__all__ = [
    # Validators
    "ValidationIssue",
    "ValidationResult",
    "Validator",
    "ValidatorRegistry",
    "ASTValidator",
    "SecurityValidator",
    "QualityValidator",
    "create_default_registry",
    # Pattern detection
    "PatternDetector",
    "DetectedPattern",
    # Style enforcement
    "StyleEnforcer",
    "StyleProfile",
    "StyleViolation",
    # Context building
    "ContextBuilder",
    "FileContext",
    "ImportInfo",
    "FunctionInfo",
    "ClassInfo",
    # Smart reading
    "SmartReader",
    "ReadStrategy",
    "ReadResult",
    # Tool orchestration
    "ToolOrchestrator",
    "ToolPlan",
    "ToolCall",
    "ToolResult",
    "ToolType",
    # Safe modification
    "SafeModifier",
    "FileSnapshot",
    "ModificationResult",
]
