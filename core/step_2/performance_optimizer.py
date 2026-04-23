import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from core.logger import setup_logger

logger = setup_logger(__name__)

class PerformanceOptimizer:
    """
    Optimaliseert verwerking van materiaalkoppelingen via:
    - Batch processing
    - Multi-threading
    - Intelligente caching
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.thread_lock = threading.Lock()
        self.processed_count = 0
        self.error_count = 0
    
    def process_elements_batch(self, elements_list: List[Dict], processor_func, batch_size: int = 500):
        """
        Verwerk elementen in batches met multi-threading.
        
        Args:
            elements_list: Liste van elementen om te verwerken
            processor_func: Functie die één element verwerkt
            batch_size: Aantal elementen per batch
        
        Returns:
            Gecombineerde resultaten van alle batches
        """
        total_elements = len(elements_list)
        all_results = []
        
        logger.info(f"Start batch verwerking: {total_elements} elementen, batch_size={batch_size}")
        
        # Verdeel in batches
        batches = [
            elements_list[i:i + batch_size] 
            for i in range(0, total_elements, batch_size)
        ]
        
        # Verwerk batches parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._process_batch, batch, processor_func, batch_idx): batch_idx
                for batch_idx, batch in enumerate(batches)
            }
            
            for future in as_completed(futures):
                batch_idx = futures[future]
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                    
                    completed_batches = len([f for f in futures if f.done()])
                    print(f"  └─ Batch {batch_idx + 1}/{len(batches)} voltooid ({len(all_results)}/{total_elements} items)")
                
                except Exception as e:
                    logger.error(f"Fout in batch {batch_idx}: {e}")
                    with self.thread_lock:
                        self.error_count += len(batches[batch_idx])
        
        logger.info(f"Batch verwerking voltooid: {len(all_results)} geslaagd, {self.error_count} fouten")
        return all_results
    
    def _process_batch(self, batch: List[Dict], processor_func, batch_idx: int) -> List[Dict]:
        """
        Verwerk één batch.
        """
        batch_results = []
        
        for idx, element in enumerate(batch):
            try:
                result = processor_func(element)
                if result is not None:
                    if isinstance(result, list):
                        batch_results.extend(result)
                    else:
                        batch_results.append(result)
                
                with self.thread_lock:
                    self.processed_count += 1
            
            except Exception as e:
                logger.debug(f"Fout bij verwerking element in batch {batch_idx}, item {idx}: {e}")
                with self.thread_lock:
                    self.error_count += 1
        
        return batch_results
    
    def get_stats(self) -> Dict[str, int]:
        """
        Haal verwerkingsstatistieken op.
        """
        return {
            'processed': self.processed_count,
            'errors': self.error_count,
            'successful': self.processed_count - self.error_count
        }