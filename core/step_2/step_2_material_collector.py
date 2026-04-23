import pandas as pd
from pathlib import Path
from config.config import (
    STEP_2_OUTPUT_FILE,
    STEP_2_EXCEL_FILE,
    STEP_2_REPORT_FILE
)
from core.logger import setup_logger
from core.step_2.material_validator import MaterialValidator
from core.step_2.material_linker_cache import MaterialLinkerCache
from core.step_2.material_linker import MaterialLinker
from core.step_2.layerset_processor import LayerSetProcessor
from core.step_2.constituent_processor import ConstituentProcessor
from core.step_2.component_properties import ComponentPropertiesProcessor
from core.step_2.performance_optimizer import PerformanceOptimizer
from core.step_2.data_joiner import DataJoiner
from core.step_2.excel_exporter import ExcelExporter

logger = setup_logger(__name__)

class Step2MaterialCollector:
    """
    Orchestrator voor Stap 2: Materiaalkoppelingen ophalen.
    
    VERANDERINGEN TEN OPZICHTE VAN VORIGE VERSIE:
    - DirectStrict afhankelijk van Stap 1 outputs (elements_df)
    - Skip elementen zonder material_info EN zonder geometry
    - Multi-threading voor performance
    - Excel output met separate sheets per element_type
    - Validatie tegen Stap 1
    """
    
    def __init__(self, ifc_file, elements_df: pd.DataFrame, ifc_version_enum):
        self.ifc_file = ifc_file
        self.elements_df = elements_df
        self.ifc_version_enum = ifc_version_enum
        
        # Modules
        self.validator = MaterialValidator()
        self.cache = MaterialLinkerCache(ifc_file)
        self.material_linker = MaterialLinker(ifc_file, self.validator, self.cache)
        self.layerset_processor = LayerSetProcessor(ifc_file, self.validator, self.cache)
        self.constituent_processor = ConstituentProcessor(ifc_file, self.validator, self.cache)
        self.component_processor = ComponentPropertiesProcessor(ifc_file, self.validator, self.cache)
        self.optimizer = PerformanceOptimizer(max_workers=4)
        self.joiner = DataJoiner()
        self.exporter = ExcelExporter(STEP_2_EXCEL_FILE)
        
        # Data
        self.materials_data = []
    
    def execute(self) -> dict:
        """
        Voer complete Stap 2 uit.
        """
        print("\n" + "=" * 60)
        print("STAP 2: MATERIAALKOPPELINGEN OPHALEN")
        print("=" * 60 + "\n")
        
        try:
            # 2.1: Filter elementen die we gaan verwerken
            elements_to_process = self._filter_processable_elements()
            
            # 2.2: Extract materialen via multi-threading
            self._extract_materials_multithreaded(elements_to_process)
            
            # 2.3: Join Stap 1 + 2 data
            merged_df = self._join_with_step1()
            
            # 2.4: Split per element_type en export naar Excel
            self._export_to_excel(merged_df)
            
            # 2.5: Print statistieken
            self._print_statistics(merged_df)
            
            print("\n" + "=" * 60)
            print("✓ STAP 2 SUCCESVOL VOLTOOID")
            print("=" * 60 + "\n")
            
            return self._get_results(merged_df)
        
        except Exception as e:
            logger.error(f"Fout in Stap 2: {e}")
            raise
    
    def _filter_processable_elements(self) -> list:
        """
        Filter elementen uit Stap 1 die we gaan verwerken.
        
        SKIP als:
        - has_material_info = False EN geometric_representation = False
        """
        print("Stap 2.1: Filteren verwerkbare elementen...")
        
        total = len(self.elements_df)
        processable = self.elements_df[
            (self.elements_df['has_material_info'] == True) | 
            (self.elements_df['geometric_representation'] == True)
        ]
        
        skipped = total - len(processable)
        
        print(f"  └─ {len(processable)} verwerkbaar, {skipped} overgeslagen")
        logger.info(f"Gefilterd: {len(processable)} van {total} elementen, {skipped} skipped")
        
        return processable.to_dict('records')
    
    def _extract_materials_multithreaded(self, elements_to_process: list):
        """
        Extract materialen via multi-threading.
        """
        print("Stap 2.2: Extracting materialen (multi-threaded)...")
        
        # Processor functie voor parallelle verwerking
        def process_single_element(element_record):
            try:
                element_id = element_record['element_id']
                ifc_element = self.ifc_file.by_id(element_id)
                
                # Extract alle materiaaltypes
                materials = []
                
                # 1. Direct materials
                materials.extend(self.material_linker.get_direct_materials(ifc_element))
                
                # 2. Layerset materials
                materials.extend(self._get_layerset_materials(ifc_element))
                
                # 3. Constituent materials
                materials.extend(self._get_constituent_materials(ifc_element))
                
                # 4. Component materials
                materials.extend(self.component_processor.get_component_materials(ifc_element))
                
                return materials if materials else []
            
            except Exception as e:
                logger.debug(f"Fout bij element {element_record.get('element_id')}: {e}")
                return []
        
        # Proces via multi-threading
        self.materials_data = self.optimizer.process_elements_batch(
            elements_to_process,
            process_single_element,
            batch_size=500
        )
        
        print(f"✓ {len(self.materials_data)} materiaalkoppelingen gevonden")
        logger.info(f"Totaal materiaalkoppelingen: {len(self.materials_data)}")
    
    def _get_layerset_materials(self, element):
        """Haal layerset materialen op."""
        materials = []
        try:
            if hasattr(element, 'HasAssociations'):
                for rel in element.HasAssociations:
                    if rel.is_a('IFCRELASSOCIATESMATERIAL'):
                        if hasattr(rel, 'RelatingMaterial'):
                            material_obj = rel.RelatingMaterial
                            if material_obj.is_a('IFCMATERIALLAYERSET'):
                                materials.extend(self.layerset_processor.process_layerset(element, material_obj))
        except Exception as e:
            logger.debug(f"Fout bij layerset: {e}")
        return materials
    
    def _get_constituent_materials(self, element):
        """Haal constituent materialen op."""
        materials = []
        try:
            if hasattr(element, 'HasAssociations'):
                for rel in element.HasAssociations:
                    if rel.is_a('IFCRELASSOCIATESMATERIAL'):
                        if hasattr(rel, 'RelatingMaterial'):
                            material_obj = rel.RelatingMaterial
                            if material_obj.is_a('IFCMATERIALCONSTITUENTSET'):
                                materials.extend(self.constituent_processor.process_constituent_set(element, material_obj))
        except Exception as e:
            logger.debug(f"Fout bij constituent: {e}")
        return materials
    
    def _join_with_step1(self) -> pd.DataFrame:
        """
        Join Stap 2 materialen met Stap 1 elementen.
        """
        print("Stap 2.3: Join Stap 1 + 2 data...")
        
        df_materials = pd.DataFrame(self.materials_data)
        merged_df = self.joiner.join_step1_and_materials(self.elements_df, df_materials)
        
        print(f"✓ {len(merged_df)} rijen na join")
        return merged_df
    
    def _export_to_excel(self, merged_df: pd.DataFrame):
        """
        Exporteer naar Excel met separate sheets per element_type.
        """
        print("Stap 2.4: Exporteren naar Excel...")
        
        dfs_by_type = self.joiner.split_by_element_type(merged_df)
        validation_stats = self.joiner.get_validation_stats(merged_df)
        
        success = self.exporter.export_to_excel(dfs_by_type, validation_stats)
        
        if success:
            print(f"✓ Excel bestand opgeslagen: {STEP_2_EXCEL_FILE}")
            logger.info(f"Excel export succesvol: {len(dfs_by_type)} sheets")
        else:
            logger.warning("Excel export had problemen")
    
    def _print_statistics(self, merged_df: pd.DataFrame):
        """
        Print statistieken.
        """
        print("Stap 2.5: Statistieken")
        print("=" * 60)
        
        validation_stats = self.joiner.get_validation_stats(merged_df)
        
        print(f"\nAlgemeen:")
        print(f"  ├─ Totaal rijen: {validation_stats['total_rows']}")
        print(f"  ├─ Unieke elementen: {validation_stats['unique_elements']}")
        print(f"  ├─ Met materiaal: {validation_stats['elements_with_material']}")
        print(f"  ├─ Zonder materiaal: {validation_stats['elements_without_material']}")
        print(f"  └─ Coverage: {validation_stats['material_coverage_percentage']:.1f}%")
        
        # Per element type
        print(f"\nPer element type:")
        for element_type in sorted(merged_df['element_type'].unique()):
            type_df = merged_df[merged_df['element_type'] == element_type]
            with_material = len(type_df[type_df['material_name'] != 'Unknown'])
            print(f"  ├─ {element_type}: {len(type_df)} rijen ({with_material} met materiaal)")
        
        # Per source
        print(f"\nPer bron:")
        for source in sorted(merged_df[merged_df['source'] != 'Unknown']['source'].unique()):
            count = len(merged_df[merged_df['source'] == source])
            print(f"  ├─ {source}: {count}")
        
        print("=" * 60)
    
    def _get_results(self, merged_df: pd.DataFrame) -> dict:
        """
        Retourneer Stap 2 results.
        """
        validation_stats = self.joiner.get_validation_stats(merged_df)
        
        return {
            'materials_df': merged_df,
            'total_material_entries': len(self.materials_data),
            'unique_elements_processed': merged_df['element_id'].nunique(),
            'validation_stats': validation_stats,
            'excel_output': STEP_2_EXCEL_FILE,
            'status': 'OK'
        }