from typing import Optional, Dict, List
from core.logger import setup_logger

logger = setup_logger(__name__)

class FallbackStrategyManager:
    """
    Manages fallback strategies in prioriteit volgorde.
    
    PRIORITEIT (van hoog naar laag):
    1. TYPE-based materialen
    2. PropertySet materialen
    3. Style-based materialen
    4. Unknown (geen fallback werkte)
    """
    
    def __init__(self, type_resolver, property_set_resolver, style_resolver):
        self.type_resolver = type_resolver
        self.property_set_resolver = property_set_resolver
        self.style_resolver = style_resolver
        
        self.resolution_count = {
            'TYPE': 0,
            'PROPERTYSETS': 0,
            'STYLE': 0,
            'UNRESOLVED': 0
        }
    
    def resolve_material(self, element, element_id: int, current_material_name: str) -> Optional[Dict]:
        """
        Probeer materiaal op te halen via alle fallback-strategieën in volgorde.
        
        Geeft op als:
        - Material is niet "Unknown"
        - OF: Alle fallback-strategieën zijn uitgeput
        
        Args:
            element: IFC element
            element_id: Element ID
            current_material_name: Huiding materiaal naam (van Stap 2)
        
        Returns:
            Dict met opgelost materiaal OF None
        """
        
        # Skip als materiaal al bekend is
        if current_material_name != 'Unknown':
            return None
        
        logger.debug(f"Element {element_id}: Start fallback resolution (material='Unknown')")
        
        # Strategie 1: TYPE-based
        result = self.type_resolver.resolve_material_from_type(element, element_id)
        if result:
            self.resolution_count['TYPE'] += 1
            return result
        
        # Strategie 2: PropertySet-based
        result = self.property_set_resolver.resolve_material_from_properties(element, element_id)
        if result:
            self.resolution_count['PROPERTYSETS'] += 1
            return result
        
        # Strategie 3: Style-based
        result = self.style_resolver.resolve_material_from_style(element, element_id)
        if result:
            self.resolution_count['STYLE'] += 1
            return result
        
        # Geen strategie werkte
        logger.debug(f"Element {element_id}: Geen fallback strategie slaagde")
        self.resolution_count['UNRESOLVED'] += 1
        return None
    
    def get_statistics(self) -> Dict:
        """
        Haal statistieken op over fallback resoluties.
        """
        total_resolved = sum([
            self.resolution_count['TYPE'],
            self.resolution_count['PROPERTYSETS'],
            self.resolution_count['STYLE']
        ])
        
        return {
            'total_resolved': total_resolved,
            'by_type': self.resolution_count['TYPE'],
            'by_propertyset': self.resolution_count['PROPERTYSETS'],
            'by_style': self.resolution_count['STYLE'],
            'unresolved': self.resolution_count['UNRESOLVED']
        }