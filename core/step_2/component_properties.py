from config.config import MATERIAL_SOURCE_COMPONENT, DATA_QUALITY_OK
from core.logger import setup_logger

logger = setup_logger(__name__)

class ComponentPropertiesProcessor:
    """
    Haalt materialen op uit deur- en raam-components via IFCDOORLININGPROPERTIES,
    IFCDOORPANELPROPERTIES, en IFCWINDOWSTYLEPROPERTIES.
    """
    
    def __init__(self, ifc_file, validator, cache):
        self.ifc_file = ifc_file
        self.validator = validator
        self.cache = cache
    
    def get_component_materials(self, element):
        """
        Haalt materialen op uit deur/raam eigenschappen.
        
        Returns:
            list van material dicts
        """
        materials = []
        
        try:
            element_type = element.is_a()
            
            if element_type == 'IFCDOOR':
                materials.extend(self._process_door_properties(element))
            
            elif element_type == 'IFCWINDOW':
                materials.extend(self._process_window_properties(element))
        
        except Exception as e:
            logger.debug(f"Fout bij verwerking component properties (element {element.id()}): {e}")
        
        return materials
    
    def _process_door_properties(self, element):
        """
        Verwerk IFCDOORLININGPROPERTIES en IFCDOORPANELPROPERTIES.
        """
        materials = []
        
        try:
            # Haal HasPropertySets op
            if hasattr(element, 'HasPropertySets'):
                for prop_set in element.HasPropertySets:
                    try:
                        # IFCDOORLININGPROPERTIES
                        if prop_set.is_a('IFCDOORLININGPROPERTIES'):
                            lining_material = self._extract_component_material(
                                element, 
                                prop_set, 
                                'Door Lining'
                            )
                            if lining_material:
                                materials.append(lining_material)
                        
                        # IFCDOORPANELPROPERTIES
                        if prop_set.is_a('IFCDOORPANELPROPERTIES'):
                            panel_material = self._extract_component_material(
                                element, 
                                prop_set, 
                                'Door Panel'
                            )
                            if panel_material:
                                materials.append(panel_material)
                    
                    except Exception as e:
                        logger.debug(f"Fout bij verwerking door property set: {e}")
                        continue
        
        except Exception as e:
            logger.debug(f"Fout bij verwerking deur properties: {e}")
        
        return materials
    
    def _process_window_properties(self, element):
        """
        Verwerk IFCWINDOWSTYLEPROPERTIES.
        """
        materials = []
        
        try:
            # Haal HasPropertySets op
            if hasattr(element, 'HasPropertySets'):
                for prop_set in element.HasPropertySets:
                    try:
                        if prop_set.is_a('IFCWINDOWSTYLEPROPERTIES'):
                            # Window frame material
                            frame_material = self._extract_component_material(
                                element, 
                                prop_set, 
                                'Window Frame'
                            )
                            if frame_material:
                                materials.append(frame_material)
                    
                    except Exception as e:
                        logger.debug(f"Fout bij verwerking window property set: {e}")
                        continue
        
        except Exception as e:
            logger.debug(f"Fout bij verwerking raam properties: {e}")
        
        return materials
    
    def _extract_component_material(self, element, prop_set, component_name):
        """
        Extract materiaal uit component property set.
        """
        try:
            # Zoek naar IFCRELASSOCIATESMATERIAL in HasAssociations van property set
            material_name = "Unknown"
            
            if hasattr(prop_set, 'HasAssociations'):
                for rel in prop_set.HasAssociations:
                    if rel.is_a('IFCRELASSOCIATESMATERIAL'):
                        if hasattr(rel, 'RelatingMaterial'):
                            material_obj = rel.RelatingMaterial
                            if hasattr(material_obj, 'Name') and material_obj.Name:
                                material_name = material_obj.Name
            
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
                'source': MATERIAL_SOURCE_COMPONENT,
                'notes': f'{component_name} component material'
            }
            
            # Valideer
            material_data = self.validator.validate_material_entry(material_data)
            
            return material_data
        
        except Exception as e:
            logger.debug(f"Fout bij extractie component materiaal: {e}")
            return None