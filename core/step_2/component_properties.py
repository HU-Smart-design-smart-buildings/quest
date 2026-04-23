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
        self.component_materials_cache = {}  # Cache voor element materials
    
    def get_component_materials(self, element):
        """
        Haalt materialen op uit deur/raam eigenschappen.
        
        Returns:
            list van material dicts
        """
        materials = []
        
        try:
            element_type = element.is_a()
            element_id = element.id()
            
            if element_type == 'IFCDOOR':
                materials.extend(self._process_door_properties(element))
            
            elif element_type == 'IFCWINDOW':
                materials.extend(self._process_window_properties(element))
            
            # FALLBACK: Als componenten zonder materiaal zijn, geef ze hetzelfde materiaal als andere componenten
            materials = self._apply_material_fallback(element_id, materials)
        
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
    
    def _apply_material_fallback(self, element_id, materials):
        """
        FALLBACK MECHANISME: Als componenten "Unknown" materiaal hebben,
        geef ze hetzelfde materiaal als andere componenten van hetzelfde element.
        
        Voorbeeld:
        - Door Lining: "Unknown" (geen material link gevonden)
        - Door Panel: "Hout" (material link gevonden)
        
        Result:
        - Door Lining: "Hout" (fallback naar panel)
        - Door Panel: "Hout"
        
        Args:
            element_id: ID van het element
            materials: list van material dicts
        
        Returns:
            lijst van material dicts met fallback toegepast
        """
        
        # Stap 1: Vind alle unieke materialen die WEL geïdentificeerd zijn (niet "Unknown")
        known_materials = [
            m for m in materials 
            if m.get('material_name') != 'Unknown'
        ]
        
        # Als er geen bekende materialen zijn, retourneer originele lijst
        if not known_materials:
            return materials
        
        # Stap 2: Selecteer het EERSTE bekende materiaal als fallback
        fallback_material_name = known_materials[0].get('material_name')
        fallback_source = known_materials[0].get('source')
        
        logger.debug(
            f"Fallback materiaal voor element {element_id}: '{fallback_material_name}' "
            f"(uit {fallback_source})"
        )
        
        # Stap 3: Vervang alle "Unknown" materialen met fallback
        updated_materials = []
        
        for material in materials:
            if material.get('material_name') == 'Unknown':
                # Duplicate materiaal object
                updated_material = material.copy()
                
                # Vervang met fallback
                updated_material['material_name'] = fallback_material_name
                
                # Update notes om aan te geven dat dit een fallback is
                original_notes = updated_material.get('notes', '')
                updated_material['notes'] = (
                    f"{original_notes} [FALLBACK: materiaal ingevuld van ander component: {fallback_material_name}]"
                )
                
                # Flag dat dit een fallback is
                updated_material['data_quality_flag'] = "FALLBACK_APPLIED"
                
                logger.debug(
                    f"Element {element_id}: {original_notes} -> "
                    f"'{fallback_material_name}' (fallback)"
                )
                
                updated_materials.append(updated_material)
            
            else:
                # Materiaal is al bekend, behoud het
                updated_materials.append(material)
        
        return updated_materials