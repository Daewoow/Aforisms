from pprint import pprint

from backend.words.words_repository import WordsRepository

if __name__ == '__main__':
    word = WordsRepository().get_word(3, "Томный")
    if word:
        print("Record read:")
        pprint(word, sort_dicts=False)
