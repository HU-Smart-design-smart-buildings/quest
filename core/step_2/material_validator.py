from core.logger import setup_logger

logger = setup_logger(__name__)

class MaterialValidator:
    """
    Valideert materiaaldata en voegt quality flags toe.
    """
    
    def __init__(self):
        self.validation_issues = []
    
    def validate_material_entry(self, material_data):
        """
        Valideer één materiaal-entry en return aangevulde data met quality flag.
        
        Args:
            material_data: dict met material info
        
        Returns:
            dict met material info + quality_flag + notes
        """
        quality_flag = "OK"
        missing_fields = []
        
        # Controleer kritieke velden
        if not material_data.get('material_name') or material_data.get('material_name') == 'Unknown':
            missing_fields.append('material_name')
        
        # Thickness validatie (als aanwezig, moet positief zijn)
        if material_data.get('layer_thickness') is not None:
            try:
                thickness = float(material_data.get('layer_thickness', 0))
                if thickness < 0:
                    missing_fields.append('layer_thickness (negative)')
                    logger.warning(f"Negatieve dikte gedetecteerd: {thickness}")
                elif thickness == 0:
                    logger.debug(f"Zero thickness voor {material_data.get('material_name')}")
            except (ValueError, TypeError):
                missing_fields.append('layer_thickness (invalid)')
        
        # Constituent fraction validatie (moet 0-1 zijn als aanwezig)
        if material_data.get('constituent_fraction') is not None:
            try:
                fraction = float(material_data.get('constituent_fraction', 0))
                if fraction < 0 or fraction > 1:
                    missing_fields.append('constituent_fraction (out of range)')
                    logger.warning(f"Fraction buiten bereik (0-1): {fraction}")
            except (ValueError, TypeError):
                missing_fields.append('constituent_fraction (invalid)')
        
        # Zet quality flag
        if missing_fields:
            quality_flag = f"MISSING: {', '.join(missing_fields)}"
        
        # Voeg metadata toe
        material_data['data_quality_flag'] = quality_flag
        
        # Log indien nodig
        if quality_flag != "OK":
            self.validation_issues.append({
                'element_id': material_data.get('element_id'),
                'issue': quality_flag
            })
        
        return material_data
    
    def get_validation_summary(self):
        """
        Retourneer samenvatting van validatie-issues.
        """
        total_issues = len(self.validation_issues)
        
        if total_issues == 0:
            return "✓ Geen validatie-issues gevonden"
        
        return f"⚠ {total_issues} validatie-issues gevonden"