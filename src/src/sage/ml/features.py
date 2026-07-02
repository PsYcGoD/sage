"""Feature extraction for ML prediction."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List


class FeatureExtractor:
    """Extract features from command and context for ML prediction."""

    def extract(self, command: str, context: Dict = None) -> Dict[str, float]:
        """
        Extract features from command and context.
        
        Returns dict of feature_name -> feature_value.
        """
        context = context or {}
        features = {}

        # Command-based features
        features['cmd_length'] = len(command)
        features['has_test_keyword'] = 1.0 if any(
            word in command.lower() for word in ['test', 'pytest', 'unittest', 'jest']
        ) else 0.0
        features['has_build_keyword'] = 1.0 if any(
            word in command.lower() for word in ['build', 'compile', 'make']
        ) else 0.0
        features['has_install_keyword'] = 1.0 if any(
            word in command.lower() for word in ['install', 'pip', 'npm', 'yarn']
        ) else 0.0

        # Time-based features
        now = datetime.now()
        features['hour_of_day'] = now.hour
        features['is_monday'] = 1.0 if now.weekday() == 0 else 0.0
        features['is_friday'] = 1.0 if now.weekday() == 4 else 0.0

        # Context-based features
        features['minutes_since_last_failure'] = context.get('minutes_since_last_failure', 1440.0)
        features['num_recent_failures'] = context.get('num_recent_failures', 0.0)
        features['num_recent_changes'] = context.get('num_recent_changes', 0.0)

        # Project-based features
        project_path = Path.cwd()
        features['has_requirements_txt'] = 1.0 if (project_path / 'requirements.txt').exists() else 0.0
        features['has_package_json'] = 1.0 if (project_path / 'package.json').exists() else 0.0
        features['has_tests_dir'] = 1.0 if (project_path / 'tests').exists() else 0.0

        return features

    def get_feature_names(self) -> List[str]:
        """Get list of feature names in order."""
        return [
            'cmd_length',
            'has_test_keyword',
            'has_build_keyword',
            'has_install_keyword',
            'hour_of_day',
            'is_monday',
            'is_friday',
            'minutes_since_last_failure',
            'num_recent_failures',
            'num_recent_changes',
            'has_requirements_txt',
            'has_package_json',
            'has_tests_dir',
        ]
