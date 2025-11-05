from pprint import pprint

from words_repository import WordsRepository

if __name__ == '__main__':
    update_response = WordsRepository().update_word(
        3, "Томный", "Устало-нежный/испытывающий неясную, беспричинную грусть")
    print("Series updated:")
    pprint(update_response, sort_dicts=False)
