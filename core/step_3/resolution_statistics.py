import pandas as pd
from typing import Dict
from core.logger import setup_logger

logger = setup_logger(__name__)

class ResolutionStatistics:
    """
    Tracking van materiaal resolutie statistieken.
    """
    
    def __init__(self):
        self.statistics = {
            'total_elements_processed': 0,
            'elements_with_unknown_material': 0,
            'successfully_resolved': 0,
            'still_unknown': 0,
            'resolution_methods': {}
        }
    
    def add_resolved_material(self, resolution_method: str):
        """Registreer een opgelost materiaal."""
        self.statistics['successfully_resolved'] += 1
        self.statistics['resolution_methods'][resolution_method] = \
            self.statistics['resolution_methods'].get(resolution_method, 0) + 1
    
    def add_unresolved(self):
        """Registreer onopgelost materiaal."""
        self.statistics['still_unknown'] += 1
    
    def print_report(self, merged_df: pd.DataFrame):
        """
        Print detailrapport van resolutie.
        """
        print("\nStap 3.5 Resolutie Statistieken")
        print("=" * 60)
        
        total_unknown_before = (merged_df['material_name'] == 'Unknown').sum()
        
        print(f"\nAlgemeen:")
        print(f"  ├─ Totaal 'Unknown' materialen voor Stap 3: {total_unknown_before}")
        print(f"  ├─ Succesvol opgelost: {self.statistics['successfully_resolved']}")
        print(f"  ├─ Nog steeds Unknown: {self.statistics['still_unknown']}")
        print(f"  └─ Success rate: {(self.statistics['successfully_resolved'] / (total_unknown_before or 1) * 100):.1f}%")
        
        if self.statistics['resolution_methods']:
            print(f"\nMethoden gebruikt:")
            for method, count in self.statistics['resolution_methods'].items():
                print(f"  ├─ {method}: {count}")
        
        print("=" * 60)
    
    def get_dict(self) -> Dict:
        """Retourneer statistics dict."""
        return self.statistics