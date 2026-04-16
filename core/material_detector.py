import ifcopenshell
from core.logger import setup_logger

logger = setup_logger(__name__)

class MaterialDetector:
    """
    Detecteert of een element materiaalinformatie heeft gekoppeld.
    TRUE = minstens één type materiaal is gekoppeld (IFCMATERIAL, IFCMATERIALLAYERSET, IFCMATERIALCONSTITUENTSET)
    """
    
    def __init__(self, ifc_file):
        self.ifc_file = ifc_file
    
    def has_material_info(self, element):
        """
        Controleer of een element materiaalinformatie heeft.
        
        Args:
            element: IFC-element object
        
        Returns:
            bool: True als minstens één materiaal gekoppeld is
        """
        try:
            # Methode 1: Controleer IFCMATERIAL rechtstreeks
            if self._has_ifcmaterial(element):
                return True
            
            # Methode 2: Controleer IFCMATERIALLAYERSET
            if self._has_material_layer_set(element):
                return True
            
            # Methode 3: Controleer IFCMATERIALCONSTITUENTSET
            if self._has_material_constituent_set(element):
                return True
            
            # Methode 4: Controleer via IFCRELASSOCIATESMATERIAL relatie
            if self._has_material_via_relation(element):
                return True
            
            return False
        
        except Exception as e:
            logger.debug(f"Fout bij materiaaldetectie voor element {element.id()}: {e}")
            return False
    
    def _has_ifcmaterial(self, element):
        """
        Controleer of element directe IFCMATERIAL gekoppeld heeft.
        """
        try:
            # Haal alle materialen op via HasAssociations
            if hasattr(element, 'HasAssociations'):
                for rel in element.HasAssociations:
                    if rel.is_a('IFCRELASSOCIATESMATERIAL'):
                        if hasattr(rel, 'RelatingMaterial'):
                            material = rel.RelatingMaterial
                            if material.is_a('IFCMATERIAL'):
                                return True
        except Exception as e:
            logger.debug(f"_has_ifcmaterial fout: {e}")
        
        return False
    
    def _has_material_layer_set(self, element):
        """
        Controleer of element IFCMATERIALLAYERSET gekoppeld heeft.
        Dit is typisch voor composiet-elementen zoals wanden, vloeren.
        """
        try:
            if hasattr(element, 'HasAssociations'):
                for rel in element.HasAssociations:
                    if rel.is_a('IFCRELASSOCIATESMATERIAL'):
                        if hasattr(rel, 'RelatingMaterial'):
                            material = rel.RelatingMaterial
                            if material.is_a('IFCMATERIALLAYERSET'):
                                return True
        except Exception as e:
            logger.debug(f"_has_material_layer_set fout: {e}")
        
        return False
    
    def _has_material_constituent_set(self, element):
        """
        Controleer of element IFCMATERIALCONSTITUENTSET gekoppeld heeft.
        Dit is typisch voor niet-homogene materialen.
        """
        try:
            if hasattr(element, 'HasAssociations'):
                for rel in element.HasAssociations:
                    if rel.is_a('IFCRELASSOCIATESMATERIAL'):
                        if hasattr(rel, 'RelatingMaterial'):
                            material = rel.RelatingMaterial
                            if material.is_a('IFCMATERIALCONSTITUENTSET'):
                                return True
        except Exception as e:
            logger.debug(f"_has_material_constituent_set fout: {e}")
        
        return False
    
    def _has_material_via_relation(self, element):
        """
        Controleer via IFCRELASSOCIATESMATERIAL relatie naar TYPE of ELEMENT.
        """
        try:
            # Controleer relaties
            if hasattr(element, 'HasAssociations'):
                for rel in element.HasAssociations:
                    if rel.is_a('IFCRELASSOCIATESMATERIAL'):
                        return True
        except Exception as e:
            logger.debug(f"_has_material_via_relation fout: {e}")
        
        return False