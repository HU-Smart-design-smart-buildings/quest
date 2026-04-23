from typing import Optional, Dict
from core.logger import setup_logger

logger = setup_logger(__name__)

class StyleMaterialResolver:
    """
    Resolver voor STYLE-based materialen.
    
    In sommige BIM-modellen kan materiaalinformatie ALLEEN via styling/uiterlijk gedefinieerd zijn.
    Dit zoekt naar:
    - IFCSTYLEDITEM → IFCSURFACESTYLE → materiaal info
    - Kleur/textuur eigenschappen die naar materiaal verwijzen
    
    Voorbeeld:
    - IFCWALL
        → HasShapeAspect → IFCSTYLEDITEM
            → Styles → IFCPRESENTATIONSTYLEASSIGNMENT
                → Styles → IFCSURFACESTYLE
    
    Opmerking: Dit is een less-common fallback maar kan in bepaalde modellen voorkomen.
    """
    
    def __init__(self):
        # Mapping van style-kenmerken naar materialen
        self.style_to_material_map = {
            'concrete': 'Beton',
            'steel': 'Staal',
            'brick': 'Keramiek',
            'wood': 'Hout',
            'glass': 'Glas',
            'aluminum': 'Aluminium',
            'copper': 'Koper',
            'bitumen': 'Bitumen',
            'gypsum': 'Gips'
        }
    
    def resolve_material_from_style(self, element, element_id: int) -> Optional[Dict]:
        """
        Probeer materiaal op te halen via STYLE informatie.
        
        Args:
            element: IFC element object
            element_id: ID van het element
        
        Returns:
            Dict met materiaalgegevens OF None
        """
        try:
            # Stap 1: Zoek IFCSTYLEDITEM
            styled_items = self._find_styled_items(element)
            
            if not styled_items:
                logger.debug(f"Element {element_id}: Geen IFCSTYLEDITEM gevonden")
                return None
            
            # Stap 2: Extract materiaal info uit styles
            for styled_item in styled_items:
                material = self._extract_material_from_styled_item(styled_item, element_id)
                
                if material:
                    logger.info(
                        f"Element {element_id}: Materiaal via STYLE opgehaald: {material.get('material_name')}"
                    )
                    return material
            
            logger.debug(f"Element {element_id}: Geen materiaal in STYLE info gevonden")
            return None
        
        except Exception as e:
            logger.debug(f"Fout bij Style resolver voor element {element_id}: {e}")
            return None
    
    def _find_styled_items(self, element) -> list:
        """
        Vind alle IFCSTYLEDITEM gekoppeld aan element.
        """
        styled_items = []
        
        try:
            # Method 1: Via de element self
            if element.is_a('IFCSTYLEDITEM'):
                styled_items.append(element)
            
            # Method 2: Via StyledByItem relatie
            if hasattr(element, 'StyledByItem') and element.StyledByItem:
                for styled in element.StyledByItem:
                    if styled.is_a('IFCSTYLEDITEM'):
                        styled_items.append(styled)
            
            # Method 3: Via geometry representation
            if hasattr(element, 'Representation') and element.Representation:
                for rep in element.Representation.Representations:
                    if hasattr(rep, 'Items'):
                        for item in rep.Items:
                            if item.is_a('IFCMAPPEDITEM') or item.is_a('IFCSTYLEDITEM'):
                                styled_items.append(item)
        
        except Exception as e:
            logger.debug(f"Fout bij vinden IFCSTYLEDITEM: {e}")
        
        return styled_items
    
    def _extract_material_from_styled_item(self, styled_item, element_id: int) -> Optional[Dict]:
        """
        Extract materiaal informatie uit IFCSTYLEDITEM.
        """
        try:
            if not hasattr(styled_item, 'Styles'):
                return None
            
            # Itereer door styles
            for style in styled_item.Styles:
                if not style.is_a('IFCPRESENTATIONSTYLEASSIGNMENT'):
                    continue
                
                if hasattr(style, 'Styles'):
                    for surface_style in style.Styles:
                        if not surface_style.is_a('IFCSURFACESTYLE'):
                            continue
                        
                        # Zoek naar material name in surface style
                        if hasattr(surface_style, 'Name') and surface_style.Name:
                            material_name = self._map_style_to_material(surface_style.Name)
                            
                            if material_name != "Unknown":
                                logger.debug(
                                    f"Element {element_id}: Style '{surface_style.Name}' gemapped naar '{material_name}'"
                                )
                                
                                return {
                                    'material_name': material_name,
                                    'material_type': 'IFCSURFACESTYLE',
                                    'source': 'STYLE',
                                    'resolution_method': 'IFCSTYLEDITEM → IFCSURFACESTYLE',
                                    'style_name': surface_style.Name
                                }
            
            return None
        
        except Exception as e:
            logger.debug(f"Fout bij extract material van styled item: {e}")
            return None
    
    def _map_style_to_material(self, style_name: str) -> str:
        """
        Map style naam naar materiaal naam.
        """
        style_lower = style_name.lower()
        
        for key, value in self.style_to_material_map.items():
            if key in style_lower:
                return value
        
        return "Unknown"