import pandas as pd
from pathlib import Path
from config.config import STEP_2_EXCEL_FILE, STEP_3_EXCEL_FILE, OUTPUT_DIR
from core.logger import setup_logger
from core.step_3.type_material_resolver import TypeMaterialResolver
from core.step_3.property_set_resolver import PropertySetResolver
from core.step_3.style_material_resolver import StyleMaterialResolver
from core.step_3.fallback_strategy_manager import FallbackStrategyManager
from core.step_3.resolution_statistics import ResolutionStatistics

logger = setup_logger(__name__)

class Step3MaterialTypeResolver:
    """
    STAP 3: Materiaaltype Verwerken
    
    Voert fallback-strategieën uit voor elementen met 'Unknown' materiaal:
    1. TYPE-based materialen (IFCWALLTYPE, etc.)
    2. PropertySet materialen (IFCPROPERTYSET)
    3. Style-based materialen (IFCSTYLEDITEM)
    
    Alle onopgeloste materialen blijven 'Unknown' (geen standaardwaarden).
    """
    
    def __init__(self, ifc_file, step_2_results: dict):
        self.ifc_file = ifc_file
        self.step_2_results = step_2_results
        self.materials_df = step_2_results['materials_df']
        
        # Resolvers
        self.type_resolver = TypeMaterialResolver(ifc_file)
        self.property_set_resolver = PropertySetResolver()
        self.style_resolver = StyleMaterialResolver()
        
        # Manager
        self.fallback_manager = FallbackStrategyManager(
            self.type_resolver,
            self.property_set_resolver,
            self.style_resolver
        )
        
        # Statistics
        self.statistics = ResolutionStatistics()
    
    def execute(self) -> dict:
        """
        Voer Stap 3 volledig uit.
        """
        print("\n" + "=" * 60)
        print("STAP 3: MATERIAALTYPE VERWERKEN (FALLBACK RESOLUTION)")
        print("=" * 60 + "\n")
        
        try:
            # 3.1: Load materialen van Stap 2
            print("Stap 3.1: Laden Stap 2 output...")
            self._load_step2_materials()
            
            # 3.2: Identify 'Unknown' elementen
            print("Stap 3.2: Identificeren 'Unknown' materialen...")
            unknown_count = self._count_unknowns()
            
            # 3.3: Apply fallback strategies
            print("Stap 3.3: Toepassen fallback-strategieën...")
            self._apply_fallback_strategies()
            
            # 3.4: Update DataFrame
            print("Stap 3.4: Update materiaaldataset...")
            self._update_materials_dataframe()
            
            # 3.5: Export naar Excel
            print("Stap 3.5: Exporteren naar Excel...")
            self._export_to_excel()
            
            # 3.6: Print statistieken
            self._print_statistics()
            
            print("\n" + "=" * 60)
            print("✓ STAP 3 SUCCESVOL VOLTOOID")
            print("=" * 60 + "\n")
            
            return self._get_results()
        
        except Exception as e:
            logger.error(f"Fout in Stap 3: {e}")
            raise
    
    def _load_step2_materials(self):
        """Laad materialen van Stap 2."""
        logger.info(f"Materialen geladen: {len(self.materials_df)} rijen")
    
    def _count_unknowns(self) -> int:
        """Tel 'Unknown' materialen."""
        unknown_count = (self.materials_df['material_name'] == 'Unknown').sum()
        print(f"  └─ {unknown_count} elementen met 'Unknown' materiaal")
        return unknown_count
    
    def _apply_fallback_strategies(self):
        """
        Pas fallback-strategieën toe op alle Unknown materialen.
        """
        unknown_indices = self.materials_df[self.materials_df['material_name'] == 'Unknown'].index
        total_unknown = len(unknown_indices)
        
        processed = 0
        
        for idx, row in self.materials_df.loc[unknown_indices].iterrows():
            try:
                element_id = row['element_id']
                
                # Haal IFC element op
                ifc_element = self.ifc_file.by_id(element_id)
                
                # Probeer via fallback-strategieën
                resolution = self.fallback_manager.resolve_material(
                    ifc_element,
                    element_id,
                    row['material_name']
                )
                
                # Als succesvol: Update de row
                if resolution:
                    self.materials_df.at[idx, 'material_name'] = resolution['material_name']
                    self.materials_df.at[idx, 'resolution_method'] = resolution['resolution_method']
                    self.materials_df.at[idx, 'data_quality_flag'] = 'FALLBACK_RESOLVED'
                    self.statistics.add_resolved_material(resolution['source'])
                else:
                    self.statistics.add_unresolved()
                
                processed += 1
                if processed % 100 == 0:
                    print(f"  └─ {processed}/{total_unknown} verwerkt...")
            
            except Exception as e:
                logger.debug(f"Fout bij element {row.get('element_id')}: {e}")
                self.statistics.add_unresolved()
        
        print(f"  └─ Totaal verwerkt: {processed}/{total_unknown}")
    
    def _update_materials_dataframe(self):
        """Update DataFrame met nieuwe kolommen."""
        if 'resolution_method' not in self.materials_df.columns:
            self.materials_df['resolution_method'] = None
        
        logger.info(f"DataFrame bijgewerkt met resolution info")
    
    def _export_to_excel(self):
        """Exporteer naar Excel."""
        try:
            Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
            
            # Maak Excel met multiple sheets
            with pd.ExcelWriter(STEP_3_EXCEL_FILE, engine='openpyxl') as writer:
                
                # Sheet 1: Volledige dataset
                self.materials_df.to_excel(writer, sheet_name='MATERIALS', index=False)
                
                # Sheet 2: Summary
                summary_data = {
                    'Metriek': [
                        'Totaal materiaalkoppelingen',
                        'Via fallback opgelost (TYPE)',
                        'Via fallback opgelost (PROPERTYSET)',
                        'Via fallback opgelost (STYLE)',
                        'Nog steeds Unknown'
                    ],
                    'Aantal': [
                        len(self.materials_df),
                        self.fallback_manager.resolution_count['TYPE'],
                        self.fallback_manager.resolution_count['PROPERTYSETS'],
                        self.fallback_manager.resolution_count['STYLE'],
                        self.fallback_manager.resolution_count['UNRESOLVED']
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='SUMMARY', index=False)
            
            logger.info(f"Excel geëxporteerd: {STEP_3_EXCEL_FILE}")
            print(f"✓ Excel opgeslagen: {STEP_3_EXCEL_FILE}")
        
        except Exception as e:
            logger.error(f"Fout bij export: {e}")
    
    def _print_statistics(self):
        """Print statistieken."""
        self.statistics.print_report(self.materials_df)
        
        # Extra info
        unknown_after = (self.materials_df['material_name'] == 'Unknown').sum()
        print(f"\nReductie Unknown materialen:")
        print(f"  ├─ Voor Stap 3: {self._count_unknowns()}")
        print(f"  └─ Na Stap 3: {unknown_after}")
    
    def _get_results(self) -> dict:
        """Retourneer Stap 3 resultaten."""
        return {
            'materials_df': self.materials_df,
            'total_resolved': self.fallback_manager.resolution_count['TYPE'] + \
                             self.fallback_manager.resolution_count['PROPERTYSETS'] + \
                             self.fallback_manager.resolution_count['STYLE'],
            'still_unknown': self.fallback_manager.resolution_count['UNRESOLVED'],
            'excel_output': STEP_3_EXCEL_FILE,
            'statistics': self.statistics.get_dict(),
            'status': 'OK'
        }