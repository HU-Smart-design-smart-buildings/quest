import sys
from pathlib import Path
from core.ifc_loader import IFCLoader
from core.version_detector import VersionDetector
from core.version_strategies import get_strategy
from core.logger import setup_logger

logger = setup_logger(__name__, "quest_main.log")

def execute_step_0(ifc_file_path):
    """
    Voer Stap 0 uit: IFC-bestand inladen, versie detecteren en strategie selecteren.
    
    Args:
        ifc_file_path: Path naar het IFC-bestand
    
    Returns:
        dict met resultaten van Stap 0
    """
    logger.info("=" * 60)
    logger.info("STAP 0: IFC-bestand inladen en versie detecteren")
    logger.info("=" * 60)
    
    # Stap 1: Valideer en laad het IFC-bestand
    loader = IFCLoader(ifc_file_path)
    if not loader.validate_file():
        logger.error("Kon IFC-bestand niet inladen. Stoppen.")
        return None
    
    ifc_file = loader.get_file_object()
    file_info = loader.get_file_info()
    
    # Stap 2: Detecteer IFC-versie
    detector = VersionDetector(ifc_file)
    version_string, version_enum = detector.detect()
    
    # Stap 3: Selecteer versiespecifieke strategie
    strategy = get_strategy(ifc_file, version_enum)
    building_elements = strategy.get_building_elements()
    
    # Stap 4: Log resultaten
    logger.info("=" * 60)
    logger.info("STAP 0 - RESULTATEN")
    logger.info("=" * 60)
    logger.info(f"Bestand: {ifc_file_path}")
    logger.info(f"Bestandsgrootte: {file_info.get('bestandsgrootte_mb', 'N/A'):.2f} MB")
    logger.info(f"Gedetecteerde versie: {version_string}")
    logger.info(f"Aantal bouwkundige elementen om te verwerken: {len(building_elements)}")
    logger.info(f"Bouwkundige elementen: {', '.join(building_elements)}")
    logger.info("=" * 60)
    
    # Retourneer Stap 0 output
    step_0_results = {
        "ifc_file": ifc_file,
        "ifc_file_path": ifc_file_path,
        "ifc_version": version_string,
        "ifc_version_enum": version_enum,
        "strategy": strategy,
        "file_info": file_info,
        "building_elements": building_elements,
        "status": "OK"
    }
    
    return step_0_results


if __name__ == "__main__":
    # Test: Voer Stap 0 uit met een voorbeeld IFC-bestand
    if len(sys.argv) > 1:
        ifc_path = sys.argv[1]
    else:
        # Standaard test-pad (aanpassen naar jouw bestand)
        ifc_path = "c:/Users/cathy/Downloads/quest/test_models/example.ifc"
    
    results = execute_step_0(ifc_path)
    
    if results:
        logger.info("✓ Stap 0 succesvol uitgevoerd!")
    else:
        logger.error("✗ Stap 0 mislukt!")
        sys.exit(1)