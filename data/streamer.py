import pandas as pd
import gc

class DataStreamer:
    """
    Chronologically streams a massive CSV file in chunks without loading
    the entire dataset into memory. 
    """
    def __init__(self, csv_path: str, chunk_size: int = 100000):
        self.csv_path = csv_path
        self.chunk_size = chunk_size
        
        # pd.read_csv with chunksize creates an open file iterator
        # It never restarts from the top, allowing for lightning fast chronological streaming.
        self.iterator = pd.read_csv(csv_path, chunksize=chunk_size)
        self.current_batch_number = 0

    def get_next_batch(self, target_column: str = None, min_positive_cases: int = 10) -> pd.DataFrame:
        """
        Grabs the next chronological chunks of data.
        If target_column is provided, it ensures at least `min_positive_cases` exist to prevent training crashes.
        """
        accumulated_chunks = []
        positive_count = 0
        
        try:
            while True:
                batch = next(self.iterator)
                accumulated_chunks.append(batch)
                
                # If a target column is provided, ensure we have enough positive cases
                if target_column and target_column in batch.columns:
                    positive_count += batch[target_column].sum()
                    if positive_count >= min_positive_cases:
                        break  # We have enough cases to train safely
                else:
                    break  # If no target specified, just return the single chunk
                
            self.current_batch_number += len(accumulated_chunks)
            final_batch = pd.concat(accumulated_chunks, ignore_index=True)
            
            gc.collect()
            return final_batch
            
        except StopIteration:
            if accumulated_chunks:
                return pd.concat(accumulated_chunks, ignore_index=True)
            raise ValueError("End of streaming data reached.")
