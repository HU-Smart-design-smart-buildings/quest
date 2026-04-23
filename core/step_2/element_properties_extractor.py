from typing import Optional, Dict
from core.logger import setup_logger

logger = setup_logger(__name__)

class ElementPropertiesExtractor:
    """
    Extraheer element-specifieke properties:
    - Dikte (voor wanden, platen)
    - Breedte (voor balken, kolommen)
    - Lengte (voor balken, kolommen)
    - Element klasse/categorie
    - Materiaalklasse
    
    Haalt data op uit:
    - IFCPROPERTYSET
    - IFCQUANTITYSET (quantities)
    - Element type basiseigenschappen
    """
    
    def __init__(self):
        # Property namen die we zoeken
        self.thickness_names = [
            'Thickness', 'thickness', 'Wanddikte', 'wanddikte',
            'PanelThickness', 'WallThickness', 'Wandsterkung'
        ]
        self.width_names = [
            'Width', 'width', 'Breedte', 'breedte',
            'ProfileWidth', 'BeamWidth', 'ColumnWidth'
        ]
        self.height_names = [
            'Height', 'height', 'Hoogte', 'hoogte',
            'ProfileHeight', 'BeamHeight', 'ColumnHeight'
        ]
        self.length_names = [
            'Length', 'length', 'Lengte', 'lengte',
            'ElementLength', 'BeamLength'
        ]
    
    def extract_element_properties(self, element, element_id: int) -> Dict:
        """
        Extraheer alle element properties.
        
        Returns:
            Dict met thickness, width, height, length (als beschikbaar)
        """
        try:
            properties = {
                'thickness': None,
                'width': None,
                'height': None,
                'length': None,
                'element_class': None,
                'material_class': None
            }
            
            # Probeer via PropertySets
            if hasattr(element, 'HasPropertySets') and element.HasPropertySets:
                for prop_set in element.HasPropertySets:
                    self._extract_from_propertyset(prop_set, properties)
            
            # Probeer via element type
            if not properties['thickness']:
                self._extract_from_type(element, properties)
            
            # Filter None values
            properties = {k: v for k, v in properties.items() if v is not None}
            
            if properties:
                logger.debug(f"Element {element_id}: Properties opgehaald: {properties}")
            
            return properties
        
        except Exception as e:
            logger.debug(f"Fout bij element properties extraction {element_id}: {e}")
            return {}
    
    def _extract_from_propertyset(self, prop_set, properties: Dict):
        """
        Extraheer properties uit PropertySet.
        """
        try:
            if not hasattr(prop_set, 'HasProperties'):
                return
            
            for prop in prop_set.HasProperties:
                if not prop.is_a('IFCPROPERTYSINGLEVALUE') and not prop.is_a('IFCQUANTITYVOLUME'):
                    continue
                
                prop_name = prop.Name if hasattr(prop, 'Name') else None
                if not prop_name:
                    continue
                
                # Haal waarde op
                value = None
                if hasattr(prop, 'NominalValue') and prop.NominalValue:
                    value = prop.NominalValue.wrappedValue if hasattr(prop.NominalValue, 'wrappedValue') else prop.NominalValue
                
                if not value:
                    continue
                
                # Probeer te converteren naar float
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    value = str(value)
                
                # Match tegen bekende property namen
                if prop_name in self.thickness_names and properties['thickness'] is None:
                    properties['thickness'] = value
                
                elif prop_name in self.width_names and properties['width'] is None:
                    properties['width'] = value
                
                elif prop_name in self.height_names and properties['height'] is None:
                    properties['height'] = value
                
                elif prop_name in self.length_names and properties['length'] is None:
                    properties['length'] = value
                
                elif prop_name.lower() in ['materialclass', 'material_class']:
                    properties['material_class'] = str(value)
                
                elif prop_name.lower() in ['elementclass', 'element_class']:
                    properties['element_class'] = str(value)
        
        except Exception as e:
            logger.debug(f"Fout bij extract from propertyset: {e}")
    
    def _extract_from_type(self, element, properties: Dict):
        """
        Probeer properties uit element type te halen.
        """
        try:
            # Vind element type
            if hasattr(element, 'IsDefinedBy'):
                for rel in element.IsDefinedBy:
                    if rel.is_a('IFCRELDEFINESBYTYPE'):
                        if hasattr(rel, 'RelatingType'):
                            element_type = rel.RelatingType
                            
                            # Haal type properties
                            if hasattr(element_type, 'HasPropertySets'):
                                for prop_set in element_type.HasPropertySets:
                                    self._extract_from_propertyset(prop_set, properties)
        
        except Exception as e:
            logger.debug(f"Fout bij extract from type: {e}")
