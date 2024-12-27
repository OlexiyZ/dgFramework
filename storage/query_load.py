import json
import re
from pathlib import Path
from .models import Query, SourceList, Source, FieldList, Field

def process_field_list(field_data):
    """
    Creating FieldList and Field from JSON structure.
    """
    field_list, _ = FieldList.objects.get_or_create(
        field_list_name=field_data["field_list"],
        data_source=SourceList.objects.get(source_list=field_data["source_list_name"]),
    )

    # Adding fields to FieldList
    Field.objects.create(
        field_list=field_list,
        source_list=SourceList.objects.get(source_list=field_data["source_list_name"]),
        field_alias=field_data.get("field_alias"),
        field_source_type=field_data.get("field_source_type"),
        field_source=field_data.get("field_source"),
        field_name=field_data.get("field_name"),
        field_value=field_data.get("field_value"),
        field_function=field_data.get("field_function"),
        function_field_list=field_data.get("function_field_list"),
    )


def process_source(source_data):
    """
    Creating data sources (Source) from JSON structure.
    """
    source_list, _ = SourceList.objects.get_or_create(source_list=source_data["source_union_list_name"])

    Source.objects.create(
        source_union_list=source_list,
        source_alias=source_data["source_alias"],
        source_type=source_data["source_type"],
        table_name=source_data["source_name"],
        source_scheme=source_data.get("source_scheme"),
        union_type=source_data.get("union_type"),
        union_condition=source_data.get("union_condition"),
        source_description=source_data.get("source_description"),
    )


def process_query(query_data, parent_query=None):
    """
    Recursive function for processing queries and their nesting.
    """

    # Creating a SourceList for a query
    source_list, _ = SourceList.objects.get_or_create(source_list=query_data["query_source"])
    # Creating a FieldList for a query
    query_field_list, _ = FieldList.objects.get_or_create(
        field_list_name=query_data["query_fields"],
        # data_source=SourceList.objects.get(source_list=query_data["query_source"]),
        data_source=SourceList.objects.get(id=source_list.id),
    )

    # Creating a request
    query = Query.objects.create(
        query_name=query_data["query_name"],
        field_list=query_field_list,
        query_conditions=query_data.get("query_conditions"),
        query_description=query_data.get("query_description"),
        query_alias=None,  # Додати, якщо є
        source_list=SourceList.objects.get(source_list=query_data["query_source"]),
    )

    # Column processing
    for column in query_data.get("columns", []):
        # pass
        process_field_list(column)

    # Source processing
    for source in query_data.get("sources", []):
        # pass
        process_source(source)

    # Handling nested queries
    for nested_query in query_data.get("nested", []):
        process_query(nested_query, parent_query=query)


# Basic processing process
def nested_queryies_load(nested_queries):
    cleaned_string = re.sub(r"\s+", " ", nested_queries).strip()
    json_data = json.loads(cleaned_string)
    try:
        for query in json_data.get("queries", []):
            process_query(query)
        return True, f"Imported successfully"
    except Exception as e:
        return False, f"error: {str(e)}"


if __name__ == "__main__":
    # Uploading a JSON file
    json_file = Path("nested_queries.json")
    with open(json_file, "r") as file:
        nested_queries = json.load(file)

    nested_queryies_load(nested_queries)

    # for query in nested_queries.get("queries", []):
    #     process_query(query)
    #
    # print("Nested queries loaded successfully!")
