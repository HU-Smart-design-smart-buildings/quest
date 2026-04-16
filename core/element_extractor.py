import pandas as pd
from config.config import UNIVERSAL_BUILDING_ELEMENTS, EXCLUDED_ELEMENTS
from core.logger import setup_logger
from core.material_detector import MaterialDetector
from core.geometry_detector import GeometryDetector
from core.type_linker import TypeLinker

logger = setup_logger(__name__)

class ElementExtractor:
    """
    Extraheert alle bouwkundige elementen uit het IFC-bestand.
    """
    
    def __init__(self, ifc_file, ifc_version_enum):
        self.ifc_file = ifc_file
        self.ifc_version_enum = ifc_version_enum
        
        # Initialiseer detectoren
        self.material_detector = MaterialDetector(ifc_file)
        self.geometry_detector = GeometryDetector(ifc_file)
        self.type_linker = TypeLinker(ifc_file)
        
        # Tussentijdse data
        self.elements_data = []
        self.parent_map = {}  # Voor nested elements
    
    def extract_all_elements(self):
        """
        Extraheert alle bouwkundige elementen uit het model.
        
        Returns:
            pd.DataFrame met element-informatie
        """
        logger.info("=" * 60)
        logger.info("STAP 1: Bouwkundige elementen verzamelen")
        logger.info("=" * 60)
        
        # Stap 1: Bouw parent-relatie map voor nested elements
        logger.info("Stap 1.1: Parent-relatie map opbouwen...")
        self._build_parent_map()
        
        # Stap 2: Haal alle elementen op
        logger.info("Stap 1.2: Alle bouwkundige elementen ophalen...")
        self._extract_elements()
        
        # Stap 3: Zet in DataFrame
        logger.info("Stap 1.3: Resultaten omzetten naar DataFrame...")
        df = pd.DataFrame(self.elements_data)
        
        logger.info(f"✓ {len(df)} elementen geëxtraheerd")
        logger.info("=" * 60)
        
        return df
    
    def _build_parent_map(self):
        """
        Bouw een map op van parent-child relaties.
        Dit helpt om nested elements te identificeren.
        """
        try:
            # Controleer IFCRELCONTAINEDINSPATIALSTRUCTURE relaties
            containment_rels = self.ifc_file.by_type('IFCRELCONTAINEDINSPATIALSTRUCTURE')
            
            for rel in containment_rels:
                try:
                    parent = rel.RelatingStructure
                    children = rel.RelatedElements
                    
                    for child in children:
                        self.parent_map[child.id()] = parent
                except Exception as e:
                    logger.debug(f"Fout bij parent-map opbouw: {e}")
        
        except Exception as e:
            logger.warning(f"Kon parent-map niet opbouwen: {e}")
    
    def _extract_elements(self):
        """
        Haal alle bouwkundige elementen op en verzamel informatie.
        """
        extracted_count = 0
        
        for element_type in UNIVERSAL_BUILDING_ELEMENTS:
            try:
                logger.debug(f"Verwerking van {element_type}...")
                elements = self.ifc_file.by_type(element_type)
                
                for element in elements:
                    try:
                        # Controleer of element in uitgesloten lijst zit
                        if element.is_a() in EXCLUDED_ELEMENTS:
                            continue
                        
                        # Haal alle informatie op
                        element_data = self._extract_element_info(element)
                        
                        if element_data:
                            self.elements_data.append(element_data)
                            extracted_count += 1
                    
                    except Exception as e:
                        logger.debug(f"Fout bij verwerking van element: {e}")
                        continue
            
            except Exception as e:
                logger.warning(f"Kon elementen van type {element_type} niet ophalen: {e}")
                continue
        
        logger.info(f"✓ {extracted_count} elementen succesvol verwerkt")
    
    def _extract_element_info(self, element):
        """
        Extraheert alle informatie voor één element.
        """
        try:
            element_id = element.id()
            element_type = element.is_a()
            element_name = self._get_element_name(element, element_id, element_type)
            
            # Haal TYPE-informatie op
            type_link, type_name = self.type_linker.get_type_link_and_name(element)
            
            # Detecteer materiaal- en geometrie-informatie
            has_material = self.material_detector.has_material_info(element)
            has_geometry = self.geometry_detector.has_geometric_representation(element)
            
            # Haal parent-element op (als aanwezig)
            parent_element_id = self.parent_map.get(element_id)
            
            element_data = {
                'element_id': element_id,
                'element_type': element_type,
                'element_name': element_name,
                'type_link': type_link,
                'type_name': type_name,
                'has_material_info': has_material,
                'geometric_representation': has_geometry,
                'parent_element_id': parent_element_id
            }
            
            return element_data
        
        except Exception as e:
            logger.debug(f"Fout bij element-info extractie: {e}")
            return None
    
    def _get_element_name(self, element, element_id, element_type):
        """
        Haal element-naam op met fallback naar generieke naam.
        """
        try:
            if hasattr(element, 'Name') and element.Name:
                return element.Name
            else:
                # Fallback: generieke naam
                return f"{element_type}_{element_id}"
        
        except Exception as e:
            logger.debug(f"Fout bij element-naamgeving: {e}")
            return f"{element_type}_{element_id}"