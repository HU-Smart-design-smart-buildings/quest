import sys
from pathlib import Path

# Imports van Stap 0
from core.step_0.ifc_loader import IFCLoader
from core.step_0.version_detector import VersionDetector
from core.step_0.version_strategies import get_strategy

# Imports van Stap 1
from core.step_1.step_1_element_collector import Step1ElementCollector

from core.logger import setup_logger

logger = setup_logger(__name__, "quest_main.log")

def execute_step_0(ifc_file_path):
    """
    STAP 0: IFC-bestand inladen en versie detecteren.
    """
    print("\n" + "=" * 70)
    print("STAP 0: BESTAND INLEZEN EN VERSIE HERKENNEN")
    print("=" * 70 + "\n")
    
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
    try:
        ifc_file = step_0_results['ifc_file']
        ifc_version = step_0_results['ifc_version']
        
        collector = Step1ElementCollector(ifc_file, ifc_version)
        return collector.execute()
    
    except Exception as e:
        logger.error(f"Fout in Stap 1: {e}", exc_info=True)
        raise

def main(ifc_file_path):
    """
    Hoofdfunctie: Voer alle stappen uit.
    """
    print("\n" + "=" * 30)
    print("QUEST - BIM MATERIAALPROFILER")
    print("=" * 30 + "\n")
    
    try:
        # Stap 0
        step_0_results = execute_step_0(ifc_file_path)
        if not step_0_results:
            return False
        
        # Stap 1
        step_1_results = execute_step_1(step_0_results)
        
        print("\n" + "═" * 70)
        print("SAMENVATTING")
        print("═" * 70)
        print(f"[OK] Stap 0: Bestand ingeladen en versie gedetecteerd")
        print(f"[OK] Stap 1: {step_1_results['total_elements']:,} elementen verzameld")
        print(f"  ├─ Met materiaal info: {step_1_results['elements_with_material']:,}")
        print(f"  └─ Output: {step_1_results.get('status')}")
        print("═" * 70 + "\n")
        
        return {
            'step_0': step_0_results,
            'step_1': step_1_results,
            'status': 'OK'
        }
    
    except Exception as e:
        logger.error(f"Kritieke fout: {e}")
        print(f"\nX FOUT: {e}")
        return {'status': 'ERROR', 'error': str(e)}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ifc_path = sys.argv[1]
    else:
        logger.error("Geen IFC-bestandspad opgegeven!")
        print("Gebruik: python main.py <C:\\Users\\cathy\\Downloads\\quest\\4.3_bestand.ifc>")
        sys.exit(1)
    
    success = main(ifc_path)
    sys.exit(0 if success else 1)