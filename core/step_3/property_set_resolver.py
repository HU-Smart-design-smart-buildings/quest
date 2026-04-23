import pandas as pd
from typing import Optional, Dict
from core.logger import setup_logger

logger = setup_logger(__name__)

class PropertySetResolver:
    """
    Resolver voor PROPERTY SET materialen.
    
    Sommige modellen slaan materiaalinfo op als IFCPROPERTYSET properties in plaats van
    via IFCRELASSOCIATESMATERIAL. Dit zoekt naar eigenschappen zoals:
    - "MaterialName"
    - "Material"
    - "MaterialCategory"
    - etc.
    
    Voorbeeld:
    - IFCWALL
    - → HasPropertySets
    -   → IFCPROPERTYSET "Basisgegevens"
    -     → IFCPROPERTYSINGLEVALUE "MaterialName" = "Beton"
    
    → Result: IFCWALL krijgt materiaal "Beton" van PropertySet
    """
    
    def __init__(self):
        self.material_property_names = [
            'MaterialName',
            'Material',
            'MaterialCategory',
            'MaterialType',
            'BaseMaterial',
            'MainMaterial',
            'PrimaryMaterial'
        ]
    
    def resolve_material_from_properties(self, element, element_id: int) -> Optional[Dict]:
        """
        Probeer materiaal op te halen via PROPERTY SETS.
        
        Args:
            element: IFC element object
            element_id: ID van het element
        
        Returns:
            Dict met materiaalgegevens OF None
        """
        try:
            if not hasattr(element, 'HasPropertySets') or not element.HasPropertySets:
                logger.debug(f"Element {element_id}: Geen PropertySets")
                return None
            
            # Itereer door alle PropertySets
            for prop_set in element.HasPropertySets:
                try:
                    material = self._extract_material_from_propertyset(prop_set, element_id)
                    
                    if material:
                        logger.info(
                            f"Element {element_id}: Materiaal via PropertySet opgehaald: {material.get('material_name')} "
                            f"(PropertySet: {prop_set.Name if hasattr(prop_set, 'Name') else 'Unknown'})"
                        )
                        return material
                
                except Exception as e:
                    logger.debug(f"Fout bij verwerking PropertySet: {e}")
                    continue
            
            logger.debug(f"Element {element_id}: Geen materiaal in PropertySets gevonden")
            return None
        
        except Exception as e:
            logger.debug(f"Fout bij PropertySet resolver voor element {element_id}: {e}")
            return None
    
    def _extract_material_from_propertyset(self, prop_set, element_id: int) -> Optional[Dict]:
        """
        Zoek naar materiael eigenschappen in PropertySet.
        """
        try:
            if not hasattr(prop_set, 'HasProperties'):
                return None
            
            # Itereer door alle properties
            for prop in prop_set.HasProperties:
                # Controleer of het een IFCPROPERTYSINGLEVALUE is
                if not prop.is_a('IFCPROPERTYSINGLEVALUE'):
                    continue
                
                # Controleer property naam
                prop_name = prop.Name if hasattr(prop, 'Name') else None
                
                if prop_name in self.material_property_names:
                    # Haal waarde op
                    if hasattr(prop, 'NominalValue') and prop.NominalValue:
                        material_value = prop.NominalValue.wrappedValue if hasattr(prop.NominalValue, 'wrappedValue') else str(prop.NominalValue)
                        
                        logger.debug(
                            f"Element {element_id}: Materiaal eigenschap gevonden: {prop_name} = {material_value}"
                        )
                        
                        return {
                            'material_name': str(material_value),
                            'material_type': 'IFCPROPERTYSET',
                            'source': 'PROPERTYSETS',
                            'resolution_method': f'IFCPROPERTYSET.{prop_name}',
                            'property_set_name': prop_set.Name if hasattr(prop_set, 'Name') else 'Unknown'
                        }
            
            return None
        
        except Exception as e:
            logger.debug(f"Fout bij extracten PropertySet materiaal: {e}")
            return None