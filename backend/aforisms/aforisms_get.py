from pprint import pprint

from backend.aforisms.aforisms_repository import AforismsRepository

if __name__ == '__main__':
    word = AforismsRepository().get_aforism(3, "Томный")
    if word:
        print("Record read:")
        pprint(word, sort_dicts=False)
