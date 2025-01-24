import numpy as np


class BatchedIterator:
    def __init__(self, data, batch_size):
        self.data = data
        self.batch_size = batch_size
        self.indices = np.arange(len(data))
        self.current_idx = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.current_idx >= len(self.data):
            raise StopIteration
        batch_indices = self.indices[self.current_idx:self.current_idx + self.batch_size]
        self.current_idx += self.batch_size
        return [self.data[i] for i in batch_indices]

    def __len__(self):
        return len(self.data) // self.batch_size

    def reset(self):
        self.current_idx = 0
