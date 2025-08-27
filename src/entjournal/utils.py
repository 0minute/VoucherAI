import json
from src.entjournal.constants import FIELD_SCHEMA_PATH

def load_field_schema():
    with open(FIELD_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_field_list():
    field_schema = load_field_schema()
    field_list = [key for key in field_schema.keys()]
    return field_list

def get_field_sap(fieldname:str):
    field_schema = load_field_schema()
    return field_schema.get(fieldname, None)["SAP"]

def get_field_dzone(fieldname:str):
    field_schema = load_field_schema()
    return field_schema.get(fieldname, None)["DZ"]
