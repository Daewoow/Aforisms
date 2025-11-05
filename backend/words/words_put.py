from pprint import pprint

from backend.words.words_repository import WordsRepository

if __name__ == '__main__':
    word_response = WordsRepository().put_word(5, "Бахвальство", "Самонадеянное, кичливое хвастовство")
    print("Word added successfully:")
    pprint(word_response, sort_dicts=False)
