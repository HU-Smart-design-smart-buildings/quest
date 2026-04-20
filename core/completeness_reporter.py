import json
from pathlib import Path
from core.logger import setup_logger

logger = setup_logger(__name__)

class CompletenessReporter:
    """
    Genereert rapportage over volledigheid van materiaaldata per element-type.
    """
    
    def __init__(self, elements_df, output_file):
        self.elements_df = elements_df
        self.output_file = output_file
        self.report = {}
    
    def generate_report(self):
        """
        Genereer volledigheidsrapport per element-type.
        
        Returns:
            dict met rapport
        """
        print("Genereer volledigheidsrapport...")
        
        # Calculate global statistics
        self.report['global'] = self._calculate_global_stats()
        
        # Per element-type
        self.report['per_type'] = {}
        
        for element_type in self.elements_df['element_type'].unique():
            self.report['per_type'][element_type] = self._calculate_type_stats(element_type)
        
        # Save rapport
        self._save_report()
        
        print("[OK] Volledigheidsrapport gegenereerd")
        
        return self.report
    
    def _calculate_global_stats(self):
        """
        Bereken globale statistieken.
        """
        total = len(self.elements_df)
        with_material = len(self.elements_df[self.elements_df['has_material_info'] == True])
        without_material = total - with_material
        percentage_with = (with_material / total * 100) if total > 0 else 0
        percentage_without = (without_material / total * 100) if total > 0 else 0
        
        return {
            'total_elements': total,
            'elements_with_material': with_material,
            'elements_without_material': without_material,
            'percentage_with_material': round(percentage_with, 2),
            'percentage_without_material': round(percentage_without, 2)
        }
    
    def _calculate_type_stats(self, element_type):
        """
        Bereken statistieken per element-type.
        """
        type_df = self.elements_df[self.elements_df['element_type'] == element_type]
        
        total = len(type_df)
        with_material = len(type_df[type_df['has_material_info'] == True])
        without_material = total - with_material
        percentage_with = (with_material / total * 100) if total > 0 else 0
        percentage_without = (without_material / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'with_material': with_material,
            'without_material': without_material,
            'percentage_with_material': round(percentage_with, 2),
            'percentage_without_material': round(percentage_without, 2)
        }
    
    def _save_report(self):
        """
        Sla rapport op als JSON-bestand.
        """
        try:
            Path(self.output_file).parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.report, f, indent=4, ensure_ascii=False)
            
            print(f"Rapport opgeslagen: {self.output_file}")
        
        except Exception as e:
            logger.error(f"Fout bij opslaan rapport: {e}")
    
    def print_report(self):
        """
        Print rapport in leesbaar formaat naar console.
        """
        print("=" * 60)
        print("VOLLEDIGHEIDSRAPPORT - GLOBAAL")
        print("=" * 60)
        
        global_stats = self.report.get('global', {})
        print(f"Totaal elementen: {global_stats.get('total_elements', 0)}")
        print(f"  - Met materiaalinfo: {global_stats.get('elements_with_material', 0)} ({global_stats.get('percentage_with_material', 0)}%)")
        print(f"  - Zonder materiaalinfo: {global_stats.get('elements_without_material', 0)} ({global_stats.get('percentage_without_material', 0)}%)")
        
        print("\n" + "=" * 60)
        print("VOLLEDIGHEIDSRAPPORT - PER ELEMENT-TYPE")
        print("=" * 60)
        
        for element_type, stats in self.report.get('per_type', {}).items():
            print(f"\n{element_type}:")
            print(f"  - Totaal: {stats.get('total', 0)}")
            print(f"  - Met materiaal: {stats.get('with_material', 0)} ({stats.get('percentage_with_material', 0)}%)")
            print(f"  - Zonder materiaal: {stats.get('without_material', 0)} ({stats.get('percentage_without_material', 0)}%)")