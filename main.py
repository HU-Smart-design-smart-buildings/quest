import sys
from pathlib import Path
from core.ifc_loader import IFCLoader
from core.version_detector import VersionDetector
from core.version_strategies import get_strategy
from core.logger import setup_logger
from core.step_1_element_collector import Step1ElementCollector

logger = setup_logger(__name__, "quest_main.log")

def execute_step_0(ifc_file_path):
    """
    STAP 0: IFC-bestand inladen en versie detecteren.
    """
    logger.info("\n" + "=" * 60)
    logger.info("STAP 0: IFC-BESTAND INLADEN EN VERSIE DETECTEREN")
    logger.info("=" * 60 + "\n")
    
    # Valideer en laad het IFC-bestand
    loader = IFCLoader(ifc_file_path)
    if not loader.validate_file():
        logger.error("Kon IFC-bestand niet inladen. Stoppen.")
        return None
    
    ifc_file = loader.get_file_object()
    file_info = loader.get_file_info()
    
    # Detecteer IFC-versie
    detector = VersionDetector(ifc_file)
    version_string, version_enum = detector.detect()
    
    # Selecteer versiespecifieke strategie
    strategy = get_strategy(ifc_file, version_enum)
    building_elements = strategy.get_building_elements()
    
    # Log resultaten
    logger.info("=" * 60)
    logger.info("STAP 0 - RESULTATEN")
    logger.info("=" * 60)
    logger.info(f"Bestand: {ifc_file_path}")
    logger.info(f"Bestandsgrootte: {file_info.get('bestandsgrootte_mb', 'N/A'):.2f} MB")
    logger.info(f"Gedetecteerde versie: {version_string}")
    logger.info(f"Aantal bouwkundige elementen-typen: {len(building_elements)}")
    logger.info("=" * 60 + "\n")
    
    # Retourneer Stap 0 output
    return {
        "ifc_file": ifc_file,
        "ifc_file_path": ifc_file_path,
        "ifc_version": version_string,
        "ifc_version_enum": version_enum,
        "strategy": strategy,
        "file_info": file_info,
        "building_elements": building_elements,
        "status": "OK"
    }


def execute_step_1(step_0_results):
    """
    STAP 1: Alle bouwkundige elementen verzamelen.
    """
    if step_0_results is None:
        logger.error("Stap 0 faalde. Kan Stap 1 niet uitvoeren.")
        return None
    
    ifc_file = step_0_results["ifc_file"]
    ifc_version_enum = step_0_results["ifc_version_enum"]
    
    # Voer Stap 1 uit
    collector = Step1ElementCollector(ifc_file, ifc_version_enum)
    step_1_results = collector.execute()
    
    return step_1_results


def main(ifc_file_path):
    """
    Hoofdfunctie: Voer beide stappen uit.
    """
    logger.info("\n" + "🚀" * 30)
    logger.info("QUEST - BIM MATERIAALPROFILER")
    logger.info("🚀" * 30 + "\n")
    
    try:
        # STAP 0
        step_0_results = execute_step_0(ifc_file_path)
        if not step_0_results:
            return False
        
        # STAP 1
        step_1_results = execute_step_1(step_0_results)
        if not step_1_results:
            return False
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ ALLE STAPPEN SUCCESVOL VOLTOOID")
        logger.info("=" * 60)
        logger.info(f"Totaal elementen verzameld: {step_1_results['total_elements']}")
        logger.info(f"Elementen met materiaalinfo: {step_1_results['elements_with_material']}")
        logger.info("=" * 60 + "\n")
        
        return True
    
    except Exception as e:
        logger.error(f"Kritieke fout: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ifc_path = sys.argv[1]
    else:
        logger.error("Geen IFC-bestandspad opgegeven!")
        logger.info("Gebruik: python main.py <C:\\Users\\cathy\\Downloads\\quest\\4.3_bestand.ifc>")
        sys.exit(1)
    
    success = main(ifc_path)
    sys.exit(0 if success else 1)