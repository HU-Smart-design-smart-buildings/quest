from core.logger import setup_logger

logger = setup_logger(__name__)

class MaterialLoader:
    """
    Laadt alle materiaal-koppelingen uit een IFC-element.
    
    Ondersteunt:
    - IFCMATERIAL (direct)
    - IFCMATERIALLAYERSET (lagen)
    - IFCMATERIALCONSTITUENTSET (constituents)
    - IFCMATERIALPROFILESET (profielen)
    """
    
    def __init__(self, ifc_file):
        self.ifc_file = ifc_file
    
    def get_materials_for_element(self, element) -> list:
        """
        Haal alle materialen gekoppeld aan een element.
        
        Returns:
            List van dicts met materiaal info
        """
        materials = []
        
        try:
            if not hasattr(element, 'HasAssociations') or not element.HasAssociations:
                return materials
            
            for rel in element.HasAssociations:
                if not rel.is_a('IFCRELASSOCIATESMATERIAL'):
                    continue
                
                if not hasattr(rel, 'RelatingMaterial'):
                    continue
                
                material_obj = rel.RelatingMaterial
                
                # DIRECT MATERIAL
                if material_obj.is_a('IFCMATERIAL'):
                    materials.append({
                        'material_name': material_obj.Name if hasattr(material_obj, 'Name') else 'Unknown',
                        'material_type': 'DIRECT',
                        'material_id': material_obj.id() if hasattr(material_obj, 'id') else None,
                        'description': material_obj.Description if hasattr(material_obj, 'Description') else None
                    })
                
                # LAYERSET
                elif material_obj.is_a('IFCMATERIALLAYERSET'):
                    layerset_materials = self._process_layerset(material_obj)
                    materials.extend(layerset_materials)
                
                # CONSTITUENT SET
                elif material_obj.is_a('IFCMATERIALCONSTITUENTSET'):
                    constituent_materials = self._process_constituent_set(material_obj)
                    materials.extend(constituent_materials)
                
                # PROFILE SET
                elif material_obj.is_a('IFCMATERIALPROFILESET'):
                    profile_materials = self._process_profile_set(material_obj)
                    materials.extend(profile_materials)
        
        except Exception as e:
            logger.debug(f"Error getting materials: {e}")
        
        return materials
    
    def _process_layerset(self, layerset_obj) -> list:
        """Process IFCMATERIALLAYERSET."""
        materials = []
        
        try:
            if not hasattr(layerset_obj, 'MaterialLayers') or not layerset_obj.MaterialLayers:
                return materials
            
            layerset_name = layerset_obj.Name if hasattr(layerset_obj, 'Name') else 'Unknown'
            total_thickness = layerset_obj.TotalThickness if hasattr(layerset_obj, 'TotalThickness') else None
            
            for layer_idx, layer in enumerate(layerset_obj.MaterialLayers):
                try:
                    material_name = 'Unknown'
                    material_id = None
                    layer_thickness = None
                    is_ventilated = None
                    
                    if hasattr(layer, 'Material') and layer.Material:
                        material_name = layer.Material.Name if hasattr(layer.Material, 'Name') else 'Unknown'
                        material_id = layer.Material.id() if hasattr(layer.Material, 'id') else None
                    
                    if hasattr(layer, 'LayerThickness'):
                        layer_thickness = float(layer.LayerThickness)
                    
                    if hasattr(layer, 'IsVentilated'):
                        is_ventilated = layer.IsVentilated
                    
                    materials.append({
                        'material_name': material_name,
                        'material_type': 'LAYERSET',
                        'material_id': material_id,
                        'layerset_name': layerset_name,
                        'layer_index': layer_idx,
                        'layer_thickness': layer_thickness,
                        'total_layerset_thickness': total_thickness,
                        'is_ventilated': is_ventilated
                    })
                
                except Exception as e:
                    logger.debug(f"Error processing layer {layer_idx}: {e}")
        
        except Exception as e:
            logger.debug(f"Error processing layerset: {e}")
        
        return materials
    
    def _process_constituent_set(self, constituent_set_obj) -> list:
        """Process IFCMATERIALCONSTITUENTSET."""
        materials = []
        
        try:
            if not hasattr(constituent_set_obj, 'Constituents') or not constituent_set_obj.Constituents:
                return materials
            
            for const_idx, constituent in enumerate(constituent_set_obj.Constituents):
                try:
                    material_name = 'Unknown'
                    material_id = None
                    fraction = None
                    component_description = None
                    
                    if hasattr(constituent, 'Material') and constituent.Material:
                        material_name = constituent.Material.Name if hasattr(constituent.Material, 'Name') else 'Unknown'
                        material_id = constituent.Material.id() if hasattr(constituent.Material, 'id') else None
                    
                    if hasattr(constituent, 'Fraction'):
                        fraction = float(constituent.Fraction)
                    
                    if hasattr(constituent, 'ComponentDescription'):
                        component_description = constituent.ComponentDescription
                    
                    materials.append({
                        'material_name': material_name,
                        'material_type': 'CONSTITUENT',
                        'material_id': material_id,
                        'constituent_fraction': fraction,
                        'constituent_index': const_idx,
                        'component_description': component_description
                    })
                
                except Exception as e:
                    logger.debug(f"Error processing constituent {const_idx}: {e}")
        
        except Exception as e:
            logger.debug(f"Error processing constituent set: {e}")
        
        return materials
    
    def _process_profile_set(self, profile_set_obj) -> list:
        """Process IFCMATERIALPROFILESET."""
        materials = []
        
        try:
            if hasattr(profile_set_obj, 'MaterialProfiles') and profile_set_obj.MaterialProfiles:
                for prof_idx, profile in enumerate(profile_set_obj.MaterialProfiles):
                    try:
                        material_name = 'Unknown'
                        material_id = None
                        profile_name = None
                        
                        if hasattr(profile, 'Material') and profile.Material:
                            material_name = profile.Material.Name if hasattr(profile.Material, 'Name') else 'Unknown'
                            material_id = profile.Material.id() if hasattr(profile.Material, 'id') else None
                        
                        if hasattr(profile, 'Profile') and profile.Profile:
                            profile_obj = profile.Profile
                            profile_name = profile_obj.ProfileName if hasattr(profile_obj, 'ProfileName') else None
                        
                        materials.append({
                            'material_name': material_name,
                            'material_type': 'PROFILESET',
                            'material_id': material_id,
                            'profile_name': profile_name,
                            'profile_index': prof_idx
                        })
                    
                    except Exception as e:
                        logger.debug(f"Error processing profile {prof_idx}: {e}")
        
        except Exception as e:
            logger.debug(f"Error processing profile set: {e}")
        
        return materials