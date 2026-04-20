"""
Stap 0: IFC-bestand inladen en versie detecteren
"""

from .ifc_loader import IFCLoader
from .version_detector import VersionDetector
from .version_strategies import get_strategy

__all__ = ['IFCLoader', 'VersionDetector', 'get_strategy']