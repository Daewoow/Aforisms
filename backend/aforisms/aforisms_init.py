import json
from decimal import Decimal

from backend.aforisms.aforisms_repository import AforismsRepository
from backend.aforisms.aforisms_table_creater import AforismTableHelper

if __name__ == '__main__':
    series_table = AforismTableHelper().create_table()
    print("Table status:", series_table.table_status)

    with open("../../aforisms.json", encoding='utf-8') as json_file:
        document_list = json.load(json_file, parse_float=Decimal)
    AforismsRepository().load_data(document_list)
