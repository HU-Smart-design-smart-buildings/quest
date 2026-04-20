from config.config import MATERIAL_SOURCE_CONSTITUENT, DATA_QUALITY_OK
from core.logger import setup_logger

logger = setup_logger(__name__)

class ConstituentProcessor:
    """
    Verwerkt IFCMATERIALCONSTITUENTSET (samengestelde materialen).
    Elk component wordt apart opgeslagen met zijn percentage (fraction).
    """
    
    def __init__(self, ifc_file, validator, cache):
        self.ifc_file = ifc_file
        self.validator = validator
        self.cache = cache
    
    def process_constituent_set(self, element, constituent_set_obj):
        """
        Verwerk samengestelde materialen.
        
        Args:
            element: IFC element
            constituent_set_obj: IFCMATERIALCONSTITUENTSET object
        
        Returns:
            list van material dicts (één per constituent)
        """
        materials = []
        
        try:
            # Haal constituents op
            if hasattr(constituent_set_obj, 'Constituents'):
                constituents = constituent_set_obj.Constituents
                
                for constituent_obj in constituents:
                    try:
                        material_entry = self._extract_constituent_material(element, constituent_obj)
                        
                        if material_entry:
                            materials.append(material_entry)
                    
                    except Exception as e:
                        logger.debug(f"Fout bij verwerking constituent: {e}")
                        continue
        
        except Exception as e:
            logger.debug(f"Fout bij verwerking constituent set (element {element.id()}): {e}")
        
        return materials
    
    def _extract_constituent_material(self, element, constituent_obj):
        """
        Extract materiaal en percentage uit één constituent.
        """
        try:
            # Haal materiaal op
            material_obj = constituent_obj.Material if hasattr(constituent_obj, 'Material') else None
            material_name = material_obj.Name if material_obj and hasattr(material_obj, 'Name') and material_obj.Name else "Unknown"
            
            # Haal fraction op (0-1 range, converteer naar percentage)
            fraction = constituent_obj.Fraction if hasattr(constituent_obj, 'Fraction') else None
            constituent_fraction = float(fraction) if fraction else None
            
            material_data = {
                'element_id': element.id(),
                'element_type': element.is_a(),
                'material_name': material_name,
                'material_type': 'IFCMATERIAL',
                'layer_thickness': None,
                'layer_index': None,
                'constituent_fraction': constituent_fraction,  # 0-1 range
                'layerset_name': None,
                'data_quality_flag': DATA_QUALITY_OK,
                'source': MATERIAL_SOURCE_CONSTITUENT,
                'notes': f'Constituent with fraction {constituent_fraction}'
            }
            
            # Valideer
            material_data = self.validator.validate_material_entry(material_data)
            
            return material_data
        
        except Exception as e:
            logger.debug(f"Fout bij extractie constituent materiaal: {e}")
            return None