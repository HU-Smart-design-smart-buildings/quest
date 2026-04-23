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
from core.step_2.data_enricher import DataEnricher

logger = setup_logger(__name__)

class Step2MaterialCollector:
    """
    STAP 2: Materiaalkoppelingen Ophalen + Data Enrichment
    
    FUNCTIONALITEIT:
    - Extract directe materiaalkoppelingen (DIRECT, LAYERSET, CONSTITUENT, COMPONENT)
    - Join met Stap 1 elementen
    - Verrijk met element properties (dikte, breedte, lengte)
    - Verrijk met geometrie data (coördinaten, bounding box)
    - Verrijk met material properties (dichtheid, thermische waarden)
    - Multi-threaded verwerking (4 workers)
    - Output naar Excel met aparte sheets per element_type
    """
    
    def __init__(self, ifc_file, elements_df: pd.DataFrame, ifc_version_enum):
        self.ifc_file = ifc_file
        self.elements_df = elements_df
        self.ifc_version_enum = ifc_version_enum
        
        # Materiaal extraction modules
        self.validator = MaterialValidator()
        self.cache = MaterialLinkerCache(ifc_file)
        self.material_linker = MaterialLinker(ifc_file, self.validator, self.cache)
        self.layerset_processor = LayerSetProcessor(ifc_file, self.validator, self.cache)
        self.constituent_processor = ConstituentProcessor(ifc_file, self.validator, self.cache)
        self.component_processor = ComponentPropertiesProcessor(ifc_file, self.validator, self.cache)
        
        # Performance & output modules
        self.optimizer = PerformanceOptimizer(max_workers=4)
        self.joiner = DataJoiner()
        self.exporter = ExcelExporter(STEP_2_EXCEL_FILE)
        
        # Data enrichment module (NIEUW)
        self.enricher = DataEnricher(ifc_file)
        
        # Data storage
        self.materials_data = []
    
    def execute(self) -> dict:
        """
        Voer complete Stap 2 uit met data enrichment.
        """
        print("\n" + "=" * 70)
        print("STAP 2: MATERIAALKOPPELINGEN OPHALEN + DATA ENRICHMENT")
        print("=" * 70 + "\n")
        
        try:
            # 2.1: Filter elementen die we gaan verwerken
            print("Stap 2.1: Filteren verwerkbare elementen...")
            elements_to_process = self._filter_processable_elements()
            
            # 2.2: Extract materialen via multi-threading
            print("Stap 2.2: Extracting materialen (multi-threaded)...")
            self._extract_materials_multithreaded(elements_to_process)
            
            # 2.3: Join Stap 1 + 2 data
            print("Stap 2.3: Join Stap 1 + 2 data...")
            merged_df = self._join_with_step1()
            
            # 2.4: Verrijk met extra data (NIEUW)
            print("Stap 2.4: Verrijken met element/material/geometry properties...")
            enriched_df = self._enrich_data(merged_df)
            
            # 2.5: Split per element_type en export naar Excel
            print("Stap 2.5: Exporteren naar Excel...")
            self._export_to_excel(enriched_df)
            
            # 2.6: Print statistieken
            self._print_statistics(enriched_df)
            
            print("\n" + "=" * 70)
            print("✓ STAP 2 SUCCESVOL VOLTOOID")
            print("=" * 70 + "\n")
            
            return self._get_results(enriched_df)
        
        except Exception as e:
            logger.error(f"Fout in Stap 2: {e}")
            raise
    
    def _filter_processable_elements(self) -> list:
        """
        Filter elementen uit Stap 1 die we gaan verwerken.
        
        SKIP als:
        - has_material_info = False EN geometric_representation = False
        """
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
        print("  Verwerking wordt parallel uitgevoerd (4 workers)...")
        
        # Processor functie voor parallelle verwerking
        def process_single_element(element_record):
            try:
                element_id = element_record['element_id']
                ifc_element = self.ifc_file.by_id(element_id)
                
                # Extract alle materiaaltypes
                materials = []
                
                # 1. Direct materials
                direct_materials = self.material_linker.get_direct_materials(ifc_element)
                if direct_materials:
                    materials.extend(direct_materials)
                
                # 2. Layerset materials
                layerset_materials = self._get_layerset_materials(ifc_element)
                if layerset_materials:
                    materials.extend(layerset_materials)
                
                # 3. Constituent materials
                constituent_materials = self._get_constituent_materials(ifc_element)
                if constituent_materials:
                    materials.extend(constituent_materials)
                
                # 4. Component materials
                component_materials = self.component_processor.get_component_materials(ifc_element)
                if component_materials:
                    materials.extend(component_materials)
                
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
        
        print(f"  └─ {len(self.materials_data)} materiaalkoppelingen gevonden")
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
                                layer_materials = self.layerset_processor.process_layerset(element, material_obj)
                                if layer_materials:
                                    materials.extend(layer_materials)
        except Exception as e:
            logger.debug(f"Fout bij layerset extraction: {e}")
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
                                constituent_materials = self.constituent_processor.process_constituent_set(element, material_obj)
                                if constituent_materials:
                                    materials.extend(constituent_materials)
        except Exception as e:
            logger.debug(f"Fout bij constituent extraction: {e}")
        return materials
    
    def _join_with_step1(self) -> pd.DataFrame:
        """
        Join Stap 2 materialen met Stap 1 elementen.
        """
        df_materials = pd.DataFrame(self.materials_data) if self.materials_data else pd.DataFrame()
        merged_df = self.joiner.join_step1_and_materials(self.elements_df, df_materials)
        
        print(f"  └─ {len(merged_df)} rijen na join")
        return merged_df
    
    def _enrich_data(self, merged_df: pd.DataFrame) -> pd.DataFrame:
        """
        NIEUW: Verrijk DataFrame met extra data uit IFC:
        - Element properties (dikte, breedte, lengte)
        - Geometry (coördinaten, bounding box)
        - Material properties (dichtheid, thermische waarden)
        """
        try:
            enriched_df = self.enricher.enrich_materials_dataframe(merged_df)
            
            # Print enrichment stats
            stats = self.enricher.get_enrichment_stats(enriched_df)
            
            print(f"  └─ Enrichment voltooid:")
            print(f"       ├─ Elementen met coördinaten: {stats.get('elements_with_coordinates', 0)}")
            print(f"       ├─ Elementen met dikte: {stats.get('elements_with_thickness', 0)}")
            print(f"       └─ Materialen met dichtheid: {stats.get('materials_with_density', 0)}")
            
            logger.info(f"Data enrichment stats: {stats}")
            
            return enriched_df
        
        except Exception as e:
            logger.error(f"Fout bij data enrichment: {e}")
            logger.warning("Proceeding without enrichment...")
            return merged_df
    
    def _export_to_excel(self, enriched_df: pd.DataFrame):
        """
        Exporteer naar Excel met separate sheets per element_type.
        """
        try:
            dfs_by_type = self.joiner.split_by_element_type(enriched_df)
            validation_stats = self.joiner.get_validation_stats(enriched_df)
            
            success = self.exporter.export_to_excel(dfs_by_type, validation_stats)
            
            if success:
                print(f"  └─ Excel opgeslagen: {STEP_2_EXCEL_FILE}")
                logger.info(f"Excel export succesvol: {len(dfs_by_type)} sheets")
            else:
                logger.warning("Excel export had problemen")
        
        except Exception as e:
            logger.error(f"Fout bij export naar Excel: {e}")
    
    def _print_statistics(self, enriched_df: pd.DataFrame):
        """
        Print gedetailleerde statistieken.
        """
        print("Stap 2.6: Statistieken")
        print("=" * 70)
        
        # Basis statistieken
        validation_stats = self.joiner.get_validation_stats(enriched_df)
        
        print(f"\nAlgemeen:")
        print(f"  ├─ Totaal rijen: {validation_stats['total_rows']}")
        print(f"  ├─ Unieke elementen: {validation_stats['unique_elements']}")
        print(f"  ├─ Met materiaal: {validation_stats['elements_with_material']}")
        print(f"  ├─ Zonder materiaal: {validation_stats['elements_without_material']}")
        print(f"  └─ Material coverage: {validation_stats['material_coverage_percentage']:.1f}%")
        
        # Element properties statistieken (NIEUW)
        thickness_count = enriched_df['thickness'].notna().sum() if 'thickness' in enriched_df.columns else 0
        width_count = enriched_df['width'].notna().sum() if 'width' in enriched_df.columns else 0
        length_count = enriched_df['length'].notna().sum() if 'length' in enriched_df.columns else 0
        coord_count = enriched_df['coord_x'].notna().sum() if 'coord_x' in enriched_df.columns else 0
        
        print(f"\nElement Properties Beschikbaarheid:")
        print(f"  ├─ Met dikte: {thickness_count}")
        print(f"  ├─ Met breedte: {width_count}")
        print(f"  ├─ Met lengte: {length_count}")
        print(f"  └─ Met coördinaten: {coord_count}")
        
        # Material properties statistieken (NIEUW)
        density_count = enriched_df['density'].notna().sum() if 'density' in enriched_df.columns else 0
        thermal_count = enriched_df['thermal_conductivity'].notna().sum() if 'thermal_conductivity' in enriched_df.columns else 0
        
        print(f"\nMaterialeigenschappen Beschikbaarheid:")
        print(f"  ├─ Met dichtheid (kg/m³): {density_count}")
        print(f"  └─ Met thermische geleiding (W/mK): {thermal_count}")
        
        # Per element type
        print(f"\nPer element type:")
        for element_type in sorted(enriched_df['element_type'].unique()):
            type_df = enriched_df[enriched_df['element_type'] == element_type]
            with_material = len(type_df[type_df['material_name'] != 'Unknown'])
            print(f"  ├─ {element_type}: {len(type_df)} rijen ({with_material} met materiaal)")
        
        # Per source
        print(f"\nPer bron:")
        for source in sorted(enriched_df[enriched_df['source'] != 'Unknown']['source'].unique()):
            count = len(enriched_df[enriched_df['source'] == source])
            print(f"  ├─ {source}: {count}")
        
        print("=" * 70)
    
    def _get_results(self, enriched_df: pd.DataFrame) -> dict:
        """
        Retourneer Stap 2 resultaten.
        """
        validation_stats = self.joiner.get_validation_stats(enriched_df)
        
        return {
            'materials_df': enriched_df,
            'total_material_entries': len(self.materials_data),
            'unique_elements_processed': enriched_df['element_id'].nunique(),
            'validation_stats': validation_stats,
            'excel_output': STEP_2_EXCEL_FILE,
            'status': 'OK'
        }