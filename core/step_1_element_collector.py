import pandas as pd
from pathlib import Path
from config.config import STEP_1_OUTPUT_FILE, STEP_1_REPORT_FILE
from core.logger import setup_logger
from core.element_extractor import ElementExtractor
from core.completeness_reporter import CompletenessReporter

logger = setup_logger(__name__)

class Step1ElementCollector:
    """
    Orchestrator voor Stap 1: Alle bouwkundige elementen verzamelen.
    """
    
    def __init__(self, ifc_file, ifc_version_enum):
        self.ifc_file = ifc_file
        self.ifc_version_enum = ifc_version_enum
        self.elements_df = None
        self.report = None
    
    def execute(self):
        """
        Voer complete Stap 1 uit.
        
        Returns:
            dict met resultaten
        """
        logger.info("\n" + "=" * 60)
        logger.info("STAP 1: ALLE BOUWKUNDIGE ELEMENTEN VERZAMELEN")
        logger.info("=" * 60 + "\n")
        
        try:
            # Stap 1.1: Extractie
            self._extract_elements()
            
            # Stap 1.2: Rapportage
            self._generate_completeness_report()
            
            # Stap 1.3: Opslaan
            self._save_results()
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ STAP 1 SUCCESVOL VOLTOOID")
            logger.info("=" * 60 + "\n")
            
            return self._get_results()
        
        except Exception as e:
            logger.error(f"Fout in Stap 1: {e}")
            raise
    
    def _extract_elements(self):
        """
        Extract alle bouwkundige elementen.
        """
        extractor = ElementExtractor(self.ifc_file, self.ifc_version_enum)
        self.elements_df = extractor.extract_all_elements()
    
    def _generate_completeness_report(self):
        """
        Genereer volledigheidsrapport.
        """
        reporter = CompletenessReporter(self.elements_df, STEP_1_REPORT_FILE)
        self.report = reporter.generate_report()
        reporter.print_report()
    
    def _save_results(self):
        """
        Sla tussentijdse resultaten op.
        """
        logger.info("Sla tussentijdse resultaten op...")
        
        try:
            # Sla DataFrame op als pickle
            Path(STEP_1_OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
            self.elements_df.to_pickle(STEP_1_OUTPUT_FILE)
            logger.info(f"✓ DataFrame opgeslagen: {STEP_1_OUTPUT_FILE}")
        
        except Exception as e:
            logger.error(f"Fout bij opslaan DataFrame: {e}")
            raise
    
    def _get_results(self):
        """
        Retourneer Stap 1 resultaten.
        """
        return {
            'elements_df': self.elements_df,
            'report': self.report,
            'total_elements': len(self.elements_df),
            'elements_with_material': len(self.elements_df[self.elements_df['has_material_info'] == True]),
            'status': 'OK'
        }