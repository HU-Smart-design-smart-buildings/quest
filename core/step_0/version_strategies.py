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


class IFC23Strategy:
    """
    Versiespecifieke strategie voor IFC 2.3
    """
    
    def __init__(self, ifc_file):
        self.ifc_file = ifc_file
    
    def get_building_elements(self):
        """
        Haal alle bouwkundige elementen op (IFC 2.3 stijl).
        
        IFC 2.3 gebruikt PascalCase: IfcWall, IfcDoor, IfcWindow
        IFC 4.x gebruikt UPPERCASE: IFCWALL, IFCDOOR, IFCWINDOW
        """
        # Map van IFC 2.3 naming -> genormaliseerd
        ifc23_elements = {
            'IfcWall',
            'IfcDoor',
            'IfcWindow',
            'IfcBeam',
            'IfcColumn',
            'IfcSlab',
            'IfcMember',
            'IfcCurtainWall',
            'IfcRoof',
            'IfcBuildingElementProxy',
            'IfcPlate',
            'IfcCovering',
            'IfcFooting',
            'IfcStair',
            'IfcBuildingElementPart',
            'IfcElementAssembly',
            'IfcDuctSegment',
            'IfcPipeSegment',
            'IfcRailing'
        }
        
        return ifc23_elements


class IFC40Strategy:
    """
    Versiespecifieke strategie voor IFC 4.0
    """
    
    def __init__(self, ifc_file):
        self.ifc_file = ifc_file
    
    def get_building_elements(self):
        """
        Haal alle bouwkundige elementen op (IFC 4.0 stijl).
        
        IFC 4.0+ gebruikt UPPERCASE: IFCWALL, IFCDOOR, IFCWINDOW
        """
        ifc40_elements = {
            'IFCWALL',
            'IFCDOOR',
            'IFCWINDOW',
            'IFCBEAM',
            'IFCCOLUMN',
            'IFCSLAB',
            'IFCMEMBER',
            'IFCCURTAINWALL',
            'IFCROOF',
            'IFCBUILDINGELEMENTPROXY',
            'IFCPLATE',
            'IFCCOVERING',
            'IFCFOOTING',
            'IFCSTAIR',
            'IFCBUILDINGELEMENTPART',
            'IFCELEMENTASSEMBLY',
            'IFCDUCTSEGMENT',
            'IFCPIPESEGMENT',
            'IFCRAILING'
        }
        
        return ifc40_elements


class IFC41Strategy(IFC40Strategy):
    """
    Versiespecifieke strategie voor IFC 4.1
    (Dezelfde als 4.0)
    """
    pass


class IFC43Strategy(IFC40Strategy):
    """
    Versiespecifieke strategie voor IFC 4.3
    (Dezelfde als 4.0)
    """
    pass


def get_strategy(ifc_file, ifc_version_enum):
    """
    Retourneer de juiste strategie gebaseerd op IFC-versie.
    """
    from config.config import IFCVersion
    
    strategy_map = {
        IFCVersion.IFC_2_3: IFC23Strategy,
        IFCVersion.IFC_4_0: IFC40Strategy,
        IFCVersion.IFC_4_1: IFC41Strategy,
        IFCVersion.IFC_4_3: IFC43Strategy,
    }
    
    strategy_class = strategy_map.get(ifc_version_enum, IFC40Strategy)
    return strategy_class(ifc_file)