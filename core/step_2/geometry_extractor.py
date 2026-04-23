from typing import Optional, Dict, Tuple
from core.logger import setup_logger

logger = setup_logger(__name__)

class GeometryExtractor:
    """
    Extraheer geometrie-informatie:
    - Coördinaten (X, Y, Z van element origin)
    - Bounding box (min/max X, Y, Z)
    - Volume
    - Oppervlakte
    - Hoogte boven NAP
    
    Gebruikt:
    - IFCOBJECTPLACEMENT
    - IFCSHAPEREPRESENTATION
    - ifcopenshell.geom (optioneel, zware berekening)
    """
    
    def __init__(self, ifc_file):
        self.ifc_file = ifc_file
    
    def extract_geometry(self, element, element_id: int) -> Dict:
        """
        Extraheer alle geometrie data.
        
        Returns:
            Dict met coordinates, bounding_box, volume, height
        """
        try:
            geometry = {
                'coord_x': None,
                'coord_y': None,
                'coord_z': None,
                'bbox_min_x': None,
                'bbox_min_y': None,
                'bbox_min_z': None,
                'bbox_max_x': None,
                'bbox_max_y': None,
                'bbox_max_z': None,
                'volume': None,
                'surface_area': None,
                'height_above_nap': None
            }
            
            # Haal placement (coordinates)
            self._extract_placement(element, geometry)
            
            # Haal bounding box
            self._extract_bounding_box(element, geometry)
            
            # Haal volume (light calculation)
            self._extract_volume(element, geometry)
            
            # Filter None values
            geometry = {k: v for k, v in geometry.items() if v is not None}
            
            if geometry:
                logger.debug(f"Element {element_id}: Geometry opgehaald: {len(geometry)} properties")
            
            return geometry
        
        except Exception as e:
            logger.debug(f"Fout bij geometry extraction {element_id}: {e}")
            return {}
    
    def _extract_placement(self, element, geometry: Dict):
        """
        Extraheer placement (coordinates).
        """
        try:
            if not hasattr(element, 'ObjectPlacement') or not element.ObjectPlacement:
                return
            
            placement = element.ObjectPlacement
            
            # IFCLOCALPLACEMENT
            if placement.is_a('IFCLOCALPLACEMENT'):
                if hasattr(placement, 'RelativePlacement') and placement.RelativePlacement:
                    rel_placement = placement.RelativePlacement
                    
                    # Location (origin point)
                    if hasattr(rel_placement, 'Location') and rel_placement.Location:
                        coords = self._extract_coord_from_cartesian(rel_placement.Location)
                        if coords:
                            geometry['coord_x'] = coords[0]
                            geometry['coord_y'] = coords[1]
                            geometry['coord_z'] = coords[2]
        
        except Exception as e:
            logger.debug(f"Fout bij extract placement: {e}")
    
    def _extract_coord_from_cartesian(self, cartesian_point) -> Optional[Tuple[float, float, float]]:
        """
        Extract X, Y, Z van IFCCARTESIANPOINT.
        """
        try:
            if cartesian_point.is_a('IFCCARTESIANPOINT'):
                if hasattr(cartesian_point, 'Coordinates') and cartesian_point.Coordinates:
                    coords = cartesian_point.Coordinates
                    x = coords[0] if len(coords) > 0 else 0
                    y = coords[1] if len(coords) > 1 else 0
                    z = coords[2] if len(coords) > 2 else 0
                    return (float(x), float(y), float(z))
        
        except Exception as e:
            logger.debug(f"Fout bij extract coordinates: {e}")
        
        return None
    
    def _extract_bounding_box(self, element, geometry: Dict):
        """
        Extraheer bounding box van element.
        
        Deze is een eenvoudige berekening zonder ifcopenshell.geom
        voor performance.
        """
        try:
            if not hasattr(element, 'Representation') or not element.Representation:
                return
            
            min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
            max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
            
            found_any = False
            
            # Itereer door alle representaties
            for rep in element.Representation.Representations:
                if not hasattr(rep, 'Items'):
                    continue
                
                for item in rep.Items:
                    # Probeer coördinaten te extraheren
                    coords = self._get_item_coordinates(item)
                    
                    for x, y, z in coords:
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        min_z = min(min_z, z)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)
                        max_z = max(max_z, z)
                        found_any = True
            
            if found_any and min_x != float('inf'):
                geometry['bbox_min_x'] = min_x
                geometry['bbox_min_y'] = min_y
                geometry['bbox_min_z'] = min_z
                geometry['bbox_max_x'] = max_x
                geometry['bbox_max_y'] = max_y
                geometry['bbox_max_z'] = max_z
        
        except Exception as e:
            logger.debug(f"Fout bij extract bounding box: {e}")
    
    def _get_item_coordinates(self, item) -> list:
        """
        Extraheer coördinaten uit geometrie item.
        """
        coords = []
        
        try:
            if item.is_a('IFCPOLYLINE'):
                if hasattr(item, 'Points'):
                    for point in item.Points:
                        coord = self._extract_coord_from_cartesian(point)
                        if coord:
                            coords.append(coord)
            
            elif item.is_a('IFCFACETEDBREP'):
                if hasattr(item, 'OuterBoundary'):
                    shell = item.OuterBoundary
                    if hasattr(shell, 'CfsFaces'):
                        for face in shell.CfsFaces:
                            if hasattr(face, 'Bounds'):
                                for bound in face.Bounds:
                                    if hasattr(bound, 'Bound'):
                                        loop = bound.Bound
                                        if hasattr(loop, 'Polygon'):
                                            for point in loop.Polygon:
                                                coord = self._extract_coord_from_cartesian(point)
                                                if coord:
                                                    coords.append(coord)
        
        except Exception as e:
            logger.debug(f"Fout bij get item coordinates: {e}")
        
        return coords
    
    def _extract_volume(self, element, geometry: Dict):
        """
        Probeer volume te extraheren (eenvoudige methode).
        """
        try:
            # Check voor quantity sets
            if hasattr(element, 'HasPropertySets') and element.HasPropertySets:
                for prop_set in element.HasPropertySets:
                    if prop_set.is_a('IFCELEMENTQUANTITYSET'):
                        if hasattr(prop_set, 'Quantities'):
                            for qty in prop_set.Quantities:
                                if qty.is_a('IFCQUANTITYVOLUME'):
                                    if hasattr(qty, 'VolumeValue'):
                                        geometry['volume'] = float(qty.VolumeValue)
                                        return
        
        except Exception as e:
            logger.debug(f"Fout bij extract volume: {e}")