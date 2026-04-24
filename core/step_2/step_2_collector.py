import pandas as pd
from pathlib import Path
from config.config import STEP_2_OUTPUT_FILE
from core.logger import setup_logger
from core.step_2.material_loader import MaterialLoader
from core.step_2.quantity_extractor import QuantityExtractor
from core.step_2.layerset_processor import LayersetProcessor

logger = setup_logger(__name__)

class Step2Collector:
    """
    STAP 2: Materiaal eigenschappen ophalen
    
    Output: DataFrame met per element (en per laag voor LAYERSET):
    - element_id, global_id, element_type, element_name
    - material_name, material_type
    - volume_m3, volume_source
    - height, length, width, layer_thickness
    - data_quality_flag
    """
    
    def __init__(self, ifc_file, elements_df: pd.DataFrame):
        self.ifc_file = ifc_file
        self.elements_df = elements_df  # Van Stap 1
        
        # Modules
        self.material_loader = MaterialLoader(ifc_file)
        self.quantity_extractor = QuantityExtractor()
        self.layerset_processor = LayersetProcessor()
        
        # Data collection
        self.material_data = []
    
    def execute(self) -> dict:
        """Voer Stap 2 uit."""
        print("\n" + "=" * 70)
        print("STAP 2: MATERIAAL EIGENSCHAPPEN OPHALEN")
        print("=" * 70 + "\n")
        
        try:
            # 2.1: Process elk element
            print("Stap 2.1: Processing elementen...")
            total_elements = len(self.elements_df)
            
            for idx, element_row in self.elements_df.iterrows():
                self._process_element(element_row)
                
                if (idx + 1) % 100 == 0:
                    print(f"  └─ {idx + 1}/{total_elements} verwerkt...")
            
            print(f"  └─ Alle {total_elements} elementen verwerkt")
            
            # 2.2: Create DataFrame
            print("Stap 2.2: Converteren naar DataFrame...")
            materials_df = self._create_dataframe()
            
            # 2.3: Reorder en clean kolommen
            print("Stap 2.3: Schonen en structureren...")
            materials_df = self._structure_columns(materials_df)
            
            # 2.4: Validatie
            print("Stap 2.4: Valideren...")
            materials_df = self._validate_dataframe(materials_df)
            
            # 2.5: Save
            print("Stap 2.5: Opslaan...")
            self._save_results(materials_df)
            
            # 2.6: Statistics
            self._print_statistics(materials_df)
            
            print("\n" + "=" * 70)
            print("✓ STAP 2 SUCCESVOL VOLTOOID")
            print("=" * 70 + "\n")
            
            return {
                'materials_df': materials_df,
                'total_rows': len(materials_df),
                'unique_elements': materials_df['element_id'].nunique(),
                'elements_with_material': len(materials_df[materials_df['material_name'] != 'Unknown']['element_id'].unique()),
                'status': 'OK'
            }
        
        except Exception as e:
            logger.error(f"Fout in Stap 2: {e}", exc_info=True)
            raise
    
    def _process_element(self, element_row):
        """Process één element uit Stap 1."""
        try:
            element_id = element_row['element_id']
            
            # Get IFC object
            ifc_element = self.ifc_file.by_id(element_id)
            
            # Get global ID
            global_id = ifc_element.GlobalId if hasattr(ifc_element, 'GlobalId') else None
            
            # Get quantities (applies to all materials from this element)
            quantities = self.quantity_extractor.extract_quantities(ifc_element)
            
            # Get materials
            materials = self.material_loader.get_materials_for_element(ifc_element)
            
            # Get layerset info
            layerset_info = self.layerset_processor.process_layerset_for_element(ifc_element)
            
            # If no materials found, add 'Unknown'
            if not materials:
                materials = [{
                    'material_name': 'Unknown',
                    'material_type': 'UNKNOWN',
                    'material_id': None,
                    'layerset_name': None,
                    'layer_index': None,
                    'layer_thickness': None,
                    'total_layerset_thickness': None,
                    'is_ventilated': None
                }]
            
            # Create row per material
            for material in materials:
                row = self._create_element_row(
                    element_row,
                    global_id,
                    material,
                    quantities,
                    layerset_info
                )
                
                self.material_data.append(row)
        
        except Exception as e:
            logger.debug(f"Error processing element {element_row.get('element_id')}: {e}")
    
    def _create_element_row(self, element_row, global_id, material, quantities, layerset_info) -> dict:
        """Create structured row voor één materiaal van element."""
        
        # Bepaal quality flags
        quality_flags = self._determine_quality_flags(quantities, material, layerset_info)
        
        # Bepaal volume source
        volume_source = 'PropertySet' if quantities['volume_m3'] is not None else None
        
        # Maak de rij met ALLE kolommen expliciet
        row = {
            # Element info
            'element_id': element_row['element_id'],
            'global_id': global_id,
            'element_type': element_row['element_type'],
            'element_name': element_row['element_name'],
            
            # Material info
            'material_name': material.get('material_name', 'Unknown'),
            'material_type': material.get('material_type', 'UNKNOWN'),
            'material_id': material.get('material_id'),
            
            # Volume en Quantities
            'volume_m3': quantities['volume_m3'],
            'volume_source': volume_source,
            'area_m2': quantities['area_m2'],
            
            # Dimensions
            'height': quantities['height'],
            'length': quantities['length'],
            'width': quantities['width'],
            
            # Layer-specific info
            'layer_index': material.get('layer_index'),
            'layer_thickness': material.get('layer_thickness'),
            'total_layerset_thickness': material.get('total_layerset_thickness'),
            'layerset_name': material.get('layerset_name'),
            'is_ventilated': material.get('is_ventilated'),
            
            # Constituent info
            'constituent_fraction': material.get('constituent_fraction'),
            'constituent_index': material.get('constituent_index'),
            'component_description': material.get('component_description'),
            
            # Profile info
            'profile_name': material.get('profile_name'),
            'profile_index': material.get('profile_index'),
            
            # Quality flag
            'data_quality_flag': quality_flags
        }
        
        return row
    
    def _determine_quality_flags(self, quantities: dict, material: dict, layerset_info: dict) -> str:
        """Bepaal data quality flags."""
        flags = []
        
        # No volume
        if quantities['volume_m3'] is None:
            flags.append('NO_VOLUME')
        
        # No dimensions
        if (quantities['height'] is None and 
            quantities['length'] is None and 
            quantities['width'] is None):
            flags.append('NO_DIMENSIONS')
        
        # Layerset but no layer thickness
        if layerset_info.get('has_layerset') and material.get('layer_thickness') is None:
            flags.append('LAYERSET_NO_THICKNESS')
        
        # Unknown material
        if material.get('material_name') == 'Unknown':
            flags.append('MATERIAL_UNKNOWN')
        
        # Return combined flag or OK
        return '|'.join(flags) if flags else 'OK'
    
    def _create_dataframe(self) -> pd.DataFrame:
        """Create DataFrame van material_data."""
        df = pd.DataFrame(self.material_data)
        print(f"  └─ {len(df)} rijen in DataFrame")
        return df
    
    def _structure_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Zorg dat kolommen in juiste volgorde staan en alle types correct zijn.
        """
        # Gewenste kolom volgorde
        desired_columns = [
            # Element identification
            'element_id',
            'global_id',
            'element_type',
            'element_name',
            
            # Material identification
            'material_name',
            'material_type',
            'material_id',
            
            # Volume & Quantities
            'volume_m3',
            'volume_source',
            'area_m2',
            
            # Dimensions
            'height',
            'length',
            'width',
            
            # Layer-specific
            'layer_index',
            'layer_thickness',
            'total_layerset_thickness',
            'layerset_name',
            'is_ventilated',
            
            # Constituent-specific
            'constituent_fraction',
            'constituent_index',
            'component_description',
            
            # Profile-specific
            'profile_name',
            'profile_index',
            
            # Quality
            'data_quality_flag'
        ]
        
        # Selecteer alleen kolommen die bestaan
        existing_columns = [col for col in desired_columns if col in df.columns]
        df = df[existing_columns]
        
        return df
    
    def _validate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valideer en clean DataFrame."""
        print(f"  Validating {len(df)} rows...")
        
        # Type conversions
        if 'element_id' in df.columns:
            df['element_id'] = pd.to_numeric(df['element_id'], errors='coerce').astype('Int64')
        
        if 'material_id' in df.columns:
            df['material_id'] = pd.to_numeric(df['material_id'], errors='coerce').astype('Int64')
        
        # Numeric columns → float
        numeric_cols = [
            'volume_m3', 
            'area_m2',
            'height', 
            'length', 
            'width', 
            'layer_thickness',
            'total_layerset_thickness',
            'constituent_fraction'
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Integer columns
        int_cols = ['layer_index', 'constituent_index', 'profile_index']
        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
        
        # Boolean columns
        if 'is_ventilated' in df.columns:
            df['is_ventilated'] = df['is_ventilated'].astype(bool)
        
        # String columns → fill NaN
        string_cols = [
            'global_id',
            'element_type',
            'element_name',
            'material_name',
            'material_type',
            'volume_source',
            'layerset_name',
            'component_description',
            'profile_name',
            'data_quality_flag'
        ]
        
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)
        
        # Fill numeric NaN with empty string for cleaner CSV
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].where(pd.notna(df[col]), '')
        
        print(f"  └─ {len(df)} rows validated")
        return df
    
    def _save_results(self, df: pd.DataFrame):
        """Save naar CSV met proper formatting."""
        try:
            Path(STEP_2_OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
            
            # Save as CSV met UTF-8 encoding
            df.to_csv(
                STEP_2_OUTPUT_FILE,
                index=False,
                encoding='utf-8',
                sep=',',
                quoting=1  # QUOTE_ALL for safety
            )
            
            print(f"  └─ Opgeslagen: {STEP_2_OUTPUT_FILE}")
            logger.info(f"Step 2 saved: {len(df)} rows to {STEP_2_OUTPUT_FILE}")
            
            # Also save as Excel for better readability
            excel_file = STEP_2_OUTPUT_FILE.with_suffix('.xlsx')
            df.to_excel(excel_file, index=False, sheet_name='Materials')
            print(f"  └─ Ook opgeslagen als: {excel_file}")
            logger.info(f"Step 2 also saved as Excel: {excel_file}")
        
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            raise
    
    def _print_statistics(self, df: pd.DataFrame):
        """Print statistieken."""
        print("\nStap 2 Statistieken:")
        print("=" * 70)
        
        print(f"Totaal rijen: {len(df):,}")
        print(f"Unieke elementen: {df['element_id'].nunique():,}")
        
        with_mat = len(df[df['material_name'] != 'Unknown']['element_id'].unique())
        without_mat = df['element_id'].nunique() - with_mat
        
        print(f"Elementen met materiaal: {with_mat:,}")
        print(f"Elementen zonder materiaal: {without_mat:,}")
        
        print(f"\nMaterialsoorten:")
        material_counts = df['material_type'].value_counts()
        for mat_type, count in material_counts.items():
            print(f"  ├─ {mat_type}: {count:,}")
        
        print(f"\nVolume coverage:")
        with_volume = df['volume_m3'].notna().sum()
        without_volume = df['volume_m3'].isna().sum()
        
        print(f"  ├─ Met volume: {with_volume:,}")
        print(f"  └─ Zonder volume: {without_volume:,}")
        
        print(f"\nDimensions coverage:")
        print(f"  ├─ Met hoogte: {df['height'].notna().sum():,}")
        print(f"  ├─ Met lengte: {df['length'].notna().sum():,}")
        print(f"  └─ Met breedte: {df['width'].notna().sum():,}")
        
        print(f"\nQuality status:")
        quality_counts = df['data_quality_flag'].value_counts()
        for flag, count in quality_counts.items():
            print(f"  ├─ {flag}: {count:,}")
        
        print("=" * 70)