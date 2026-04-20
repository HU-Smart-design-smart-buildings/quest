from core.logger import setup_logger

logger = setup_logger(__name__)

class MaterialLinkerCache:
    """
    Cache voor type-definities om performance te verbeteren.
    Slaat material-definities op zodat dezelfde types niet herhaald hoeven te worden opgehaald.
    """
    
    def __init__(self, ifc_file):
        self.ifc_file = ifc_file
        self.material_cache = {}       # Cache voor materiaal-ID → materiaal object
        self.layerset_cache = {}       # Cache voor layerset-ID → layerset data
        self.constituent_cache = {}    # Cache voor constituent-ID → constituent data
        self.cache_hits = 0
        self.cache_misses = 0
    
    def get_or_cache_material(self, material_id, retriever_func):
        """
        Haal materiaal uit cache of bereken het en cache het.
        
        Args:
            material_id: Unieke ID van het materiaal
            retriever_func: Functie om materiaal op te halen indien niet in cache
        
        Returns:
            Materiaal data
        """
        if material_id in self.material_cache:
            self.cache_hits += 1
            return self.material_cache[material_id]
        
        # Niet in cache - bereken en cache het
        material_data = retriever_func()
        self.material_cache[material_id] = material_data
        self.cache_misses += 1
        
        return material_data
    
    def get_or_cache_layerset(self, layerset_id, retriever_func):
        """
        Haal layerset uit cache of bereken het en cache het.
        """
        if layerset_id in self.layerset_cache:
            self.cache_hits += 1
            return self.layerset_cache[layerset_id]
        
        layerset_data = retriever_func()
        self.layerset_cache[layerset_id] = layerset_data
        self.cache_misses += 1
        
        return layerset_data
    
    def get_or_cache_constituent(self, constituent_id, retriever_func):
        """
        Haal constituent uit cache of bereken het en cache het.
        """
        if constituent_id in self.constituent_cache:
            self.cache_hits += 1
            return self.constituent_cache[constituent_id]
        
        constituent_data = retriever_func()
        self.constituent_cache[constituent_id] = constituent_data
        self.cache_misses += 1
        
        return constituent_data
    
    def get_cache_stats(self):
        """
        Retourneer cache statistieken.
        """
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'total_requests': total_requests,
            'hit_rate': round(hit_rate, 2),
            'materials_cached': len(self.material_cache),
            'layersets_cached': len(self.layerset_cache),
            'constituents_cached': len(self.constituent_cache)
        }
    
    def clear_cache(self):
        """
        Clear alle caches.
        """
        self.material_cache.clear()
        self.layerset_cache.clear()
        self.constituent_cache.clear()
        logger.info("✓ Caches geleegd")