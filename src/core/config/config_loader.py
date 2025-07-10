"""
Configuration Loader for CivicForge

Loads entity patterns and other configuration from YAML files,
allowing runtime updates without code changes.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """Loads and manages configuration from YAML files"""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            # Default to config directory relative to this file
            config_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.config_dir = Path(config_dir)
        self._cache = {}
    
    def load_entities(self) -> Dict[str, Any]:
        """Load entity patterns from entities.yaml"""
        if "entities" not in self._cache:
            entities_path = self.config_dir / "entities.yaml"
            self._cache["entities"] = self._load_yaml(entities_path)
        return self._cache["entities"]
    
    def reload_entities(self) -> Dict[str, Any]:
        """Force reload of entity patterns"""
        if "entities" in self._cache:
            del self._cache["entities"]
        return self.load_entities()
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load a YAML file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"Warning: Config file not found: {path}")
            return {}
        except yaml.YAMLError as e:
            print(f"Error loading YAML from {path}: {e}")
            return {}
    
    def get_skill_patterns(self) -> Dict[str, list]:
        """Get skill patterns from config"""
        entities = self.load_entities()
        return entities.get("skills", {})
    
    def get_time_patterns(self) -> Dict[str, Dict[str, list]]:
        """Get time-related patterns from config"""
        entities = self.load_entities()
        return {
            "days_of_week": entities.get("days_of_week", {}),
            "time_periods": entities.get("time_periods", {})
        }
    
    def get_location_patterns(self) -> Dict[str, list]:
        """Get location patterns from config"""
        entities = self.load_entities()
        return entities.get("location_types", {})
    
    def get_profession_mapping(self) -> Dict[str, str]:
        """Get profession to skill mapping"""
        entities = self.load_entities()
        return entities.get("professions", {})


# Singleton instance
_config_loader = None

def get_config_loader() -> ConfigLoader:
    """Get or create the singleton ConfigLoader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader