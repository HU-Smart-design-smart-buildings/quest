from config.config import MATERIAL_SOURCE_DIRECT, DATA_QUALITY_OK
from core.logger import setup_logger

logger = setup_logger(__name__)

class MaterialLinker:
    """
    Haalt directe materiaalkoppelingen op uit elementen.
    Dit zijn echte koppelingen (NIET via types).
    """
    
    def __init__(self, ifc_file, validator, cache):
        self.ifc_file = ifc_file
        self.validator = validator
        self.cache = cache
    
    def get_direct_materials(self, element):
        """
        Haal directe materialen op uit een element.
        
        Returns:
            list van material dicts
        """
        materials = []
        
        try:
            # Controleer IFCRELASSOCIATESMATERIAL relaties
            if hasattr(element, 'HasAssociations'):
                for rel in element.HasAssociations:
                    if rel.is_a('IFCRELASSOCIATESMATERIAL'):
                        if hasattr(rel, 'RelatingMaterial'):
                            material_obj = rel.RelatingMaterial
                            
                            # Bepaal material type
                            if material_obj.is_a('IFCMATERIAL'):
                                material_data = self._extract_simple_material(element, material_obj)
                                materials.append(material_data)
                            
                            elif material_obj.is_a('IFCMATERIALLAYERSET'):
                                # Dit wordt door LayerSetProcessor afgehandeld
                                pass
                            
                            elif material_obj.is_a('IFCMATERIALCONSTITUENTSET'):
                                # Dit wordt door ConstituentProcessor afgehandeld
                                pass
        
        except Exception as e:
            logger.debug(f"Fout bij ophalen directe materialen (element {element.id()}): {e}")
        
        return materials
    
    def _extract_simple_material(self, element, material_obj):
        """
        Extract gegevens van IFCMATERIAL object.
        """
        try:
            material_name = material_obj.Name if hasattr(material_obj, 'Name') and material_obj.Name else "Unknown"
            
            material_data = {
                'element_id': element.id(),
                'element_type': element.is_a(),
                'material_name': material_name,
                'material_type': 'IFCMATERIAL',
                'layer_thickness': None,
                'layer_index': None,
                'constituent_fraction': None,
                'layerset_name': None,
                'data_quality_flag': DATA_QUALITY_OK,
                'source': MATERIAL_SOURCE_DIRECT,
                'notes': 'Direct material link'
            }
            
            # Valideer
            material_data = self.validator.validate_material_entry(material_data)
            
            return material_data
        
        except Exception as e:
            logger.debug(f"Fout bij extractie simple material: {e}")
            return None