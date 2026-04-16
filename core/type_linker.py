from core.logger import setup_logger

logger = setup_logger(__name__)

class TypeLinker:
    """
    Koppelt elementen aan hun TYPE-definities en haalt type-informatie op.
    """
    
    def __init__(self, ifc_file):
        self.ifc_file = ifc_file
        self.type_cache = {}  # Cache voor sneller opzoeken
    
    def get_type_link_and_name(self, element):
        """
        Haal TYPE-relatie en type-naam op van een element.
        
        Args:
            element: IFC-element object
        
        Returns:
            tuple: (type_link_id, type_name) of (None, None)
        """
        try:
            # Controleer of element TYPE-relatie heeft
            type_obj = self._get_type_object(element)
            
            if type_obj is None:
                return None, None
            
            type_id = type_obj.id()
            type_name = self._get_type_name(type_obj)
            
            return type_id, type_name
        
        except Exception as e:
            logger.debug(f"Fout bij type-linking voor element {element.id()}: {e}")
            return None, None
    
    def _get_type_object(self, element):
        """
        Haal het TYPE-object op van een element.
        Zoekt via IFCRELDEFINESBYTYPE relatie.
        """
        try:
            # Check cache eerst
            element_id = element.id()
            if element_id in self.type_cache:
                return self.type_cache[element_id]
            
            # Methode 1: Direct via IsDefinedBy
            if hasattr(element, 'IsDefinedBy'):
                for rel in element.IsDefinedBy:
                    if rel.is_a('IFCRELDEFINESBYTYPE'):
                        if hasattr(rel, 'RelatingType'):
                            type_obj = rel.RelatingType
                            self.type_cache[element_id] = type_obj
                            return type_obj
            
            # Methode 2: Via RelatedObjects (inverse relatie)
            related_objects = self.ifc_file.by_type('IFCRELDEFINESBYTYPE')
            for rel in related_objects:
                if hasattr(rel, 'RelatedObjects'):
                    if element in rel.RelatedObjects:
                        if hasattr(rel, 'RelatingType'):
                            type_obj = rel.RelatingType
                            self.type_cache[element_id] = type_obj
                            return type_obj
            
            self.type_cache[element_id] = None
            return None
        
        except Exception as e:
            logger.debug(f"_get_type_object fout: {e}")
            return None
    
    def _get_type_name(self, type_obj):
        """
        Haal de naam van het TYPE-object op.
        Fallback: gebruik klassenaam als Name ontbreekt.
        """
        try:
            if hasattr(type_obj, 'Name') and type_obj.Name:
                return type_obj.Name
            else:
                # Fallback: klassennaam
                return type_obj.is_a()
        
        except Exception as e:
            logger.debug(f"_get_type_name fout: {e}")
            return type_obj.is_a() if type_obj else "UNKNOWN"