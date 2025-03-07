import json
import requests
import re
from bs4 import BeautifulSoup



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
    if section["name"] in ["Noun", "Verb", "Adjective", "Adverb"]:
        process_section(section, parent_node, 
                        [], # no tags to process here, only lines
                        "word-classes", 
                        multiple=True, add_name=True, process_lines=True)
                        



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


def process_section(section, parent_node, tags_to_process, node_name, multiple=False, add_name=False, process_lines=False):
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

        if process_lines:
            process_line(line, section_node)

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
    # pronunciation section
    if tag_head(tag) in ["enPR"]:
        section_node[tag_head(tag)] = tag_arg(tag, 1)
    if tag_head(tag) in ["IPA"]:
        section_node[tag_head(tag)] = tag_arg(tag, 2)
    if tag_head(tag) in ["homophones", "rhymes"]:
        section_node[tag_head(tag)].append(tag_arg(tag, 2))

    # etymology section
    if tag_head(tag) in ["root"]:
        new_node = { "langcode": tag_arg(tag, 2), "word": tag_arg(tag, 3) }
        section_node["root"] = new_node
    if tag_head(tag) in ["inh"]:
        new_node = { "langcode": tag_arg(tag, 2), "word": tag_arg(tag, 3) }
        section_node["inherits"].append(new_node)
    if tag_head(tag) in ["cog", "m"]: 
        # {{cog|fy|read}}
        # {{cog|sq|pruth||redhead}} - arg 4 is the gloss
        # {{cog|sa|रुधिर|tr=rudhirá||red, bloody}} - arg 3 is the transliteration, arg 5 is the gloss
        # {{cog|grc|ἐρυθρός}} - arg 2 is a non-Latin word but no transliteration is provided
        new_node = { "langcode": tag_arg(tag, 1), "word": tag_arg(tag, 2) }
        arg4 = tag_arg(tag, 4)
        arg5 = tag_arg(tag, 5)
        if arg4 and arg4 != "" and "=" not in arg4: # can appear in 4 or 5
            new_node["gloss"] = arg4
        if arg5 and arg5 != "" and "=" not in arg5: # can appear in 4 or 5
            new_node["gloss"] = arg5
        translit = tag_key(tag, "tr")
        # if there is no transliteration for a non-Latin script word, get it from Wiktionary
        # remember that we stripped the {{}} from the tag, so add them back in
        # NB we may have a hyphen, apostrophe, or an asterisk for reconstructed words
        if not translit and not re.match(r"^[a-zA-Z'*-]+$", tag_arg(tag, 2)):
            translit = get_transliteration_from_wiktionary("{{" + tag + "}}", "red", "en") # TODO
        # if we now have a transliteration, add it to the node
        if translit:
            new_node["translit"] = translit
        section_node["cognates"].append(new_node)

# in some sections we need to process lines rather than tags
def process_line(line, section_node):
    if section_node["name"] in ["Noun", "Verb", "Adjective", "Adverb"]:
        if "definitions" not in section_node:
            section_node["definitions"] = []
        if line.startswith("# "):
            definition = get_text_from_wiktionary(line[2:], "red", "en") # TODO
            section_node["definitions"].append(definition)




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
        
def get_text_from_wiktionary(text, word, langcode):
    html = get_html_from_wiktionary(text, word, langcode)
    # get the text from the HTML
    soup = BeautifulSoup(html, 'lxml')
    return soup.get_text()

def get_transliteration_from_wiktionary(text, word, langcode):
    html = get_html_from_wiktionary(text, word, langcode)
    # get the transliteration from the HTML
    soup = BeautifulSoup(html, 'lxml')
    span = soup.find('span', class_='Latn')
    if span:
        return span.get_text()
    else:
        return None

def get_html_from_wiktionary(text, word, langcode):
    # for a piece of Wikitext, get the formatted text from Wiktionary
    # first define the URL to retrieve the data
    urlHead = "https://en.wiktionary.org/w/api.php?action=parse&text="
    urlMid = "&prop=text&title="
    urlTail = "&formatversion=2&format=json"

    # first, encode any # symbols in the text
    text = text.replace("#", "%23")

    # make an HTTP request to Wiktionary
    response = requests.get(urlHead + text + urlMid + get_page_title(word, langcode) + urlTail)

    # get the HTML from the JSON data
    html = response.json()['parse']['text']

    return html

def get_page_title(word, langcode):
    # reconstructed words have a different format, for now just return the word
    return word



