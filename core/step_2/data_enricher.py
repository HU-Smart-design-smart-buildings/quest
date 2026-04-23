import pandas as pd
from typing import Dict
from core.logger import setup_logger
from core.step_2.element_properties_extractor import ElementPropertiesExtractor
from core.step_2.material_properties_extractor import MaterialPropertiesExtractor
from core.step_2.geometry_extractor import GeometryExtractor

logger = setup_logger(__name__)

class DataEnricher:
    """
    Combineert alle extra data (element properties, material properties, geometry)
    met materiaaldata van Stap 2.
    """
    
    def __init__(self, ifc_file):
        self.ifc_file = ifc_file
        self.element_extractor = ElementPropertiesExtractor()
        self.material_extractor = MaterialPropertiesExtractor()
        self.geometry_extractor = GeometryExtractor(ifc_file)
    
    def enrich_materials_dataframe(self, materials_df: pd.DataFrame) -> pd.DataFrame:
        """
        Verrijk materiaal DataFrame met extra data.
        
        Args:
            materials_df: DataFrame van Stap 2 materialen
        
        Returns:
            DataFrame met extra kolommen
        """
        logger.info(f"Start data enrichment: {len(materials_df)} rijen")
        
        # Initialiseer kolommen
        enriched_df = materials_df.copy()
        
        # Element properties kolommen
        element_props_cols = ['thickness', 'width', 'height', 'length', 'element_class', 'material_class']
        for col in element_props_cols:
            enriched_df[col] = None
        
        # Material properties kolommen
        material_props_cols = ['density', 'thermal_conductivity', 'heat_capacity', 'fire_rating', 'color', 'surface_finish']
        for col in material_props_cols:
            enriched_df[col] = None
        
        # Geometry kolommen
        geometry_cols = ['coord_x', 'coord_y', 'coord_z', 'bbox_min_x', 'bbox_min_y', 'bbox_min_z', 
                        'bbox_max_x', 'bbox_max_y', 'bbox_max_z', 'volume', 'surface_area', 'height_above_nap']
        for col in geometry_cols:
            enriched_df[col] = None
        
        # Process per unieke element (voorkomen duplicaat werk)
        unique_elements = enriched_df['element_id'].unique()
        total_unique = len(unique_elements)
        
        # Cache voor opgehaalde data
        element_cache = {}
        material_cache = {}
        
        for idx, unique_element_id in enumerate(unique_elements):
            try:
                # Haal IFC element op
                if unique_element_id not in element_cache:
                    ifc_element = self.ifc_file.by_id(unique_element_id)
                    element_cache[unique_element_id] = ifc_element
                else:
                    ifc_element = element_cache[unique_element_id]
                
                # Extraheer element properties (1x per unique element)
                element_props = self.element_extractor.extract_element_properties(ifc_element, unique_element_id)
                
                # Extraheer geometry (1x per unique element)
                geometry_props = self.geometry_extractor.extract_geometry(ifc_element, unique_element_id)
                
                # Update alle rijen met dit element_id
                element_rows = enriched_df[enriched_df['element_id'] == unique_element_id]
                
                for row_idx in element_rows.index:
                    # Element properties
                    for key, value in element_props.items():
                        if key in element_props_cols:
                            enriched_df.at[row_idx, key] = value
                    
                    # Geometry properties
                    for key, value in geometry_props.items():
                        if key in geometry_cols:
                            enriched_df.at[row_idx, key] = value
                    
                    # Material properties (per material)
                    material_name = enriched_df.at[row_idx, 'material_name']
                    
                    # Probeer material object op te halen (via cache)
                    material_obj = None
                    if material_name and material_name != 'Unknown':
                        if material_name not in material_cache:
                            # Dit is een simplificatie - in werkelijkheid zou je via 
                            # IFCMATERIAL lookup werken
                            material_cache[material_name] = None
                        material_obj = material_cache[material_name]
                    
                    # Extraheer material properties
                    if material_obj:
                        mat_props = self.material_extractor.extract_material_properties(
                            material_obj, 
                            material_name
                        )
                        for key, value in mat_props.items():
                            if key in material_props_cols:
                                enriched_df.at[row_idx, key] = value
                
                if (idx + 1) % 100 == 0:
                    print(f"  └─ {idx + 1}/{total_unique} elementen verrijkt...")
            
            except Exception as e:
                logger.debug(f"Fout bij enrichment van element {unique_element_id}: {e}")
                continue
        
        logger.info(f"Data enrichment voltooid: {len(enriched_df)} rijen met extra data")
        
        return enriched_df
    
    def get_enrichment_stats(self, enriched_df: pd.DataFrame) -> Dict:
        """
        Haal statistieken op wat aangevuld is.
        """
        stats = {}
        
        # Element properties
        stats['elements_with_thickness'] = enriched_df['thickness'].notna().sum()
        stats['elements_with_width'] = enriched_df['width'].notna().sum()
        stats['elements_with_height'] = enriched_df['height'].notna().sum()
        stats['elements_with_length'] = enriched_df['length'].notna().sum()
        
        # Geometry
        stats['elements_with_coordinates'] = enriched_df['coord_x'].notna().sum()
        stats['elements_with_volume'] = enriched_df['volume'].notna().sum()
        
        # Material properties
        stats['materials_with_density'] = enriched_df['density'].notna().sum()
        stats['materials_with_thermal_conductivity'] = enriched_df['thermal_conductivity'].notna().sum()
        
        return stats