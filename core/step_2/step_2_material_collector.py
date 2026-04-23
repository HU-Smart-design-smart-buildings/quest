import pandas as pd
from pathlib import Path
from config.config import (
    STEP_2_OUTPUT_FILE, 
    STEP_2_MATERIAL_DEFINITIONS_FILE,
    STEP_2_REPORT_FILE,
    UNIVERSAL_BUILDING_ELEMENTS
)
from core.logger import setup_logger
from core.step_2.material_validator import MaterialValidator
from core.step_2.material_linker_cache import MaterialLinkerCache
from core.step_2.material_linker import MaterialLinker
from core.step_2.layerset_processor import LayerSetProcessor
from core.step_2.constituent_processor import ConstituentProcessor
from core.step_2.component_properties import ComponentPropertiesProcessor

logger = setup_logger(__name__)

class Step2MaterialCollector:
    """
    Orchestrator voor Stap 2: Materiaalkoppelingen ophalen.
    """
    
    def __init__(self, ifc_file, elements_df, ifc_version_enum):
        self.ifc_file = ifc_file
        self.elements_df = elements_df
        self.ifc_version_enum = ifc_version_enum
        
        # Initialiseer modules
        self.validator = MaterialValidator()
        self.cache = MaterialLinkerCache(ifc_file)
        self.material_linker = MaterialLinker(ifc_file, self.validator, self.cache)
        self.layerset_processor = LayerSetProcessor(ifc_file, self.validator, self.cache)
        self.constituent_processor = ConstituentProcessor(ifc_file, self.validator, self.cache)
        self.component_processor = ComponentPropertiesProcessor(ifc_file, self.validator, self.cache)
        
        # Tussentijdse data
        self.materials_data = []
        self.material_definitions = {}
    
    def execute(self):
        """
        Voer complete Stap 2 uit.
        
        Returns:
            dict met resultaten
        """
        print("\n" + "=" * 60)
        print("STAP 2: MATERIAALKOPPELINGEN OPHALEN")
        print("=" * 60 + "\n")
        
        try:
            # Stap 2.1: Ophalen materiaalkoppelingen per element
            self._extract_all_materials()
            
            # Stap 2.2: Opslaan resultaten
            self._save_results()
            
            # Stap 2.3: Print statistieken
            self._print_statistics()
            
            print("\n" + "=" * 60)
            print("✓ STAP 2 SUCCESVOL VOLTOOID")
            print("=" * 60 + "\n")
            
            return self._get_results()
        
        except Exception as e:
            logger.error(f"Fout in Stap 2: {e}")
            raise
    
    def _extract_all_materials(self):
        """
        Haal alle materiaalkoppelingen op per element.
        """
        print("Stap 2.1: Materiaalkoppelingen ophalen per element...")
        
        total_elements = len(self.elements_df)
        processed = 0
        errors = 0
        
        for idx, row in self.elements_df.iterrows():
            try:
                element_id = row['element_id']
                
                # Haal IFC element op
                ifc_element = self.ifc_file.by_id(element_id)
                
                # Haal alle materiaalkoppelingen op
                self._extract_materials_for_element(ifc_element)
                
                processed += 1
                if processed % 100 == 0:
                    print(f"  └─ {processed}/{total_elements} elementen verwerkt...")
            
            except Exception as e:
                logger.debug(f"Fout bij verwerking element {element_id}: {e}")
                errors += 1
                continue
        
        print(f"✓ {processed} elementen verwerkt, {len(self.materials_data)} materiaalkoppelingen gevonden")
        if errors > 0:
            logger.warning(f"⚠ {errors} fouten tijdens verwerking")
    
    def _extract_materials_for_element(self, element):
        """
        Haal alle materiaalkoppelingen voor één element op.
        """
        try:
            # 1. Directe materialen
            direct_materials = self.material_linker.get_direct_materials(element)
            self.materials_data.extend(direct_materials)
            
            # 2. Gelaagde materialen (IFCMATERIALLAYERSET)
            layerset_materials = self._get_layerset_materials(element)
            self.materials_data.extend(layerset_materials)
            
            # 3. Samengestelde materialen (IFCMATERIALCONSTITUENTSET)
            constituent_materials = self._get_constituent_materials(element)
            self.materials_data.extend(constituent_materials)
            
            # 4. Deur/Raam-componenten
            component_materials = self.component_processor.get_component_materials(element)
            self.materials_data.extend(component_materials)
        
        except Exception as e:
            logger.debug(f"Fout bij extractie materialen voor element: {e}")
    
    def _get_layerset_materials(self, element):
        """
        Haal gelaagde materialen op.
        """
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
            logger.debug(f"Fout bij ophalen layerset materialen: {e}")
        
        return materials
    
    def _get_constituent_materials(self, element):
        """
        Haal samengestelde materialen op.
        """
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
            logger.debug(f"Fout bij ophalen constituent materialen: {e}")
        
        return materials
    
    def _save_results(self):
        """
        Sla resultaten op.
        """
        print("Stap 2.2: Resultaten opslaan...")
        
        try:
            # Maak DataFrame
            df_materials = pd.DataFrame(self.materials_data)
            
            # DEBUG: Log de huidige kolommen
            logger.info(f"Kolommen in materials_data: {df_materials.columns.tolist()}")
            logger.info(f"Sample element_type waarden: {df_materials['element_type'].unique()[:5] if 'element_type' in df_materials.columns else 'KOLOM NIET GEVONDEN'}")
            
            # Zorg voor correcte kolom-volgorde
            column_order = [
                'element_id', 'element_type', 'material_name', 'material_type',
                'layer_thickness', 'layer_index', 'constituent_fraction', 
                'layerset_name', 'data_quality_flag', 'source', 'notes'
            ]
            
            # Voeg ontbrekende kolommen toe (mag niet voorkomen, maar voor zekerheid)
            for col in column_order:
                if col not in df_materials.columns:
                    df_materials[col] = None
                    logger.warning(f"Kolom '{col}' ontbrak, toegevoegd als None")
            
            # Zorg dat element_type het juiste format heeft (uppercase IFC types)
            if 'element_type' in df_materials.columns:
                df_materials['element_type'] = df_materials['element_type'].str.upper()
            
            df_materials = df_materials[column_order]
            
            # Sla als pickle op
            Path(STEP_2_OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
            df_materials.to_pickle(STEP_2_OUTPUT_FILE)
            print(f"✓ DataFrame opgeslagen: {STEP_2_OUTPUT_FILE}")
            logger.info(f"DataFrame shape: {df_materials.shape}")
            logger.info(f"Unieke element types: {df_materials['element_type'].unique().tolist()}")
            
            # Sla ook material definitions cache op
            self.cache.material_cache.update(self.cache.layerset_cache)
            self.cache.material_cache.update(self.cache.constituent_cache)
            
            # Opslaan cache stats voor rapportage
            cache_stats = self.cache.get_cache_stats()
            logger.info(f"Cache statistieken: {cache_stats}")
        
        except Exception as e:
            logger.error(f"Fout bij opslaan resultaten: {e}")
            raise
    
    def _print_statistics(self):
        """
        Print statistieken.
        """
        print("\nStap 2.3: Statistieken")
        print("=" * 60)
        
        if len(self.materials_data) > 0:
            df = pd.DataFrame(self.materials_data)
            
            # Zorg dat element_type uppercase is
            if 'element_type' in df.columns:
                df['element_type'] = df['element_type'].str.upper()
            
            # Totalen per bron
            print(f"\nMateriaalkoppelingen per bron:")
            for source in sorted(df['source'].unique()):
                count = len(df[df['source'] == source])
                print(f"  ├─ {source}: {count}")
            
            # Totalen per element type
            print(f"\nMateriaalkoppelingen per element type:")
            element_type_counts = df['element_type'].value_counts().sort_index()
            for element_type, count in element_type_counts.items():
                unique_elements_of_type = df[df['element_type'] == element_type]['element_id'].nunique()
                print(f"  ├─ {element_type}: {count} koppelingen ({unique_elements_of_type} unieke elementen)")
            
            # Elementen met materialen
            unique_elements = df['element_id'].nunique()
            print(f"\nUnieke elementen met materialen: {unique_elements}")
            
            # Data quality
            print(f"\nData Quality Flags:")
            quality_counts = df['data_quality_flag'].value_counts()
            for flag, count in quality_counts.items():
                percentage = (count / len(df)) * 100
                print(f"  ├─ {flag}: {count} ({percentage:.1f}%)")
            
            # Fallback statistieken
            fallback_count = len(df[df['data_quality_flag'] == 'FALLBACK_APPLIED'])
            if fallback_count > 0:
                print(f"\n⚠ Fallback materialen toegepast: {fallback_count}")
                fallback_df = df[df['data_quality_flag'] == 'FALLBACK_APPLIED']
                print(f"  ├─ Per bron:")
                for source in sorted(fallback_df['source'].unique()):
                    count = len(fallback_df[fallback_df['source'] == source])
                    print(f"  │  ├─ {source}: {count}")
            
            # Material names statistieken
            print(f"\nMateriaalnamen gevonden:")
            material_counts = df['material_name'].value_counts().head(10)
            for material, count in material_counts.items():
                print(f"  ├─ {material}: {count}")
            
            # Unknown materialen
            unknown_count = len(df[df['material_name'] == 'Unknown'])
            if unknown_count > 0:
                print(f"\n⚠ Unknown materialen: {unknown_count}")
        
        else:
            print("⚠ Geen materiaalkoppelingen gevonden!")
        
        print("=" * 60)
    
    def _get_results(self):
        """
        Retourneer Stap 2 resultaten.
        """
        df_materials = pd.DataFrame(self.materials_data)
        if 'element_type' in df_materials.columns:
            df_materials['element_type'] = df_materials['element_type'].str.upper()
        
        return {
            'materials_df': df_materials,
            'total_material_entries': len(self.materials_data),
            'unique_elements_with_materials': len(self.elements_df),
            'cache_stats': self.cache.get_cache_stats(),
            'status': 'OK'
        }