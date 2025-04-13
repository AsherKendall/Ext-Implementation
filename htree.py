from hashlib import sha256

class HTreeNode:
    def __init__(self, is_leaf=False):
        self.is_leaf = is_leaf
        self.entries = []
        self.children = []

class HTree:
    def __init__(self):
        self.root = HTreeNode()

    def hash_filename(self, filename):
        # Simple hash function for demonstration purposes
        return sha256(filename.encode('utf-8')).hexdigest()

    def insert(self, filename):
        hash_value = self.hash_filename(filename)
        current_node = self.root

        while not current_node.is_leaf:
            for entry in current_node.entries:
                if entry['hash'] == hash_value:
                    current_node = entry['child']
                    break
            else:
                new_node = HTreeNode(is_leaf=True)
                current_node.entries.append({'hash': hash_value, 'child': new_node})
                current_node = new_node

        current_node.entries.append({'filename': filename, 'hash': hash_value})

    def search(self, filename):
        hash_value = self.hash_filename(filename)
        current_node = self.root

        while not current_node.is_leaf:
            for entry in current_node.entries:
                if entry['hash'] == hash_value:
                    current_node = entry['child']
                    break
            else:
                return None

        for entry in current_node.entries:
            if entry['filename'] == filename:
                return entry

        return None

# Example usage
htree = HTree()
htree.insert("file1.txt")
htree.insert("file2.txt")
htree.insert("file3.txt")
htree.insert("file4.txt")
htree.insert("file5.txt")
htree.insert("file6.txt")
htree.insert("file7.txt")

print(htree.search("file1.txt"))  # Output: {'filename': 'file1.txt', 'hash': 102}
print(htree.search("file55.txt"))  # Output: None

print(htree.root.entries)