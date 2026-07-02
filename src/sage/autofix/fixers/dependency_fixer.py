"""Dependency fixer for package management issues."""

from __future__ import annotations

from ..analyzers import ErrorAnalysis


class DependencyFixer:
    """Generates fixes for dependency issues."""

    confidence = 0.90

    def can_fix(self, analysis: ErrorAnalysis) -> bool:
        """Check if this is a dependency error."""
        return analysis.error_type == "missing_module"

    def generate_fix(self, analysis: ErrorAnalysis) -> str:
        """Generate dependency fix."""
        module = analysis.details.get("module", "")
        
        if analysis.language == "python":
            # Common Python package name mappings
            package_map = {
                "PIL": "pillow",
                "cv2": "opencv-python",
                "sklearn": "scikit-learn",
                "yaml": "pyyaml",
            }
            package = package_map.get(module, module)
            return f"pip install {package}"
        
        elif analysis.language in ["javascript", "typescript"]:
            return f"npm install {module}"
        
        return f"Install {module}"
