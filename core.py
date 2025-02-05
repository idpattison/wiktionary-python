import json
import requests
import re

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
    tree = wikitext_to_tree_nodes(wikitext, language)

    # now convert the generic tree nodes to a specific language directory
    language_tree = tree_nodes_to_language_tree(tree, language, word)

    print(language_tree)




def wikitext_to_tree_nodes(wikitext, language):
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

def tree_nodes_to_language_tree(tree, language, word):
    # create a directory with specific labels for the given language
    # if we can't find the language, return an empty dictionary 
    language_tree = {}

    # iterate through the children of the root node - these will all be languages
    for child in tree["children"]:
        if child["name"] == "English":  # hard coded for now

            # add basic information to the language tree
            language_tree["word"] = word
            language_tree["language"] = "en"
            language_tree["gloss"] = word # this should be the meaning of the word

            # iterate through the grandchildren of the language node
            for section in child["children"]:
                process_section(section, language_tree)

    print(language_tree)

def process_section(section, parent_node):
    # process the section node and return a dictionary to add to the parent node
    if section["name"] == "Pronunciation":
        process_pronunciation_section(section, parent_node)
    if section["name"].startswith("Etym"):
        process_etymology_section(section, parent_node)


def process_pronunciation_section(section, parent_node):
    # process the pronunciation section and return a dictionary to add to the parent node
    pronunciation_node = {}
    for line in section["lines"]:
        tags = get_tags(line)
        for tag in tags:
            arguments = get_tag_arguments(tag)
            if arguments[0] in ["enPR"]:
                pronunciation_node[arguments[0]] = arguments[1]
            if arguments[0] in ["IPA", "homophones", "rhymes"]:
                pronunciation_node[arguments[0]] = arguments[2]

    parent_node["pronunciation"] = pronunciation_node

def process_etymology_section(section, parent_node):
    # process the etymology section and return a dictionary to add to the parent node
    etymology_node = { "name": section["name"] }

    # check if we already have an etymology array in the parent node
    if "etymologies" not in parent_node:
        parent_node["etymologies"] = []

    for line in section["lines"]:
        tags = get_tags(line)
        for tag in tags:
            arguments = get_tag_arguments(tag)
            # root tage has the format {{root|en|ine-pro|*h₁rewdʰ-}}
            if arguments[0] == "root":
                root_node = { "langcode": arguments[2], "word": arguments[3] }
                etymology_node["root"] = root_node

    parent_node["etymologies"].append(etymology_node)


def get_tags(line):
    # get the tags from the line
    # tags are enclosed in double brackets like this: {{head|var1|var2}}
    tags = re.findall(r'\{\{(.*?)\}\}', line)
    return tags

def get_tag_arguments(tag):
    # get the arguments from a tag
    # arguments are separated by pipes like this: head|var1|var2
    arguments = tag.split('|')
    return arguments