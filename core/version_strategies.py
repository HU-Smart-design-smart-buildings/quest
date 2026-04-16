from config.config import IFCVersion
from core.logger import setup_logger

logger = setup_logger(__name__)

# Alle bouwkundige elementen die we willen verwerken (uniform voor alle versies)
UNIVERSAL_BUILDING_ELEMENTS = [
    "IFCWALL", "IFCDOOR", "IFCWINDOW", "IFCBEAM", 
    "IFCCOLUMN", "IFCSLAB", "IFCMEMBER", "IFCCURTAINWALL", 
    "IFCROOF", "IFCBUILDINGELEMENTPROXY"
]

class VersionStrategy:
    """
    Base class voor versiespecifieke extractielogica.
    """
    
    def __init__(self, ifc_file, ifc_version):
        self.ifc_file = ifc_file
        self.ifc_version = ifc_version
    
    def get_building_elements(self):
        """Retourneer uniform lijst van bouwkundige elementen voor ALLE versies."""
        return UNIVERSAL_BUILDING_ELEMENTS
    
    def extract_material_info(self, element):
        """Versiespecifieke materiaal-extractie."""
        raise NotImplementedError


class IFC23Strategy(VersionStrategy):
    """Extractiestrategie voor IFC 2.3"""
    
    def __init__(self, ifc_file):
        super().__init__(ifc_file, IFCVersion.IFC_2_3)
        logger.info("IFC 2.3 strategie geladen")
    
    def get_building_elements(self):
        """Retourneer dezelfde elementen als andere versies."""
        return UNIVERSAL_BUILDING_ELEMENTS
    
    def extract_material_info(self, element):
        """IFC 2.3 materialenextractie"""
        # Implementatie volgt in volgende fases
        pass


class IFC40Strategy(VersionStrategy):
    """Extractiestrategie voor IFC 4.0"""
    
    def __init__(self, ifc_file):
        super().__init__(ifc_file, IFCVersion.IFC_4_0)
        logger.info("IFC 4.0 strategie geladen")
    
    def get_building_elements(self):
        """Retourneer dezelfde elementen als andere versies."""
        return UNIVERSAL_BUILDING_ELEMENTS
    
    def extract_material_info(self, element):
        """IFC 4.0 materialenextractie"""
        pass


class IFC41Strategy(VersionStrategy):
    """Extractiestrategie voor IFC 4.1"""
    
    def __init__(self, ifc_file):
        super().__init__(ifc_file, IFCVersion.IFC_4_1)
        logger.info("IFC 4.1 strategie geladen")
    
    def get_building_elements(self):
        """Retourneer dezelfde elementen als andere versies."""
        return UNIVERSAL_BUILDING_ELEMENTS
    
    def extract_material_info(self, element):
        """IFC 4.1 materialenextractie"""
        pass

class IFC43Strategy(VersionStrategy):
    """Extractiestrategie voor IFC 4.3"""
    
    def __init__(self, ifc_file):
        super().__init__(ifc_file, IFCVersion.IFC_4_3)
        logger.info("IFC 4.3 strategie geladen")
    
    def get_building_elements(self):
        """Retourneer dezelfde elementen als andere versies."""
        return UNIVERSAL_BUILDING_ELEMENTS
    
    def extract_material_info(self, element):
        """IFC 4.3 materialenextractie"""
        pass


def get_strategy(ifc_file, ifc_version_enum):
    """
    Factory-functie om de juiste strategie te retourneren.
    
    Args:
        ifc_file: ifcopenshell file object
        ifc_version_enum: IFCVersion enum
    
    Returns:
        VersionStrategy subclass instance
    """
    strategies = {
        IFCVersion.IFC_2_3: IFC23Strategy,
        IFCVersion.IFC_4_0: IFC40Strategy,
        IFCVersion.IFC_4_1: IFC41Strategy,
        IFCVersion.IFC_4_3: IFC43Strategy,
    }
    
    strategy_class = strategies.get(ifc_version_enum, IFC40Strategy)
    return strategy_class(ifc_file)