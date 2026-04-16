import ifcopenshell
from pathlib import Path
from core.logger import setup_logger

logger = setup_logger(__name__)

class IFCLoader:
    """
    Verantwoordelijk voor het inladen en valideren van IFC-bestanden.
    """
    
    def __init__(self, ifc_file_path):
        """
        Initialiseer de loader met een IFC-bestandspad.
        
        Args:
            ifc_file_path: Path naar het IFC-bestand
        """
        self.ifc_file_path = Path(ifc_file_path)
        self.ifc_file = None
        self.is_valid = False
        self.file_info = {}
        
    def validate_file(self):
        """
        Controleer of het bestand bestaat en een geldig IFC-bestand is.
        
        Returns:
            bool: True als geldig, False anders
        """
        logger.info(f"Valideer IFC-bestand: {self.ifc_file_path}")
        
        # Controleer bestandsexistentie
        if not self.ifc_file_path.exists():
            logger.error(f"Bestand niet gevonden: {self.ifc_file_path}")
            return False
        
        # Controleer bestandsextensie
        if self.ifc_file_path.suffix.lower() not in [".ifc", ".ifczip"]:
            logger.warning(f"Onverwachte bestandsextensie: {self.ifc_file_path.suffix}")
        
        # Probeer bestand in te laden
        try:
            self.ifc_file = ifcopenshell.open(str(self.ifc_file_path))
            self.is_valid = True
            self.file_info["bestandsgrootte_mb"] = self.ifc_file_path.stat().st_size / (1024 * 1024)
            logger.info(f"✓ IFC-bestand succesfully ingeladen")
            return True
        except Exception as e:
            logger.error(f"Fout bij het inladen van IFC-bestand: {e}")
            return False
    
    def get_file_object(self):
        """
        Retourneer het geladen IFC-bestand object.
        
        Returns:
            ifcopenshell file object of None
        """
        return self.ifc_file if self.is_valid else None
    
    def get_file_info(self):
        """
        Retourneer basisinformatie over het bestand.
        
        Returns:
            dict met bestandsinformatie
        """
        return self.file_info