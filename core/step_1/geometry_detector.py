import ifcopenshell.geom
from core.logger import setup_logger

logger = setup_logger(__name__)

class GeometryDetector:
    """
    Detecteert of een element geometrie-representatie heeft.
    TRUE = minstens één eigenschap is aanwezig (shape, representation, etc.)
    """
    
    def __init__(self, ifc_file):
        self.ifc_file = ifc_file
    
    def has_geometric_representation(self, element):
        """
        Controleer of een element geometrische representatie heeft.
        
        Args:
            element: IFC-element object
        
        Returns:
            bool: True als minstens één geometrische eigenschap aanwezig is
        """
        try:
            # Methode 1: Controleer op IFCPRODUCTDEFINITIONSHAPE
            if self._has_product_definition_shape(element):
                return True
            
            # Methode 2: Controleer op IFCSHAPEREPRESENTATION
            if self._has_shape_representation(element):
                return True
            
            # Methode 3: Probeer 3D-geometrie via ifcopenshell.geom
            if self._can_generate_geometry(element):
                return True
            
            return False
        
        except Exception as e:
            logger.debug(f"Fout bij geometrie-detectie voor element {element.id()}: {e}")
            return False
    
    def _has_product_definition_shape(self, element):
        """
        Controleer of element IFCPRODUCTDEFINITIONSHAPE heeft.
        """
        try:
            if hasattr(element, 'Representation'):
                if element.Representation is not None:
                    if element.Representation.is_a('IFCPRODUCTDEFINITIONSHAPE'):
                        return True
        except Exception as e:
            logger.debug(f"_has_product_definition_shape fout: {e}")
        
        return False
    
    def _has_shape_representation(self, element):
        """
        Controleer of element IFCSHAPEREPRESENTATION heeft via Representation.
        """
        try:
            if hasattr(element, 'Representation'):
                if element.Representation is not None:
                    if hasattr(element.Representation, 'Representations'):
                        representations = element.Representation.Representations
                        if representations and len(representations) > 0:
                            for rep in representations:
                                if rep.is_a('IFCSHAPEREPRESENTATION'):
                                    return True
        except Exception as e:
            logger.debug(f"_has_shape_representation fout: {e}")
        
        return False
    
    def _can_generate_geometry(self, element):
        """
        Probeer daadwerkelijk geometrie te genereren via ifcopenshell.geom.
        Dit is de minst betrouwbare methode maar most fallback.
        """
        try:
            settings = ifcopenshell.geom.settings()
            settings.set(settings.DISABLE_OPENING_SUBTRACTION, False)
            
            shape = ifcopenshell.geom.create_shape(settings, element)
            
            if shape is not None:
                # Controleer of shape daadwerkelijk inhoud heeft
                verts = shape.verts
                if verts and len(verts) > 0:
                    return True
        
        except Exception as e:
            logger.debug(f"_can_generate_geometry fout: {e}")
        
        return False