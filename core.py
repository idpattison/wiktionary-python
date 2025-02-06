import json
import requests
import re

# class TreeNode:
#     def __init__(self, type=None, name=None):  # type for the node, attributes as keyword args
#         self.name = name
#         self.type = type
#         self.lines = []  # Initialize as an empty list
#         self.children = [] # Initialize as an empty list

#     def add_child(self, child):
#         self.children.append(child)

#     def add_line(self, line):
#         self.lines.append(line)

#     def __repr__(self):  # For easy printing/representation
#         return f"TreeNode(name={self.name}, lines={len(self.lines)})"



def get_word(word, langcode):

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
    tree = wikitext_to_tree_nodes(wikitext, langcode)

    # now convert the generic tree nodes to a specific language directory
    language_tree = tree_nodes_to_language_tree(tree, langcode, word)

    print(language_tree)




def wikitext_to_tree_nodes(wikitext, langcode):
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

def tree_nodes_to_language_tree(tree, langcode, word):
    # create a directory with specific labels for the given language
    # if we can't find the language, return an empty dictionary 
    language_tree = {}

    # iterate through the children of the root node - these will all be languages
    for child in tree["children"]:
        if child["name"] == "English":  # hard coded for now

            # add basic information to the language tree
            language_tree["word"] = word
            language_tree["langcode"] = "en"
            language_tree["gloss"] = word # only include this for non-English words

            # iterate through the grandchildren of the language node
            for section in child["children"]:
                process_children(section, language_tree)

    print(language_tree)


def process_children(section, parent_node):
    if section["name"] == "Pronunciation":
        # process_pronunciation_section(section, parent_node)
        process_section(section, parent_node, 
                        ["enPR", "IPA", "homophones", "rhymes"], 
                        "pronunciation")
    if section["name"].startswith("Etym"):
        # process_etymology_section(section, parent_node)
        process_section(section, parent_node, 
                        ["root", "inh", "cog", "m"], 
                        "etymologies", multiple=True, add_name=True)



# i want to make this more generic and parameter driven, here are the potential situations
# *** section processing
# section can be a one-off (Pronunciation) or can be potentially multiple (Etymology)
# within each section, we can process tags or lines
# e.g. Pronunciation is just processing of tags, but Word Class section will want to look at each line for 
# inflection details and definitions
# *** tag processing
# tags can be one-off (IPA) or multiple (inh)
# tag head can be copied through or changed - inh = inherits
# tag arguments will differ - we need to map arg position to key
# {{cog|fy|read}} maps to { "cognates": [ { "langcode": "fy", "word": "read" } ] }
# sometimes there is only one argument, so the array will contain simple values not dictionaries
# {{homophones|en|read}} maps to { "homophones": [ "read" ] }


def process_section(section, parent_node, tags_to_process, node_name, multiple=False, add_name=False):
    section_node = {}
    # if there could be multiple sections, set up an array
    if multiple:
        if (node_name not in parent_node):
            parent_node[node_name] = []

    if add_name:
        section_node["name"] = section["name"]

    for line in section["lines"]:
        tags = get_tags(line)
        for tag in tags:
            if tag_head(tag) in tags_to_process:
                process_tag(tag, section_node)

    for child in section["children"]:
        process_children(child, section_node)

    if multiple:
        parent_node[node_name].append(section_node)
    else:
        parent_node[node_name] = section_node

def process_tag(tag, section_node):
    # check for tags which can be multiple, these will need an array to have been set up
    # NB other tags are added directly to the section node
    if tag_head(tag) in ["homophones", "rhymes"]: # these use the tag head as the key
        if tag_head(tag) not in section_node:
            section_node[tag_head(tag)] = []
    if tag_head(tag) in ["cog", "m"]:
        if "cognates" not in section_node:
            section_node["cognates"] = []
    if tag_head(tag) in ["inh"]:
        if "inherits" not in section_node:
            section_node["inherits"] = []

    # process each type of tag
    if tag_head(tag) in ["enPR"]:
        section_node[tag_head(tag)] = tag_arg(tag, 1)
    if tag_head(tag) in ["IPA"]:
        section_node[tag_head(tag)] = tag_arg(tag, 2)
    if tag_head(tag) in ["homophones", "rhymes"]:
        section_node[tag_head(tag)].append(tag_arg(tag, 2))
    if tag_head(tag) in ["root"]:
        new_node = { "langcode": tag_arg(tag, 2), "word": tag_arg(tag, 3) }
        section_node["root"] = new_node

    if tag_head(tag) in ["inh"]:
        new_node = { "langcode": tag_arg(tag, 2), "word": tag_arg(tag, 3) }
        section_node["inherits"].append(new_node)
    if tag_head(tag) in ["cog", "m"]: 
        # {{cog|fy|read}}
        # {{cog|sq|pruth||redhead}}
        # {{cog|sa|रुधिर|tr=rudhirá||red, bloody}}
        new_node = { "langcode": tag_arg(tag, 1), "word": tag_arg(tag, 2) }
        arg4 = tag_arg(tag, 4)
        arg5 = tag_arg(tag, 5)
        if arg4 and arg4 != "" and "=" not in arg4: # can appear in 4 or 5
            new_node["gloss"] = arg4
        if arg5 and arg5 != "" and "=" not in arg5: # can appear in 4 or 5
            new_node["gloss"] = arg5
        translit = tag_key(tag, "tr")
        if translit:
            new_node["translit"] = translit
        section_node["cognates"].append(new_node)


