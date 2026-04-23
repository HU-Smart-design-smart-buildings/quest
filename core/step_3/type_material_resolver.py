import pandas as pd
from typing import Optional, Dict, List
from core.logger import setup_logger

logger = setup_logger(__name__)

class TypeMaterialResolver:
    """
    Resolver voor TYPE-based materialen.
    
    Wenn een element geen direct materiaal heeft, maar wel gekoppeld is aan een TYPE,
    proberen we het materiaal van het TYPE op te halen.
    
    Voorbeeld:
    - IFCWALL (element) → Geen direct materiaal
    - IFCWALL → is_defined_by → IFCWALLTYPE
    - IFCWALLTYPE → HasAssociations → IFCMATERIAL "Beton"
    
    → Result: IFCWALL krijgt materiaal "Beton" van zijn TYPE
    """
    
    def __init__(self, ifc_file):
        self.ifc_file = ifc_file
    
    def resolve_material_from_type(self, element, element_id: int) -> Optional[Dict]:
        """
        Probeer materiaal op te halen via het TYPE van het element.
        
        Args:
            element: IFC element object
            element_id: ID van het element
        
        Returns:
            Dict met materiaalgegevens OF None
        """
        try:
            # Stap 1: Vind het TYPE geassocieerd met dit element
            element_type = self._find_element_type(element)
            
            if not element_type:
                logger.debug(f"Element {element_id}: Geen TYPE gevonden")
                return None
            
            type_name = element_type.Name if hasattr(element_type, 'Name') else "Unknown"
            logger.debug(f"Element {element_id}: TYPE gevonden: {type_name}")
            
            # Stap 2: Probeer materiaal van TYPE op te halen
            material = self._extract_material_from_type(element_type)
            
            if material:
                logger.info(
                    f"Element {element_id}: Materiaal via TYPE opgehaald: {material.get('material_name')} "
                    f"(TYPE: {type_name})"
                )
                return material
            else:
                logger.debug(f"Element {element_id}: TYPE {type_name} heeft geen materiaal")
                return None
        
        except Exception as e:
            logger.debug(f"Fout bij TYPE resolver voor element {element_id}: {e}")
            return None
    
    def _find_element_type(self, element):
        """
        Vind het TYPE geassocieerd met het element.
        
        Zoekt naar:
        - IFCRELDEFINESBYTYPE relaties
        - is_a('IFCWALLTYPE') etc. via HasAssociations
        """
        try:
            # Methode 1: Via IFCRELDEFINESBYTYPE
            if hasattr(element, 'IsDefinedBy'):
                for rel in element.IsDefinedBy:
                    if rel.is_a('IFCRELDEFINESBYTYPE'):
                        if hasattr(rel, 'RelatingType'):
                            return rel.RelatingType
            
            # Methode 2: Via is_a() check op base type
            # (Sommige modellen refereren TYPE direct)
            return None
        
        except Exception as e:
            logger.debug(f"Fout bij vinden TYPE: {e}")
            return None
    
    def _extract_material_from_type(self, element_type):
        """
        Extract materiaal van een TYPE object.
        """
        try:
            if not hasattr(element_type, 'HasAssociations'):
                return None
            
            # Zoek IFCRELASSOCIATESMATERIAL relaties
            for rel in element_type.HasAssociations:
                if rel.is_a('IFCRELASSOCIATESMATERIAL'):
                    if hasattr(rel, 'RelatingMaterial'):
                        material_obj = rel.RelatingMaterial
                        
                        # Check materiaal type
                        if material_obj.is_a('IFCMATERIAL'):
                            material_name = material_obj.Name if hasattr(material_obj, 'Name') else "Unknown"
                            
                            return {
                                'material_name': material_name,
                                'material_type': 'IFCMATERIAL',
                                'source': 'TYPE',
                                'resolution_method': f'IFCRELDEFINESBYTYPE → {element_type.is_a()}'
                            }
                        
                        # LAYERSET of CONSTITUENT van TYPE
                        elif material_obj.is_a('IFCMATERIALLAYERSET'):
                            return {
                                'material_name': self._get_primary_material_from_layerset(material_obj),
                                'material_type': 'IFCMATERIALLAYERSET',
                                'source': 'TYPE',
                                'resolution_method': f'IFCRELDEFINESBYTYPE → IFCMATERIALLAYERSET'
                            }
            
            return None
        
        except Exception as e:
            logger.debug(f"Fout bij extracten TYPE materiaal: {e}")
            return None
    
    def _get_primary_material_from_layerset(self, layerset_obj) -> str:
        """
        Haal primaire (eerste/dikste) laag van layerset.
        """
        try:
            if hasattr(layerset_obj, 'MaterialLayers') and layerset_obj.MaterialLayers:
                first_layer = layerset_obj.MaterialLayers[0]
                if hasattr(first_layer, 'Material') and first_layer.Material:
                    return first_layer.Material.Name if hasattr(first_layer.Material, 'Name') else "Unknown"
        except Exception as e:
            logger.debug(f"Fout bij ophalen primair materiaal: {e}")
        
        return "Unknown"