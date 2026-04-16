import re
from config.config import IFCVersion, IFC_VERSION_MAP
from core.logger import setup_logger

logger = setup_logger(__name__)

class VersionDetector:
    """
    Geautomatiseerde detectie van de IFC-versie uit het bestand.
    """
    
    def __init__(self, ifc_file):
        """
        Initialiseer detector met geladen IFC-bestand.
        
        Args:
            ifc_file: ifcopenshell file object
        """
        self.ifc_file = ifc_file
        self.detected_version = None
        self.version_enum = None
        
    def detect(self):
        """
        Detecteer IFC-versie door meerdere methodes te proberen.
        
        Returns:
            tuple: (versie_string, IFCVersion enum)
        """
        logger.info("Start IFC-versie detectie...")
        
        # Methode 1: Gebruik ifcopenshell's ingebouwde schema detectie
        version_via_schema = self._detect_via_schema()
        if version_via_schema:
            self.detected_version = version_via_schema
            self.version_enum = IFC_VERSION_MAP.get(version_via_schema)
            logger.info(f"✓ IFC-versie gedetecteerd (via schema): {self.detected_version}")
            return self.detected_version, self.version_enum
        
        # Methode 2: Parse FILE_SCHEMA header
        version_via_header = self._detect_via_header()
        if version_via_header:
            self.detected_version = version_via_header
            self.version_enum = IFC_VERSION_MAP.get(version_via_header)
            logger.info(f"✓ IFC-versie gedetecteerd (via header): {self.detected_version}")
            return self.detected_version, self.version_enum
        
        # Methode 3: Fallback - inspecteer aanwezige entiteiten
        version_via_entities = self._detect_via_entities()
        if version_via_entities:
            logger.warning(f"⚠ IFC-versie geschat op basis van entiteiten: {version_via_entities}")
            self.detected_version = version_via_entities
            self.version_enum = IFC_VERSION_MAP.get(version_via_entities, IFCVersion.IFC_4_0)
            return self.detected_version, self.version_enum
        
        logger.error("✗ Kon IFC-versie niet detecteren - standaard op 4.0")
        self.detected_version = "4.0"
        self.version_enum = IFCVersion.IFC_4_0
        return self.detected_version, self.version_enum
    
    def _detect_via_schema(self):
        """
        Probeer versie via ifcopenshell's schema eigenschap te detecteren.
        
        Returns:
            str met versie of None
        """
        try:
            # ifcopenshell heeft een schema property
            schema = self.ifc_file.schema
            # Formaat is meestal "IFC2X3", "IFC4", "IFC4X1", "IFC4X3"
            version_map = {
                "IFC2X3": "2.3",
                "IFC4": "4.0",
                "IFC4X1": "4.1",
                "IFC4X3": "4.3",
            }
            return version_map.get(schema)
        except Exception as e:
            logger.debug(f"Schema detectie mislukt: {e}")
            return None
    
    def _detect_via_header(self):
        """
        Parse de FILE_SCHEMA regel uit de IFC-headerinfo.
        
        Returns:
            str met versie of None
        """
        try:
            # Lees de eerste regels van het bestand
            with open(self.ifc_file.wrapped_data.file_name if hasattr(self.ifc_file.wrapped_data, 'file_name') else "", 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(2000)  # Eerste 2000 chars
                
                # Zoek naar FILE_SCHEMA regel
                schema_match = re.search(r"FILE_SCHEMA\s*\(\s*\('([^']+)'\)", content)
                if schema_match:
                    schema_str = schema_match.group(1)
                    # Normaliseer naar standaardformaat
                    if "2" in schema_str and "3" in schema_str:
                        return "2.3"
                    elif "4" in schema_str:
                        if "3" in schema_str:
                            return "4.3"
                        elif "1" in schema_str:
                            return "4.1"
                        else:
                            return "4.0"
        except Exception as e:
            logger.debug(f"Header detectie mislukt: {e}")
        
        return None
    
    def _detect_via_entities(self):
        """
        Schat versie op basis van aanwezige entiteiten.
        IFC 4.x heeft meer entiteiten dan 2.3.
        
        Returns:
            str met versie of None
        """
        try:
            all_entities = self.ifc_file.wrapped_data.entity_names() if hasattr(self.ifc_file.wrapped_data, 'entity_names') else []
            entity_count = len(all_entities)
            
            # IFC 2.3 heeft ongeveer 200-250 entiteiten
            # IFC 4.0/4.1/4.3 hebben meer (300+)
            if entity_count < 280:
                return "2.3"
            else:
                # Voor 4.0, 4.1, 4.3 verschil: 4.3 heeft MOSTENTITEITEN
                return "4.0"  # Default fallback
        except Exception as e:
            logger.debug(f"Entity-based detectie mislukt: {e}")
            return None
    
    def get_detected_version(self):
        """Retourneer gedetecteerde versie."""
        return self.detected_version, self.version_enum