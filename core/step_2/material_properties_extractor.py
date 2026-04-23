from typing import Optional, Dict
from core.logger import setup_logger

logger = setup_logger(__name__)

class MaterialPropertiesExtractor:
    """
    Extraheer material-specifieke fysische eigenschappen:
    - Dichtheid (kg/m³)
    - Thermische geleiding (W/mK)
    - Warmtecapaciteit (J/kgK)
    - Brandwerendheid (minuten/klasse)
    - Oppervlaktebehandeling
    - Kleur (RGB)
    
    Haalt data op uit:
    - IFCMATERIAL → HasRepresentation
    - IFCMATERIALPROPERTIES
    - IFCCLASSIFICATION
    """
    
    def __init__(self):
        self.property_mapping = {
            'density': ['Density', 'Dichtheid', 'VolumetricMass'],
            'thermal_conductivity': ['ThermalConductivity', 'Thermischegeleiding', 'Lambda'],
            'heat_capacity': ['HeatCapacity', 'WarmteCapaciteit', 'SpecificHeatCapacity'],
            'fire_rating': ['FireRating', 'Brandwerendheid', 'FireResistance'],
            'color': ['Color', 'Kleur', 'RGB', 'Colour'],
            'surface_finish': ['SurfaceFinish', 'Afwerking', 'Oppervlakte']
        }
    
    def extract_material_properties(self, material_obj, material_name: str) -> Dict:
        """
        Extraheer alle material properties.
        
        Returns:
            Dict met density, thermal_conductivity, heat_capacity, etc.
        """
        try:
            properties = {
                'density': None,
                'thermal_conductivity': None,
                'heat_capacity': None,
                'fire_rating': None,
                'color': None,
                'surface_finish': None
            }
            
            if not material_obj:
                return properties
            
            # Probeer via HasRepresentation
            if hasattr(material_obj, 'HasRepresentation'):
                for rep in material_obj.HasRepresentation:
                    self._extract_from_material_representation(rep, properties)
            
            # Probeer via MaterialConstituent (voor composiet materialen)
            if hasattr(material_obj, 'Constituents'):
                for constituent in material_obj.Constituents:
                    if hasattr(constituent, 'Material'):
                        sub_properties = self.extract_material_properties(
                            constituent.Material, 
                            material_name
                        )
                        # Merge (eerste constituent wint)
                        for key in properties:
                            if properties[key] is None and key in sub_properties:
                                properties[key] = sub_properties[key]
            
            # Filter None values
            properties = {k: v for k, v in properties.items() if v is not None}
            
            if properties:
                logger.debug(f"Material '{material_name}': Properties opgehaald: {properties}")
            
            return properties
        
        except Exception as e:
            logger.debug(f"Fout bij material properties extraction: {e}")
            return {}
    
    def _extract_from_material_representation(self, representation, properties: Dict):
        """
        Extraheer properties uit material representation.
        """
        try:
            # IFCMATERIALPROPERTIES bevat fysische waarden
            if representation.is_a('IFCMATERIALPROPERTIES'):
                self._parse_material_properties_object(representation, properties)
        
        except Exception as e:
            logger.debug(f"Fout bij extract from representation: {e}")
    
    def _parse_material_properties_object(self, mat_props, properties: Dict):
        """
        Parse IFCMATERIALPROPERTIES object.
        """
        try:
            # Standaard IFC properties
            if hasattr(mat_props, 'MolecularWeight'):
                properties['molecular_weight'] = float(mat_props.MolecularWeight) \
                    if mat_props.MolecularWeight else None
            
            # Probeer via HasProperties (PropertySet-like pattern)
            if hasattr(mat_props, 'Properties'):
                for prop in mat_props.Properties:
                    if not hasattr(prop, 'Name'):
                        continue
                    
                    prop_name = prop.Name.lower()
                    prop_value = None
                    
                    if hasattr(prop, 'Value'):
                        prop_value = prop.Value
                    elif hasattr(prop, 'NominalValue'):
                        prop_value = prop.NominalValue.wrappedValue \
                            if hasattr(prop.NominalValue, 'wrappedValue') else prop.NominalValue
                    
                    # Match tegen bekende property namen
                    for key, names in self.property_mapping.items():
                        if any(name.lower() in prop_name for name in names):
                            try:
                                properties[key] = float(prop_value)
                            except (ValueError, TypeError):
                                properties[key] = str(prop_value)
                            break
        
        except Exception as e:
            logger.debug(f"Fout bij parse material properties: {e}")