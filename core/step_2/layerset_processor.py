from config.config import MATERIAL_SOURCE_LAYERSET, DATA_QUALITY_OK
from core.logger import setup_logger

logger = setup_logger(__name__)

class LayerSetProcessor:
    """
    Verwerkt IFCMATERIALLAYERSET (gelaagde bouwmaterialen).
    Elk materiaal wordt apart opgeslagen met zijn dikte en LayerSetName.
    """
    
    def __init__(self, ifc_file, validator, cache):
        self.ifc_file = ifc_file
        self.validator = validator
        self.cache = cache
    
    def process_layerset(self, element, layerset_obj):
        """
        Verwerk gelaagde materialen.
        
        Args:
            element: IFC element
            layerset_obj: IFCMATERIALLAYERSET object
        
        Returns:
            list van material dicts (één per laag)
        """
        materials = []
        
        try:
            layerset_name = layerset_obj.LayerSetName if hasattr(layerset_obj, 'LayerSetName') and layerset_obj.LayerSetName else "Unknown"
            
            # Haal lagen op
            if hasattr(layerset_obj, 'MaterialLayers'):
                layers = layerset_obj.MaterialLayers
                
                for layer_index, layer_obj in enumerate(layers, start=1):
                    try:
                        material_entry = self._extract_layer_material(
                            element, 
                            layer_obj, 
                            layer_index, 
                            layerset_name
                        )
                        
                        if material_entry:
                            materials.append(material_entry)
                    
                    except Exception as e:
                        logger.debug(f"Fout bij verwerking layer {layer_index}: {e}")
                        continue
        
        except Exception as e:
            logger.debug(f"Fout bij verwerking layerset (element {element.id()}): {e}")
        
        return materials
    
    def _extract_layer_material(self, element, layer_obj, layer_index, layerset_name):
        """
        Extract materiaal en dikte uit één laag.
        """
        try:
            # Haal materiaal op
            material_obj = layer_obj.Material if hasattr(layer_obj, 'Material') else None
            material_name = material_obj.Name if material_obj and hasattr(material_obj, 'Name') and material_obj.Name else "Unknown"
            
            # Haal dikte op (in meters)
            layer_thickness = layer_obj.LayerThickness if hasattr(layer_obj, 'LayerThickness') else None
            
            material_data = {
                'element_id': element.id(),
                'element_type': element.is_a(),
                'material_name': material_name,
                'material_type': 'IFCMATERIAL',
                'layer_thickness': float(layer_thickness) if layer_thickness else None,
                'layer_index': layer_index,
                'constituent_fraction': None,
                'layerset_name': layerset_name,
                'data_quality_flag': DATA_QUALITY_OK,
                'source': MATERIAL_SOURCE_LAYERSET,
                'notes': f'Layer {layer_index} from IFCMATERIALLAYERSET'
            }
            
            # Valideer
            material_data = self.validator.validate_material_entry(material_data)
            
            return material_data
        
        except Exception as e:
            logger.debug(f"Fout bij extractie laag materiaal: {e}")
            return None