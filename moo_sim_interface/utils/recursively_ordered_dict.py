from collections import UserDict


class RecursivelyOrderedDict(UserDict):
    def __getitem__(self, key):
        split_key = key.split('.', 1)
        if len(split_key) > 1:
            return self.data[split_key[0]][split_key[1]]
        else:
            return self.data[key]

    def __setitem__(self, key, value):
        split_key = key.split('.', 1)
        if len(split_key) > 1:
            if split_key[0] not in self.data:
                self.data[split_key[0]] = RecursivelyOrderedDict()
            self.data[split_key[0]][split_key[1]] = value
        else:
            self.data[key] = value
