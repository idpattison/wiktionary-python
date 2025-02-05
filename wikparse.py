import argparse

from core import get_word

def main():
    parser = argparse.ArgumentParser(description='Process some words.')
    parser.add_argument('word', type=str, help='The word to process')
    parser.add_argument('-l', '--language', type=str, help='The language code of the word')

    args = parser.parse_args()

    word = args.word
    language = args.language

    get_word(word, language)

if __name__ == "__main__":
    main()