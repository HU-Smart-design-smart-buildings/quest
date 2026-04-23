# QUEST - BIM Materiaalprofiler
## Volledige Projectdocumentatie

---

## 📋 Inhoudsopgave

1. [Projectoverzicht](#projectoverzicht)
2. [Systeemarchitectuur](#systeemarchitectuur)
3. [Stap-voor-stap Implementatie](#stap-voor-stap-implementatie)
4. [Troubleshooting](#troubleshooting)
5. [Performance Optimalisatie](#performance-optimalisatie)
6. [FAQ](#faq)

---

## 🎯 Projectoverzicht

**Naam:** QUEST - BIM Materiaalprofiler  
**Doel:** Automatisch bouwmaterialen extraheren uit IFC-bestanden (versies 2.3 tot 4.3)  
**Taal:** Python 3.x  
**Frameworks:** ifcopenshell, pandas, openpyxl

### Aannames & Principes

- **IFC-versie agnostic:** Werkt met IFC 2.3, 4.0, 4.1, 4.3
- **Multi-source materialen:** Haalt materialen op uit:
  - Directe koppelingen (IFCRELASSOCIATESMATERIAL)
  - Gelaagde systemen (IFCMATERIALLAYERSET)
  - Samengestelde materialen (IFCMATERIALCONSTITUENTSET)
  - Component-materialen (deur/raam onderdelen)
  - Type-based materialen (fallback)
  - PropertySet materialen (fallback)
  - Style-based materialen (fallback)

- **Performance-gefocust:** Multi-threading, batching, caching
- **Geen hardcoded defaults:** Onbekende materialen krijgen geen standaardwaarden

---

## 🏗️ Systeemarchitectuur

### Mappenstructuur

```
quest/
├── core/
│   ├── step_0/
│   │   ├── ifc_loader.py               # IFC-bestand laden
│   │   ├── version_detector.py         # Versie detecteren
│   │   └── version_strategies.py       # Versiespecifieke logica
│   │
│   ├── step_1/
│   │   ├── element_extractor.py        # Bouwkundige elementen ophalen
│   │   ├── element_validator.py        # Element filtering
│   │   └── step_1_element_collector.py # Orchestrator
│   │
│   ├── step_2/
│   │   ├── material_linker.py          # Direct materialen
│   │   ├── layerset_processor.py       # Gelaagde materialen
│   │   ├── constituent_processor.py    # Samengestelde materialen
│   │   ├── component_properties.py     # Component-materialen
│   │   ├── material_validator.py       # Validatie
│   │   ├── material_linker_cache.py    # Caching
│   │   ├── performance_optimizer.py    # Multi-threading
│   │   ├── data_joiner.py              # Stap 1 + 2 join
│   │   ├── excel_exporter.py           # Excel output
│   │   └── step_2_material_collector.py # Orchestrator
│   │
│   ├── step_3/
│   │   ├── type_material_resolver.py   # TYPE-based fallback
│   │   ├── property_set_resolver.py    # PropertySet fallback
│   │   ├── style_material_resolver.py  # Style-based fallback
│   │   ├── fallback_strategy_manager.py # Prioriteit management
│   │   ├── resolution_statistics.py    # Statistieken
│   │   └── step_3_material_type_resolver.py # Orchestrator
│   │
│   └── logger.py                       # Logging setup
│
├── config/
│   └── config.py                       # Globale configuratie
│
├── output/
│   ├── step_1_elements.xlsx            # Stap 1 output
│   ├── step_2_materials.xlsx           # Stap 2 output (multi-sheet)
│   ├── step_2_materials.pkl            # Stap 2 output (pickle)
│   ├── step_3_materials_resolved.xlsx  # Stap 3 output
│   └── logs/
│       └── quest_main.log              # Applicatie logs
│
├── main.py                             # Entry point
└── DOCUMENTATION.md                    # Deze file
```

---

## 🔄 Stap-voor-stap Implementatie

### STAP 0: IFC-Bestand Inladen en Versie Detecteren

**Doel:** IFC-bestand valideren en versie bepalen

**Onderdelen:**
- `ifc_loader.py` → Laad IFC-bestand via ifcopenshell
- `version_detector.py` → Detecteer IFC-versie (2.3, 4.0, 4.1, 4.3)
- `version_strategies.py` → Selecteer versiespecifieke strategie

**Input:** IFC-bestandspad  
**Output:**
```python
{
    "ifc_file": <ifcopenshell object>,
    "ifc_version": "IFC 4.3",
    "ifc_version_enum": IFCVersion.IFC_4_3,
    "building_elements": {'IFCWALL', 'IFCDOOR', 'IFCBEAM', ...},
    "status": "OK"
}
```

**Key Points:**
- IFC 2.3 uses PascalCase (IfcWall) → genormaliseerd naar UPPERCASE
- IFC 4.x uses UPPERCASE (IFCWALL)
- Versie bepaalt welke entiteiten beschikbaar zijn

---

### STAP 1: Bouwkundige Elementen Verzamelen

**Doel:** Alle bouwkundige elementen uit IFC extraheren met metadata

**Proces:**
1. Filtreer op element_types uit versie-strategie
2. Haal metadata op (ID, naam, type, material_info, geometry)
3. Bepaal parent-relaties
4. Output naar Excel + pickle

**Input:** IFC-bestand (van Stap 0)  
**Output:**
```
DataFrame met kolommen:
- element_id
- element_type (IFCWALL, IFCDOOR, etc.)
- element_name
- type_link
- type_naam
- has_material_info (True/False)
- geometric_representation (True/False)
- parent_element_id
```

**Excel Sheets:**
- Sheet 1: Alle elementen
- Sheet 2: Elementen met materiaal
- Sheet 3: Elementen zonder materiaal
- Sheet 4: SUMMARY

**Key Points:**
- `has_material_info` = Element heeft mogelijk gekoppelde materialen
- `geometric_representation` = Element heeft geometrie (voor volume berekening)
- Parent-relaties voor hierarchie

---

### STAP 2: Materiaalkoppelingen Ophalen

**Doel:** Extraheer alle materiaalkoppelingen per element

**Proces:**
1. Filter elementen van Stap 1 (skip zonder material_info EN geometry)
2. Extract 4 soorten materialen:
   - DIRECT: Via IFCRELASSOCIATESMATERIAL
   - LAYERSET: Via IFCMATERIALLAYERSET (+ dikte berekening)
   - CONSTITUENT: Via IFCMATERIALCONSTITUENTSET (+ fractie berekening)
   - COMPONENT: Via deur/raam onderdelen

3. Join Stap 1 elementen met Stap 2 materialen
4. Elementen zonder materiaal krijgen `material_name = 'Unknown'`
5. Multi-threaded verwerking (4 workers)
6. Output per element_type in aparte Excel sheets

**Input:** 
- IFC-bestand
- elements_df van Stap 1

**Output:** Per element_type aparte Excel sheet
```
Columns:
- (alle kolommen van Stap 1)
- material_name
- material_type (IFCMATERIAL, IFCMATERIALLAYERSET, etc.)
- layer_thickness (alleen voor layers)
- layer_index (laag nummer)
- constituent_fraction (0-1 range)
- layerset_name (naam layerset indien van toepassing)
- data_quality_flag (OK, MISSING, FALLBACK_APPLIED)
- source (DIRECT, LAYERSET, CONSTITUENT, COMPONENT)
- notes
- resolution_method (hoe het materiaal gevonden is)
```

**Sheets:**
- Per element_type (WALL, BEAM, DOOR, etc.)
- SUMMARY (statistieken)

**Key Points:**
- Multi-threading: 4 workers, batch_size=500
- Performance: Geen duplicaat IFC lookups
- Unknown handling: Elementen zonder materiaal krijgen rij met 'Unknown'
- Dikte-verdeling: Fallback voor onbekende laagdiktens

---

### STAP 3: Materiaaltype Verwerken (Fallback Resolution)

**Doel:** Probeer 'Unknown' materialen op te lossen via fallback-strategieën

**Fallback-strategieën (in prioriteit):**

1. **TYPE-based** (prioriteit 1)
   - Element → IsDefinedBy → IFCWALLTYPE → HasAssociations → Material
   - Bijv: IFCWALL zonder materiaal krijgt materiaal van IFCWALLTYPE

2. **PropertySet-based** (prioriteit 2)
   - Element → HasPropertySets → IFCPROPERTYSET → MaterialName eigenschap
   - Zoekt naar: MaterialName, Material, MaterialCategory, etc.

3. **Style-based** (prioriteit 3)
   - Element → StyledByItem → IFCSTYLEDITEM → IFCSURFACESTYLE
   - Map style-kenmerken naar materiaalnamen

**Proces:**
1. Identificeer alle elementen met `material_name = 'Unknown'`
2. Per element, probeer in volgorde: TYPE → PropertySet → Style
3. Update DataFrame met gevonden material
4. Flag als 'FALLBACK_RESOLVED'
5. Log welke methode gebruikt is

**Input:** step_2_materials.xlsx (met veel 'Unknown')  
**Output:** step_3_materials_resolved.xlsx (veel minder 'Unknown')

**Sheets:**
- MATERIALS (volledige dataset met resoluties)
- SUMMARY (statistieken)

**Statistieken:**
```
- Totaal Unknown voor Stap 3
- Via TYPE opgelost
- Via PropertySet opgelost
- Via Style opgelost
- Nog steeds Unknown
- Success rate (%)
```

**Key Points:**
- Geen hardcoded defaults voor nog-steeds-Unknown
- Logging welke methode per element werkte
- Statistics tracking per resolution method

---

## 🐛 Troubleshooting

### Issue 1: IFCWALL zichtbaar in Stap 1 maar niet in Stap 2

**Oorzaak:** Element_type niet correct genormaliseerd naar uppercase

**Oplossing:**
```python
# In alle *_processor.py files:
'element_type': element.is_a().upper() if element.is_a() else 'Unknown'
```

**Check:**
```bash
# In step_2_material_collector.py
logger.info(f"Unieke element types: {df['element_type'].unique().tolist()}")
```

---

### Issue 2: IFC 2.3 gebruikt PascalCase (IfcWall) in plaats van UPPERCASE

**Oorzaak:** Version strategy niet correct ingesteld

**Oplossing:**
```python
# In version_strategies.py
class IFC23Strategy:
    def get_building_elements(self):
        return {
            'IfcWall',      # ← PascalCase voor 2.3
            'IfcDoor',
            ...
        }

class IFC40Strategy:
    def get_building_elements(self):
        return {
            'IFCWALL',      # ← UPPERCASE voor 4.x
            'IFCDOOR',
            ...
        }
```

---

### Issue 3: Elementen zonder materiaal skipped in Stap 2

**Oorzaak:** Filter criteria te streng

**Huige logica:**
```python
Skip element if:
- has_material_info = False AND geometric_representation = False
```

**Gewenst gedrag:**
```python
Process element if:
- has_material_info = True OR geometric_representation = True
```

---

### Issue 4: Performance traag voor grote bestanden

**Oorzaak:** Sequentiële verwerking

**Oplossing:** Controleer multi-threading in Stap 2:
```python
self.optimizer = PerformanceOptimizer(max_workers=4)  # Pas aan naar beschikbare CPU cores
```

---

## ⚡ Performance Optimalisatie

### Batch Processing
```python
# In performance_optimizer.py
process_elements_batch(
    elements_list,
    processor_func,
    batch_size=500  # Pas aan naar geheugen beschikbaarheid
)
```

### Multi-threading
```python
# max_workers = aantal CPU cores
# Standaard: 4
# Voor grote bestanden: 8-12
```

### Caching
```python
# material_linker_cache.py
# Cacht al opgehaalde materialen
self.cache.get_or_add(key, compute_func)
```

### Query Optimization
```python
# Minimaliseer IFC lookups
loaded_elements = {}
for element_id in batch:
    if element_id not in loaded_elements:
        loaded_elements[element_id] = ifc_file.by_id(element_id)
```

---

## ❓ FAQ

### Q: Warum worden sommige materialen niet gevonden?
**A:** Dit kan gebeuren als:
1. Materiaal is niet gekoppeld via IFCRELASSOCIATESMATERIAL
2. Element is gekoppeld aan TYPE, maar TYPE zelf geen materiaal heeft
3. PropertySet bestaat maar gebruikt ander naamschema
4. Model heeft inconsistentie in materiaalkoppeling

→ Check logs voor `resolution_method` kolom

---

### Q: Hoe weet ik welke fallback-methode per element gehanteerd is?
**A:** Check kolom `resolution_method` in Stap 3 output:
```
- "DIRECT" = Van Stap 2 (niet opgelost via fallback)
- "IFCRELDEFINESBYTYPE → IFCWALLTYPE" = Via TYPE resolver
- "IFCPROPERTYSET.MaterialName" = Via PropertySet resolver
- "IFCSTYLEDITEM → IFCSURFACESTYLE" = Via Style resolver
```

---

### Q: Kan ik specifieke fallback-strategieën uitschakelen?
**A:** Momenteel niet (config.py). In toekomst via:
```python
FALLBACK_STRATEGIES_ENABLED = {
    'TYPE': True,
    'PROPERTYSETS': True,
    'STYLE': True
}
```

---

### Q: Wat gebeurt er met elementen die nog steeds 'Unknown' zijn na Stap 3?
**A:** Ze blijven in de dataset met:
- `material_name = 'Unknown'`
- `data_quality_flag = 'UNRESOLVED'`
- `resolution_method = None`

Dit is intentioneel — geen hardcoded defaults.

---

### Q: Hoe groot mag het IFC-bestand zijn?
**A:** Afhankelijk van beschikbare RAM:
- < 100 MB: Zonder problemen
- 100-500 MB: Werkt, langzamer
- > 500 MB: Mogelijk geheugen problemen

→ Pas `max_workers` aan (minder = minder RAM)

---

### Q: Kan ik resultaten van Stap 2 en 3 mergen?
**A:** Ja! Beide geven DataFrame uit. Join op element_id:
```python
step_2_df = pd.read_excel('step_2_materials.xlsx', sheet_name='WALL')
step_3_df = pd.read_excel('step_3_materials_resolved.xlsx', sheet_name='MATERIALS')

# Filter op element_type
step_3_wall = step_3_df[step_3_df['element_type'] == 'IFCWALL']

merged = step_2_df.merge(step_3_wall, on=['element_id', 'element_type'], suffixes=('_s2', '_s3'))
```

---

## 📊 Dataflow Diagram

```
┌──────────────────────────┐
│ IFC-bestand laden        │
│ (Stap 0)                 │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Bouwkundige elementen    │
│ verzamelen (Stap 1)      │
│ → elements.xlsx          │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Direct materiaalkoppelingen
│ ophalen (Stap 2)         │
│ → materials.xlsx         │
│   (per element_type)     │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────────┐
│ Fallback resolution (Stap 3) │
│ - TYPE-based                 │
│ - PropertySet-based          │
│ - Style-based                │
│ → materials_resolved.xlsx    │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────┐
│ (Toekomstige stappen)    │
│ - Stap 4: Versieverschil │
│ - Stap 5: Hoeveelheden   │
│ - Stap 6: Eigenschappen  │
│ - Stap 7: Samenvoegen    │
│ - Stap 8: Exporteren     │
└──────────────────────────┘
```

---

## 🚀 Entry Point

**File:** `main.py`

```python
python main.py "C:\Users\cathy\Downloads\quest\4.3_bestand.ifc"
```

**Output:**
```
[OK] ALLE STAPPEN SUCCESVOL VOLTOOID
- Totaal elementen verzameld: 3922
- Totaal materiaalkoppelingen: 12543
- Totaal via fallback opgelost: 1245
```

---

## 📝 Versiegeschiedenis

| Versie | Datum | Wijzigingen |
|--------|-------|------------|
| 1.0 | 2024 | Stap 0-3 volledig geïmplementeerd |
| 1.1 | 2024 | Multi-threading toevoegd aan Stap 2 |
| 1.2 | 2024 | Fallback-strategieën (Stap 3) afgerond |

---

**Laatste Update:** April 2024  
**Auteur:** GitHub Copilot  
**Status:** Production Ready (Stap 0-3)