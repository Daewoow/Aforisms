from pprint import pprint

from backend.aforisms.aforisms_repository import AforismsRepository

if __name__ == '__main__':
    aforism_response = AforismsRepository().put_word(5, "Не солона хлебавши", "", "Нничего не добившись, обманувшись в своих ожиданиях")
    print("Aforism added successfully:")
    pprint(aforism_response, sort_dicts=False)
