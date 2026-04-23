import pandas as pd
from pathlib import Path
from typing import Dict
from core.logger import setup_logger

logger = setup_logger(__name__)

class ExcelExporter:
    """
    Exporteert Stap 2 output naar Excel met separate sheets per element_type.
    """
    
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def export_to_excel(self, dfs_by_type: Dict[str, pd.DataFrame], 
                       validation_stats: dict) -> bool:
        """
        Exporteert DataFrames naar Excel met:
        - Separate sheet per element_type
        - Summary sheet met statistieken
        - Formatting en validatie
        
        Args:
            dfs_by_type: Dict met element_type → DataFrame
            validation_stats: Validatiestatistieken
        
        Returns:
            True if successful
        """
        try:
            with pd.ExcelWriter(self.output_path, engine='openpyxl') as writer:
                # Schrijf elke element_type naar aparte sheet
                for element_type, df in dfs_by_type.items():
                    # Sanitize sheet name (max 31 chars, geen special chars)
                    sheet_name = self._sanitize_sheet_name(element_type)
                    
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.info(f"Sheet '{sheet_name}' geschreven: {len(df)} rijen")
                
                # Schrijf summary sheet
                self._write_summary_sheet(writer, validation_stats)
            
            logger.info(f"Excel bestand succesvol opgeslagen: {self.output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Fout bij exporteren naar Excel: {e}")
            return False
    
    def _sanitize_sheet_name(self, name: str, max_length: int = 31) -> str:
        """
        Zet element_type naam om naar geldige Excel sheet naam.
        """
        # Verwijder IFC prefix
        if name.upper().startswith('IFC'):
            name = name[3:]
        
        # Vervang invalid characters
        invalid_chars = r'[\\/?*\[\]]'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Truncate naar max length
        name = name[:max_length]
        
        return name
    
    def _write_summary_sheet(self, writer, validation_stats: dict):
        """
        Schrijf summary/statistieken sheet.
        """
        summary_data = {
            'Metriek': [
                'Totaal rijen',
                'Unieke elementen',
                'Elementen met materiaal',
                'Elementen zonder materiaal',
                'Materiaal coverage (%)'
            ],
            'Waarde': [
                validation_stats.get('total_rows', 0),
                validation_stats.get('unique_elements', 0),
                validation_stats.get('elements_with_material', 0),
                validation_stats.get('elements_without_material', 0),
                f"{validation_stats.get('material_coverage_percentage', 0):.1f}%"
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='SUMMARY', index=False)
        logger.info("Summary sheet geschreven")