

def create_item_if_not_exist(ddb_table, item_key: dict, body: str):
    response = ddb_table.get_item(
        Key=item_key
    )
    item = response.get("Item")
    if not item: 
        ddb_table.put_item(Item=body)
