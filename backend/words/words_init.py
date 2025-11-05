import json
from decimal import Decimal

from backend.words.words_repository import WordsRepository
from backend.words.words_table_creater import WordTableHelper

if __name__ == '__main__':

    with open("../../words.json", encoding='utf-8') as json_file:
        document_list = json.load(json_file, parse_float=Decimal)
    WordsRepository().load_data(document_list)

    series_table = WordTableHelper().create_table()
    print("Table status:", series_table.table_status)