def process_pronunciation_section(section, parent_node):
    # process the pronunciation section and return a dictionary to add to the parent node
    pronunciation_node = {}
    for line in section["lines"]:
        tags = get_tags(line)
        for tag in tags:
            if tag_head(tag) in ["enPR"]:
                pronunciation_node[tag_head(tag)] = tag_arg(tag, 1)
            if tag_head(tag) in ["IPA", "homophones", "rhymes"]:
                pronunciation_node[tag_head(tag)] = tag_arg(tag, 2)

    parent_node["pronunciation"] = pronunciation_node

def process_etymology_section(section, parent_node):
    # process the etymology section and return a dictionary to add to the parent node
    etymology_node = { "name": section["name"] }

    # check if we already have an etymology array in the parent node
    if "etymologies" not in parent_node:
        parent_node["etymologies"] = []

    for line in section["lines"]:
        tags = get_tags(line)
        previous_word = ""
        for tag in tags:

            # root tag has the format {{root|en|ine-pro|*h₁rewdʰ-}}
            if tag_head(tag) == "root":
                root_node = { "langcode": tag_arg(tag, 2), "word": tag_arg(tag, 3) }
                etymology_node["root"] = root_node
                previous_word = tag_arg(tag, 3)

            # inh tag has the format {{inh|en|enm|red|id=red}}
            # cog tag has the format {{cog|en|enm|red}}
            # m tag is an alias for cog
            # if the word is "-" then use the previous word
            if tag_head(tag) in ["inh", "cog", "m"]:
                if tag_head(tag) == "inh":
                    index_name = "inherits"
                    lang = tag_arg(tag, 2)
                    word = tag_arg(tag, 3)
                if tag_head(tag) in ["cog", "m"]:
                    index_name = "cognates"
                    lang = tag_arg(tag, 1)
                    word = tag_arg(tag, 2)
                # check if we already have the relevant node in the etymology node
                if index_name not in etymology_node:
                    etymology_node[index_name] = []
                if word == "-":
                    new_node = { "langcode": lang, "word": previous_word }
                else:
                    new_node = { "langcode": lang, "word": word }
                # if there is a tag 3 in a non-inh tag, it is likely to be a transliteration
                # format is tr=transliteration
                # we should also check if the word is in a non-Latin script
                if tag_head(tag) != "inh" and tag_arg(tag, 3) and tag_arg(tag, 3) != "" and not re.match(r'^[a-zA-Z0-9]*$', word):
                    new_node["translit"] = tag_arg(tag, 3)[3:]
                # if there is a tag 4 or tag 5, it is likely to be a gloss
                if tag_arg(tag, 4) and tag_arg(tag, 4) != "":
                    new_node["gloss"] = tag_arg(tag, 4)
                if tag_arg(tag, 5) and tag_arg(tag, 5) != "":
                    new_node["gloss"] = tag_arg(tag, 5)
                etymology_node[index_name].append(new_node)
                if word != "-":
                    previous_word = word

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

def tag_head(tag):
    # get the head, which will be the first argument
    return get_tag_arguments(tag)[0]

def tag_arg(tag, index):
    # get the argument at the given index
    if len(get_tag_arguments(tag)) > index:
        return get_tag_arguments(tag)[index]
    else:
        return None
    
def tag_key(tag, key):
    # get a key from the start of an argument
    # format will be {{cog|sa|रुधिर|tr=rudhirá||red, bloody}}
    # return the key's value
    args = get_tag_arguments(tag)
    for arg in args:
        if arg.startswith(key + "="):
            return arg.split('=')[1]