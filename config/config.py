import os
from pathlib import Path
from enum import Enum

# Basispadstructuur
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"

# Zorg dat directories bestaan
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# IFC-versies die we ondersteunen
class IFCVersion(Enum):
    IFC_2_3 = "2.3"
    IFC_4_0 = "4.0"
    IFC_4_1 = "4.1"
    IFC_4_3 = "4.3"

# Mapping van versie-strings naar enum
IFC_VERSION_MAP = {
    "2.3": IFCVersion.IFC_2_3,
    "4.0": IFCVersion.IFC_4_0,
    "4.1": IFCVersion.IFC_4_1,
    "4.3": IFCVersion.IFC_4_3,
}

# Bouwkundige elementen per versie
BUILDING_ELEMENTS = {
    IFCVersion.IFC_2_3: [
        "IFCWALL", "IFCDOOR", "IFCWINDOW", "IFCBEAM", 
        "IFCCOLUMN", "IFCSLAB", "IFCMEMBER", "IFCROOF"
    ],
    IFCVersion.IFC_4_0: [
        "IFCWALL", "IFCDOOR", "IFCWINDOW", "IFCBEAM", 
        "IFCCOLUMN", "IFCSLAB", "IFCMEMBER", "IFCCURTAINWALL", 
        "IFCROOF", "IFCBUILDINGELEMENTPROXY"
    ],
    IFCVersion.IFC_4_1: [
        "IFCWALL", "IFCDOOR", "IFCWINDOW", "IFCBEAM", 
        "IFCCOLUMN", "IFCSLAB", "IFCMEMBER", "IFCCURTAINWALL", 
        "IFCROOF", "IFCBUILDINGELEMENTPROXY"
    ],
    IFCVersion.IFC_4_3: [
        "IFCWALL", "IFCDOOR", "IFCWINDOW", "IFCBEAM", 
        "IFCCOLUMN", "IFCSLAB", "IFCMEMBER", "IFCCURTAINWALL", 
        "IFCROOF", "IFCBUILDINGELEMENTPROXY"
    ],
}

# Logging configuratie
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"