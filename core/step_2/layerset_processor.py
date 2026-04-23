from config.config import MATERIAL_SOURCE_LAYERSET, DATA_QUALITY_OK
from core.logger import setup_logger

logger = setup_logger(__name__)

class LayerSetProcessor:
    """
    Verwerkt IFCMATERIALLAYERSET (gelaagde bouwmaterialen).
    Elk materiaal wordt apart opgeslagen met zijn dikte en LayerSetName.
    """
    
    def __init__(self, ifc_file, validator, cache):
        self.ifc_file = ifc_file
        self.validator = validator
        self.cache = cache
    
    def process_layerset(self, element, layerset_obj):
        """
        Verwerk gelaagde materialen.
        
        Args:
            element: IFC element
            layerset_obj: IFCMATERIALLAYERSET object
        
        Returns:
            list van material dicts (één per laag)
        """
        materials = []
        
        try:
            layerset_name = layerset_obj.LayerSetName if hasattr(layerset_obj, 'LayerSetName') and layerset_obj.LayerSetName else "Unknown"
            
            # Haal totale dikte van de layerset op (als beschikbaar)
            total_thickness = None
            if hasattr(layerset_obj, 'TotalThickness'):
                total_thickness = float(layerset_obj.TotalThickness) if layerset_obj.TotalThickness else None
            
            # Haal lagen op
            if hasattr(layerset_obj, 'MaterialLayers'):
                layers = layerset_obj.MaterialLayers
                
                for layer_index, layer_obj in enumerate(layers, start=1):
                    try:
                        material_entry = self._extract_layer_material(
                            element, 
                            layer_obj, 
                            layer_index, 
                            layerset_name
                        )
                        
                        if material_entry:
                            materials.append(material_entry)
                    
                    except Exception as e:
                        logger.debug(f"Fout bij verwerking layer {layer_index}: {e}")
                        continue
            
            # FALLBACK: Als layers zonder materiaal zijn en totale dikte beschikbaar is,
            # verdeel dan de ontbrekende dikte
            if total_thickness is not None:
                materials = self._apply_material_fallback(
                    element.id(), 
                    materials, 
                    layerset_name,
                    total_thickness
                )
            else:
                logger.debug(
                    f"Element {element.id()}, LayerSet '{layerset_name}': "
                    f"Geen TotalThickness beschikbaar - fallback niet toegepast"
                )
        
        except Exception as e:
            logger.debug(f"Fout bij verwerking layerset (element {element.id()}): {e}")
        
        return materials
    
    def _extract_layer_material(self, element, layer_obj, layer_index, layerset_name):
        """
        Extract materiaal en dikte uit één laag.
        """
        try:
            # Haal materiaal op
            material_obj = layer_obj.Material if hasattr(layer_obj, 'Material') else None
            material_name = material_obj.Name if material_obj and hasattr(material_obj, 'Name') and material_obj.Name else "Unknown"
            
            # Haal dikte op (in meters)
            layer_thickness = layer_obj.LayerThickness if hasattr(layer_obj, 'LayerThickness') else None
            
            material_data = {
                'element_id': element.id(),
                'element_type': element.is_a().upper() if element.is_a() else 'Unknown',
                'material_name': material_name,
                'material_type': 'IFCMATERIAL',
                'layer_thickness': float(layer_thickness) if layer_thickness else None,
                'layer_index': layer_index,
                'constituent_fraction': None,
                'layerset_name': layerset_name,
                'data_quality_flag': DATA_QUALITY_OK,
                'source': MATERIAL_SOURCE_LAYERSET,
                'notes': f'Layer {layer_index} from IFCMATERIALLAYERSET'
            }
            
            # Valideer
            material_data = self.validator.validate_material_entry(material_data)
            
            return material_data
        
        except Exception as e:
            logger.debug(f"Fout bij extractie laag materiaal: {e}")
            return None
    
    def _apply_material_fallback(self, element_id, materials, layerset_name, total_thickness):
        """
        FALLBACK MECHANISME: Als layers "Unknown" materiaal hebben EN
        de totale dikte van de layerset beschikbaar is,
        geef de unknown layers hetzelfde materiaal als andere layers.
        
        De ontbrekende dikte wordt gelijk verdeeld over de unknown layers.
        
        BELANGRIJK: 
        - Fallback wordt ALLEEN toegepast als TotalThickness bekend is!
        - Als TotalThickness None is, worden unknown diktens niet aangevuld!
        
        Voorbeeld:
        Input (met TotalThickness = 0.60m):
        - Layer 1: "Unknown"  thickness: None
        - Layer 2: "Beton"    thickness: 0.30m
        - Layer 3: "Unknown"  thickness: None
        - TotalThickness: 0.60m
        
        Berekening:
        ├─ Totale bekende dikte: 0.30m
        ├─ Ontbrekende dikte: 0.60 - 0.30 = 0.30m
        ├─ Aantal unknowns: 2
        └─ Per unknown layer: 0.30 ÷ 2 = 0.15m
        
        Result:
        - Layer 1: "Beton"    thickness: 0.15m (fallback)
        - Layer 2: "Beton"    thickness: 0.30m (origineel)
        - Layer 3: "Beton"    thickness: 0.15m (fallback)
        - TOTAAL: 0.60m ✓
        
        Args:
            element_id: ID van het element
            materials: list van material dicts
            layerset_name: naam van de layerset
            total_thickness: totale dikte van de layerset (in meters)
        
        Returns:
            lijst van material dicts met fallback toegepast
        """
        
        # Stap 1: Vind alle lagen die WEL een materiaal hebben (niet "Unknown")
        known_materials = [
            m for m in materials 
            if m.get('material_name') != 'Unknown'
        ]
        
        # Als er geen bekende materialen zijn, retourneer originele lijst
        if not known_materials:
            logger.warning(
                f"Element {element_id}, LayerSet '{layerset_name}': "
                f"Geen bekende materialen gevonden"
            )
            return materials
        
        # Stap 2: Selecteer het EERSTE bekende materiaal als fallback
        fallback_material_name = known_materials[0].get('material_name')
        fallback_source = known_materials[0].get('source')
        
        # Stap 3: Bereken totale bekende dikte
        total_known_thickness = sum(
            m.get('layer_thickness') or 0 
            for m in known_materials
        )
        
        unknown_materials = [
            m for m in materials 
            if m.get('material_name') == 'Unknown'
        ]
        
        num_unknowns = len(unknown_materials)
        
        # Stap 4: Controleer of ontbrekende dikte beschikbaar is
        missing_thickness = total_thickness - total_known_thickness
        
        # Als missing_thickness negatief is, waarschuw
        if missing_thickness < 0:
            logger.warning(
                f"Element {element_id}, LayerSet '{layerset_name}': "
                f"Totale bekende dikte ({total_known_thickness:.4f}m) > "
                f"TotalThickness ({total_thickness:.4f}m)! "
                f"Fallback niet toegepast."
            )
            return materials
        
        # Stap 5: Bereken dikte per unknown layer
        if num_unknowns > 0:
            thickness_per_unknown = missing_thickness / num_unknowns
            
            logger.debug(
                f"Element {element_id}, LayerSet '{layerset_name}': "
                f"Fallback berekening - "
                f"TotalThickness: {total_thickness:.4f}m, "
                f"Totale bekende dikte: {total_known_thickness:.4f}m, "
                f"Ontbrekende dikte: {missing_thickness:.4f}m, "
                f"Per unknown layer: {thickness_per_unknown:.4f}m (aantal: {num_unknowns})"
            )
        else:
            thickness_per_unknown = 0
        
        # Stap 6: Vervang alle "Unknown" materialen met fallback
        updated_materials = []
        
        for material in materials:
            if material.get('material_name') == 'Unknown':
                # Duplicate materiaal object
                updated_material = material.copy()
                
                # Vervang met fallback
                updated_material['material_name'] = fallback_material_name
                updated_material['layer_thickness'] = round(thickness_per_unknown, 4)
                
                # Update notes om aan te geven dat dit een fallback is
                original_notes = updated_material.get('notes', '')
                updated_material['notes'] = (
                    f"{original_notes} [FALLBACK: materiaal ingevuld van andere layer: "
                    f"{fallback_material_name}, thickness: {thickness_per_unknown:.4f}m]"
                )
                
                # Flag dat dit een fallback is
                updated_material['data_quality_flag'] = "FALLBACK_APPLIED"
                
                logger.debug(
                    f"Element {element_id}: {original_notes} -> "
                    f"'{fallback_material_name}' (thickness: {thickness_per_unknown:.4f}m, fallback)"
                )
                
                updated_materials.append(updated_material)
            
            else:
                # Materiaal is al bekend, behoud het
                updated_materials.append(material)
        
        # Stap 7: Validatie - controleer totale dikte
        total_thickness_after = sum(
            m.get('layer_thickness') or 0 
            for m in updated_materials
        )
        
        if abs(total_thickness_after - total_thickness) > 0.0001:  # Tolerantie voor floating point
            logger.warning(
                f"Element {element_id}, LayerSet '{layerset_name}': "
                f"Totale dikte na fallback ({total_thickness_after:.4f}m) ≠ "
                f"TotalThickness ({total_thickness:.4f}m)"
            )
        else:
            logger.debug(
                f"Element {element_id}, LayerSet '{layerset_name}': "
                f"Validatie OK - Totale dikte = {total_thickness_after:.4f}m"
            )
        
        return updated_materials