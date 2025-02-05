import json
import requests

class TreeNode:
    def __init__(self, type=None, name=None):  # type for the node, attributes as keyword args
        self.name = name
        self.type = type
        self.lines = []  # Initialize as an empty list
        self.children = [] # Initialize as an empty list

    def add_child(self, child):
        self.children.append(child)

    def add_line(self, line):
        self.lines.append(line)

    def __repr__(self):  # For easy printing/representation
        return f"TreeNode(name={self.name}, lines={len(self.lines)})"



def get_word(word, language):

    # for the given word, retrieve the JSON data from Wiktionary
    # first define the URL to retrieve the data
    urlHead = "https://en.wiktionary.org/w/api.php?action=parse&page="
    urlTail = "&prop=wikitext&format=json"
    url = urlHead + word + urlTail

    # make an HTTP request to Wiktionary
    response = requests.get(url)
    data = response.json()

    # extract the wikitext from the JSON data
    wikitext = data['parse']['wikitext']['*']

    # parse the wikitext to extract the sections for the given language
    tree = wikitext_to_tree(wikitext, language)
    print(tree)




def wikitext_to_tree(wikitext, language):
    tree = { "name": "Root", "level": 0, "children": [], "lines": [] } # Initialize the tree with a root node
    node_path = [tree] # breadcrumb trail of the current nodes so we can add to the correct on;e

    for line in wikitext.split('\n'):

        # ignore blank lines
        if not line:
            continue

        # section headers start with ==
        if line.startswith('=='):
            level = int(line.count('=') / 2) - 1
            title = line.strip('=')

            # size of node path should be one less than the level
            # if not, pop until it is
            while len(node_path) > level:
                node_path.pop()

            # create the new node and add it as a child
            # tree node class depends on the name of the section
            node = { "name": title, "level": level, "children": [], "lines": [] }
            node_path[-1]["children"].append(node)
            # finally add the new node to the node path
            node_path.append(node)

        # line does not start with ==
        else:
            if len(node_path) > 0: # ignore anything before the first section - it will be the 'see also' block
                node_path[-1]["lines"].append(line)

    return tree


 
