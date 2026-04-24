from core.logger import setup_logger

logger = setup_logger(__name__)

class LayersetProcessor:
    """
    Gespecialiseerde processor voor IFCMATERIALLAYERSET.
    
    Extraheert laag-specifieke informatie:
    - Laag diktes
    - Laag volgorde
    - Laag ventilatie info
    """
    
    def __init__(self):
        pass
    
    def process_layerset_for_element(self, element) -> dict:
        """
        Process layersets gekoppeld aan element.
        
        Returns:
            {
                'has_layerset': bool,
                'total_thickness': float,
                'layer_count': int,
                'layers': [
                    {
                        'layer_index': int,
                        'material_name': str,
                        'layer_thickness': float,
                        'is_ventilated': bool
                    },
                    ...
                ]
            }
        """
        result = {
            'has_layerset': False,
            'total_thickness': None,
            'layer_count': 0,
            'layers': []
        }
        
        try:
            if not hasattr(element, 'HasAssociations') or not element.HasAssociations:
                return result
            
            for rel in element.HasAssociations:
                if not rel.is_a('IFCRELASSOCIATESMATERIAL'):
                    continue
                
                if not hasattr(rel, 'RelatingMaterial'):
                    continue
                
                material_obj = rel.RelatingMaterial
                
                if not material_obj.is_a('IFCMATERIALLAYERSET'):
                    continue
                
                result['has_layerset'] = True
                self._extract_layer_details(material_obj, result)
        
        except Exception as e:
            logger.debug(f"Error processing layerset: {e}")
        
        return result
    
    def _extract_layer_details(self, layerset_obj, result: dict):
        """Extract gedetailleerde layer informatie."""
        try:
            if hasattr(layerset_obj, 'TotalThickness') and layerset_obj.TotalThickness:
                result['total_thickness'] = float(layerset_obj.TotalThickness)
            
            if not hasattr(layerset_obj, 'MaterialLayers') or not layerset_obj.MaterialLayers:
                return
            
            result['layer_count'] = len(layerset_obj.MaterialLayers)
            
            for layer_idx, layer in enumerate(layerset_obj.MaterialLayers):
                try:
                    layer_info = {
                        'layer_index': layer_idx,
                        'material_name': 'Unknown',
                        'layer_thickness': None,
                        'is_ventilated': False
                    }
                    
                    # Material name
                    if hasattr(layer, 'Material') and layer.Material:
                        if hasattr(layer.Material, 'Name'):
                            layer_info['material_name'] = str(layer.Material.Name)
                    
                    # Layer thickness
                    if hasattr(layer, 'LayerThickness') and layer.LayerThickness is not None:
                        layer_info['layer_thickness'] = float(layer.LayerThickness)
                    
                    # Ventilated
                    if hasattr(layer, 'IsVentilated') and layer.IsVentilated is not None:
                        layer_info['is_ventilated'] = bool(layer.IsVentilated)
                    
                    result['layers'].append(layer_info)
                
                except Exception as e:
                    logger.debug(f"Error processing layer {layer_idx}: {e}")
        
        except Exception as e:
            logger.debug(f"Error extracting layer details: {e}")
    
    def get_total_layer_thickness(self, layerset_obj) -> float:
        """Haal totale dikte uit layerset."""
        try:
            if hasattr(layerset_obj, 'TotalThickness') and layerset_obj.TotalThickness:
                return float(layerset_obj.TotalThickness)
        except:
            pass
        
        return None