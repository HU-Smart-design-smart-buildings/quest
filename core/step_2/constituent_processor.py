from config.config import MATERIAL_SOURCE_CONSTITUENT, DATA_QUALITY_OK
from core.logger import setup_logger

logger = setup_logger(__name__)

class ConstituentProcessor:
    """
    Verwerkt IFCMATERIALCONSTITUENTSET (samengestelde materialen).
    Elk component wordt apart opgeslagen met zijn percentage (fraction).
    """
    
    def __init__(self, ifc_file, validator, cache):
        self.ifc_file = ifc_file
        self.validator = validator
        self.cache = cache
    
    def process_constituent_set(self, element, constituent_set_obj):
        """
        Verwerk samengestelde materialen.
        
        Args:
            element: IFC element
            constituent_set_obj: IFCMATERIALCONSTITUENTSET object
        
        Returns:
            list van material dicts (één per constituent)
        """
        materials = []
        
        try:
            # Haal constituents op
            if hasattr(constituent_set_obj, 'Constituents'):
                constituents = constituent_set_obj.Constituents
                
                for constituent_obj in constituents:
                    try:
                        material_entry = self._extract_constituent_material(element, constituent_obj)
                        
                        if material_entry:
                            materials.append(material_entry)
                    
                    except Exception as e:
                        logger.debug(f"Fout bij verwerking constituent: {e}")
                        continue
            
            # FALLBACK: Als constituents zonder materiaal zijn, verdeel de overige fraction
            materials = self._apply_material_fallback(element.id(), materials)
        
        except Exception as e:
            logger.debug(f"Fout bij verwerking constituent set (element {element.id()}): {e}")
        
        return materials
    
    def _extract_constituent_material(self, element, constituent_obj):
        """
        Extract materiaal en percentage uit één constituent.
        """
        try:
            # Haal materiaal op
            material_obj = constituent_obj.Material if hasattr(constituent_obj, 'Material') else None
            material_name = material_obj.Name if material_obj and hasattr(material_obj, 'Name') and material_obj.Name else "Unknown"
            
            # Haal fraction op (0-1 range, converteer naar percentage)
            fraction = constituent_obj.Fraction if hasattr(constituent_obj, 'Fraction') else None
            constituent_fraction = float(fraction) if fraction else None
            
            material_data = {
                'element_id': element.id(),
                'element_type': element.is_a().upper() if element.is_a() else 'Unknown',  # ← FIX
                'material_name': material_name,
                'material_type': 'IFCMATERIAL',
                'layer_thickness': None,
                'layer_index': None,
                'constituent_fraction': constituent_fraction,  # 0-1 range
                'layerset_name': None,
                'data_quality_flag': DATA_QUALITY_OK,
                'source': MATERIAL_SOURCE_CONSTITUENT,
                'notes': f'Constituent with fraction {constituent_fraction}'
            }
            
            # Valideer
            material_data = self.validator.validate_material_entry(material_data)
            
            return material_data
        
        except Exception as e:
            logger.debug(f"Fout bij extractie constituent materiaal: {e}")
            return None
    
    def _apply_material_fallback(self, element_id, materials):
        """
        FALLBACK MECHANISME: Als constituents "Unknown" materiaal hebben,
        geef ze hetzelfde materiaal als andere constituents van hetzelfde element.
        
        BELANGRIJK: De totale fraction mag niet boven 1.0 uitkomen!
        De "Unknown" constituents krijgen gelijk verdeeld wat overblijft.
        
        Voorbeeld:
        Input:
        - Constituent 1: "Unknown"  fraction: None
        - Constituent 2: "Staal"    fraction: 0.70
        - Constituent 3: "Unknown"  fraction: None
        
        Berekening:
        - Totale fraction van bekende: 0.70
        - Overgebleven: 1.0 - 0.70 = 0.30
        - Aantal unknowns: 2
        - Fraction per unknown: 0.30 / 2 = 0.15
        
        Result:
        - Constituent 1: "Staal"    fraction: 0.15 (fallback)
        - Constituent 2: "Staal"    fraction: 0.70 (origineel)
        - Constituent 3: "Staal"    fraction: 0.15 (fallback)
        - TOTAAL: 0.15 + 0.70 + 0.15 = 1.0 ✓
        
        Args:
            element_id: ID van het element
            materials: list van material dicts
        
        Returns:
            lijst van material dicts met fallback toegepast
        """
        
        # Stap 1: Vind alle unieke materialen die WEL geïdentificeerd zijn (niet "Unknown")
        known_materials = [
            m for m in materials 
            if m.get('material_name') != 'Unknown'
        ]
        
        # Als er geen bekende materialen zijn, retourneer originele lijst
        if not known_materials:
            logger.warning(f"Element {element_id}: Geen bekende materialen gevonden in constituent set")
            return materials
        
        # Stap 2: Selecteer het EERSTE bekende materiaal als fallback
        fallback_material_name = known_materials[0].get('material_name')
        fallback_source = known_materials[0].get('source')
        
        # Stap 3: Bereken totale bekende fraction en aantal unknowns
        total_known_fraction = sum(
            m.get('constituent_fraction') or 0 
            for m in known_materials
        )
        
        unknown_materials = [
            m for m in materials 
            if m.get('material_name') == 'Unknown'
        ]
        
        num_unknowns = len(unknown_materials)
        
        # Stap 4: Bereken fraction per unknown
        if num_unknowns > 0:
            remaining_fraction = 1.0 - total_known_fraction
            
            # Zorg dat remaining_fraction niet negatief is
            if remaining_fraction < 0:
                logger.warning(
                    f"Element {element_id}: Totale fraction ({total_known_fraction}) > 1.0! "
                    f"Clipping naar 1.0"
                )
                remaining_fraction = 0
            
            fraction_per_unknown = remaining_fraction / num_unknowns
            
            logger.debug(
                f"Element {element_id}: Fallback berekening - "
                f"Totale bekend: {total_known_fraction:.2f}, "
                f"Overgebleven: {remaining_fraction:.2f}, "
                f"Per unknown: {fraction_per_unknown:.2f} (aantal: {num_unknowns})"
            )
        else:
            fraction_per_unknown = 0
        
        # Stap 5: Vervang alle "Unknown" materialen met fallback
        updated_materials = []
        
        for material in materials:
            if material.get('material_name') == 'Unknown':
                # Duplicate materiaal object
                updated_material = material.copy()
                
                # Vervang met fallback
                updated_material['material_name'] = fallback_material_name
                updated_material['constituent_fraction'] = round(fraction_per_unknown, 4)
                
                # Update notes om aan te geven dat dit een fallback is
                original_notes = updated_material.get('notes', '')
                updated_material['notes'] = (
                    f"{original_notes} [FALLBACK: materiaal ingevuld van ander constituent: "
                    f"{fallback_material_name}, fraction: {fraction_per_unknown:.4f}]"
                )
                
                # Flag dat dit een fallback is
                updated_material['data_quality_flag'] = "FALLBACK_APPLIED"
                
                logger.debug(
                    f"Element {element_id}: {original_notes} -> "
                    f"'{fallback_material_name}' (fraction: {fraction_per_unknown:.4f}, fallback)"
                )
                
                updated_materials.append(updated_material)
            
            else:
                # Materiaal is al bekend, behoud het
                updated_materials.append(material)
        
        # Stap 6: Validatie - controleer of totaal = 1.0
        total_fraction = sum(
            m.get('constituent_fraction') or 0 
            for m in updated_materials
        )
        
        if abs(total_fraction - 1.0) > 0.0001:  # Kleine tolerantie voor floating point
            logger.warning(
                f"Element {element_id}: Totale fraction na fallback = {total_fraction:.4f} "
                f"(verwacht: 1.0)"
            )
        
        return updated_materials