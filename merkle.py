from merkly.mtree import MerkleTree
from merkly.node import Node, Side
import hashlib

class Node:
    def __init__(self, children=None, value=None):
        self.children = children if children is not None else []
        self.value = value

def hash_function(data):
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def create_htree(data_list):
    # Create leaf nodes
    leaf_nodes = [Node(value=hash_function(data)) for data in data_list]

    # Create root node if only one level is needed
    if len(leaf_nodes) <= 4:
        return Node(children=leaf_nodes, value=hash_function(''.join(node.value for node in leaf_nodes)))

    # Create intermediate nodes for two levels
    intermediate_nodes = []
    for i in range(0, len(leaf_nodes), 4):
        children = leaf_nodes[i:i + 4]
        combined_hash = hash_function(''.join(node.value for node in children))
        intermediate_nodes.append(Node(children=children, value=combined_hash))

    # Create root node
    root_hash = hash_function(''.join(node.value for node in intermediate_nodes))
    root_node = Node(children=intermediate_nodes, value=root_hash)

    return root_node

def print_htree(node, level=0):
    if node:
        print(' ' * 4 * level + '->', node.value)
        for child in node.children:
            print_htree(child, level + 1)
def search_htree(node, name):
    target_hash = hash_function(name)
    if node.value == target_hash:
        return node
    for child in node.children:
        result = search_htree(child, target_hash)
        if result:
            return result
    return None


# Example usage
data = ['file1.txt', 'file2.txt', 'file3.txt', 'file4.txt', 'file5.txt', 'file6.txt', 'file7.txt', 'file8.txt', 'file9.txt', 'file10.txt']
root = create_htree(data)
print(search_htree(root,'file5.txt'))
print_htree(root)
