import sys
from pathlib import Path

# Imports van Stap 0
from core.step_0.ifc_loader import IFCLoader
from core.step_0.version_detector import VersionDetector
from core.step_0.version_strategies import get_strategy

# Imports van Stap 1
from core.step_1.step_1_element_collector import Step1ElementCollector

# Imports van Stap 2
from core.step_2.step_2_material_collector import Step2MaterialCollector

from core.logger import setup_logger

logger = setup_logger(__name__, "quest_main.log")

def execute_step_0(ifc_file_path):
    """
    STAP 0: IFC-bestand inladen en versie detecteren.
    """
    print("\n" + "=" * 60)
    print("STAP 0: IFC-BESTAND INLADEN EN VERSIE DETECTEREN")
    print("=" * 60 + "\n")
    
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
    print("=" * 60)
    print("STAP 0 - RESULTATEN")
    print("=" * 60)
    print(f"Bestand: {ifc_file_path}")
    print(f"Bestandsgrootte: {file_info.get('bestandsgrootte_mb', 'N/A'):.2f} MB")
    print(f"Gedetecteerde versie: {version_string}")
    print(f"Aantal bouwkundige elementen-typen: {len(building_elements)}")
    print("=" * 60 + "\n")
    
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


def execute_step_2(step_0_results, step_1_results):
    """
    STAP 2: Materiaalkoppelingen ophalen.
    """
    if step_0_results is None or step_1_results is None:
        logger.error("Stap 0 of 1 faalde. Kan Stap 2 niet uitvoeren.")
        return None
    
    ifc_file = step_0_results["ifc_file"]
    ifc_version_enum = step_0_results["ifc_version_enum"]
    elements_df = step_1_results["elements_df"]
    
    # Voer Stap 2 uit
    collector = Step2MaterialCollector(ifc_file, elements_df, ifc_version_enum)
    step_2_results = collector.execute()
    
    return step_2_results


def main(ifc_file_path):
    """
    Hoofdfunctie: Voer alle stappen uit.
    """
    print("\n" + "=" * 30)
    print("QUEST - BIM MATERIAALPROFILER")
    print("=" * 30 + "\n")
    
    try:
        # STAP 0
        step_0_results = execute_step_0(ifc_file_path)
        if not step_0_results:
            return False
        
        # STAP 1
        step_1_results = execute_step_1(step_0_results)
        if not step_1_results:
            return False
        
        # STAP 2
        step_2_results = execute_step_2(step_0_results, step_1_results)
        if not step_2_results:
            return False
        
        print("\n" + "=" * 60)
        print("[OK] ALLE STAPPEN SUCCESVOL VOLTOOID")
        print("=" * 60)
        print(f"Totaal elementen verzameld (Stap 1): {step_1_results['total_elements']}")
        print(f"Totaal materiaalkoppelingen (Stap 2): {step_2_results['total_material_entries']}")
        print("=" * 60 + "\n")
        
        return True
    
    except Exception as e:
        logger.error(f"Kritieke fout: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ifc_path = sys.argv[1]
    else:
        logger.error("Geen IFC-bestandspad opgegeven!")
        print("Gebruik: python main.py <C:\\Users\\cathy\\Downloads\\quest\\4.3_bestand.ifc>")
        sys.exit(1)
    
    success = main(ifc_path)
    sys.exit(0 if success else 1)