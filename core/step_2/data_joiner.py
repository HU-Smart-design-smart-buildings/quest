import pandas as pd
from typing import Tuple
from core.logger import setup_logger

logger = setup_logger(__name__)

class DataJoiner:
    """
    Voegt Stap 1 gegevens (elementen) samen met Stap 2 gegevens (materialen).
    """
    
    def __init__(self):
        pass
    
    def join_step1_and_materials(self, 
                                 elements_df: pd.DataFrame, 
                                 materials_df: pd.DataFrame) -> pd.DataFrame:
        """
        Join Stap 1 elementen met Stap 2 materialen.
        
        Args:
            elements_df: DataFrame van Stap 1 (element_id, element_type, ...)
            materials_df: DataFrame van Stap 2 (element_id, material_name, ...)
        
        Returns:
            Joined DataFrame met alle gebonden informatie
        """
        logger.info(f"Start join: {len(elements_df)} elementen + {len(materials_df)} materiaalrijen")
        
        # LEFT JOIN: behoud al elementen uit Stap 1, zelfs zonder materiaal
        merged_df = elements_df.merge(
            materials_df,
            on=['element_id', 'element_type'],
            how='left'
        )
        
        # Kolommen die we verwachten van Stap 2
        expected_material_columns = [
            'material_name', 'material_type', 'layer_thickness', 
            'layer_index', 'constituent_fraction', 'layerset_name',
            'data_quality_flag', 'source', 'notes'
        ]
        
        # Voor elementen ZONDER materiaal: vul 'Unknown' in
        for col in expected_material_columns:
            if col in merged_df.columns:
                merged_df[col] = merged_df[col].fillna('Unknown' if col == 'material_name' else None)
            else:
                merged_df[col] = 'Unknown' if col == 'material_name' else None
        
        logger.info(f"Join voltooid: {len(merged_df)} rijen")
        
        # Validatie
        elements_without_material = len(merged_df[merged_df['material_name'] == 'Unknown']['element_id'].unique())
        elements_with_material = len(merged_df[merged_df['material_name'] != 'Unknown']['element_id'].unique())
        
        logger.info(f"Validatie: {elements_with_material} elementen met materiaal, {elements_without_material} zonder")
        
        return merged_df
    
    def split_by_element_type(self, merged_df: pd.DataFrame) -> dict:
        """
        Splits DataFrame per element_type voor separate Excel sheets.
        
        Args:
            merged_df: Joined DataFrame
        
        Returns:
            Dict met element_type als key, DataFrame als value
        """
        dfs_by_type = {}
        
        for element_type in merged_df['element_type'].unique():
            type_df = merged_df[merged_df['element_type'] == element_type].copy()
            dfs_by_type[element_type] = type_df
            logger.info(f"Sheet '{element_type}': {len(type_df)} rijen")
        
        return dfs_by_type
    
    def get_validation_stats(self, merged_df: pd.DataFrame) -> dict:
        """
        Haal validatiestatistieken op.
        """
        total_rows = len(merged_df)
        unique_elements = merged_df['element_id'].nunique()
        elements_with_material = len(merged_df[merged_df['material_name'] != 'Unknown']['element_id'].unique())
        elements_without_material = unique_elements - elements_with_material
        
        material_coverage = (elements_with_material / unique_elements * 100) if unique_elements > 0 else 0
        
        return {
            'total_rows': total_rows,
            'unique_elements': unique_elements,
            'elements_with_material': elements_with_material,
            'elements_without_material': elements_without_material,
            'material_coverage_percentage': material_coverage
        }