from core.logger import setup_logger

logger = setup_logger(__name__)

class QuantityExtractor:
    """
    Extraheert volumes, lengtes, breedtes en hoogtes uit 
    IFCQUANTITYVOLUME, IFCQUANTITYLENGTH, IFCQUANTITYAREA
    """
    
    def __init__(self):
        pass
    
    def extract_quantities(self, element) -> dict:
        """
        Haal alle quantities uit element.
        
        Returns:
            Dict met volume_m3, height, length, width (allemaal optional)
        """
        quantities = {
            'volume_m3': None,
            'height': None,
            'length': None,
            'width': None,
            'area_m2': None
        }
        
        try:
            if not hasattr(element, 'HasPropertySets') or not element.HasPropertySets:
                return quantities
            
            for prop_set in element.HasPropertySets:
                # IFCELEMENTQUANTITYSET
                if prop_set.is_a('IFCELEMENTQUANTITYSET'):
                    self._extract_from_quantity_set(prop_set, quantities)
            
            return quantities
        
        except Exception as e:
            logger.debug(f"Error extracting quantities: {e}")
            return quantities
    
    def _extract_from_quantity_set(self, quantity_set, quantities: dict):
        """Extraheer waarden uit IFCELEMENTQUANTITYSET."""
        try:
            if not hasattr(quantity_set, 'Quantities') or not quantity_set.Quantities:
                return
            
            for qty in quantity_set.Quantities:
                try:
                    qty_name = qty.Name if hasattr(qty, 'Name') else None
                    qty_value = None
                    
                    # VOLUME
                    if qty.is_a('IFCQUANTITYVOLUME'):
                        if hasattr(qty, 'VolumeValue') and qty.VolumeValue is not None:
                            qty_value = float(qty.VolumeValue)
                            quantities['volume_m3'] = qty_value
                    
                    # LENGTH
                    elif qty.is_a('IFCQUANTITYLENGTH'):
                        if hasattr(qty, 'LengthValue') and qty.LengthValue is not None:
                            qty_value = float(qty.LengthValue)
                            # Map to correct field based on name
                            if qty_name and 'HEIGHT' in qty_name.upper():
                                quantities['height'] = qty_value
                            elif qty_name and 'LENGTH' in qty_name.upper():
                                quantities['length'] = qty_value
                            elif qty_name and 'WIDTH' in qty_name.upper():
                                quantities['width'] = qty_value
                            else:
                                # Default to length if no specific name
                                if quantities['length'] is None:
                                    quantities['length'] = qty_value
                    
                    # AREA
                    elif qty.is_a('IFCQUANTITYAREA'):
                        if hasattr(qty, 'AreaValue') and qty.AreaValue is not None:
                            qty_value = float(qty.AreaValue)
                            quantities['area_m2'] = qty_value
                
                except Exception as e:
                    logger.debug(f"Error extracting quantity {qty_name}: {e}")
        
        except Exception as e:
            logger.debug(f"Error in quantity set extraction: {e}")