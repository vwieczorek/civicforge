"""
Configuration module for CivicForge

Manages externalized configuration for entity patterns and other settings.
"""

from .config_loader import ConfigLoader, get_config_loader

__all__ = ["ConfigLoader", "get_config_loader"]