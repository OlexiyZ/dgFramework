import json
import re
from pathlib import Path
from .models import Query, SourceList, Source, FieldList, Field, UnionType, SourceSystem, SourceScheme, Report
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils.timezone import now


def process_field_list(field_data):
    """
    Creating FieldList and Field from JSON structure.
    """
    import_result = []
    try:
        source_list, created = SourceList.objects.get_or_create(source_list=field_data['source_list_name'])
        if created:
            import_result.append((field_data['source_list'], 'SourceList created'))
            print(f"Field {source_list.source_list} SourceList created")

        field_list, created = FieldList.objects.get_or_create(field_list_name=field_data['field_list'],
                                                              data_source=source_list)
        if created:
            import_result.append((field_data['field_list'], 'FieldList created'))
            print(f"Field {field_list.field_list_name} FieldList created")

        if field_data['field_source']:
            if field_data['data_source_type'] == 'query':
                try:
                    query_object, created = Query.objects.get_or_create(query_name=field_data['field_source'])
                    if created:
                        import_result.append((query_object.query_name, 'Query created'))
                        print(f"Field {query_object.query_name} Query created")
                    else:
                        import_result.append((query_object.query_name, 'Query updated'))
                        print(f"Field {query_object.query_name} Query updated")
                except Exception as e:
                    import_result.append(f"Query {query_object.query_name} creation error: {e}")
                    print(f"Query {query_object.query_name} creation error: {e}")

                field_source, created = Source.objects.get_or_create(
                    source_union_list=source_list,
                    query_name=query_object,
                    defaults={
                        'source_type': field_data['data_source_type'],
                        'source_alias': field_data['field_source'],
                        'query_name': query_object,
                    }
                )
                if created:
                    import_result.append((field_source.source_alias, 'DataSource created'))
                    print(f"Field {field_source.source_alias} DataSource created")
                else:
                    import_result.append((field_source.source_alias, 'DataSource updated'))
                    print(f"Field {field_source.source_alias} DataSource updated")
            else:
                field_source = Source.objects.get(
                    source_union_list=source_list,
                    source_alias=field_data['field_source']
                )
        else:
            # field_source = None
            if not field_data['field_alias']:
                try:
                    field_source = Source.objects.get(
                        source_union_list=source_list
                    )
                except ObjectDoesNotExist:
                    field_source = None
                except MultipleObjectsReturned:
                    field_source = Source.objects.filter(source_union_list=source_list).first()
                except Exception as e:
                    import_result.append(f"Getting Source {source_list} error: {e}")
                    print(f"Getting Source {source_list} error: {e}")
            else:
                field_source = None

        if field_data['field_alias']:
            try:
                field, created = Field.objects.update_or_create(
                    field_list=field_list,
                    source_list=source_list,
                    field_alias=field_data['field_alias'] if field_data['field_alias'] else field_source,
                    field_source=field_source,
                    defaults={
                        'field_list': field_list,
                        'source_list': source_list,
                        'field_alias': field_data['field_alias'],
                        'field_source_type': field_data['field_source_type'],
                        # 'field_source': field_source,
                        'field_name': field_data['field_name'],
                        'field_value': field_data['field_value'],
                        'field_function': field_data['field_function'],
                        'function_field_list': field_data['function_field_list'],
                        'field_query_body': field_data['field_query_body'],
                        'field_description': field_data['field_description']
                    }
                )
            except Exception as e:
                import_result.append(f"Field alias {field_data['field_alias']} create or update error: {e}")
                print(f"Field alias {field_data['field_alias']} create or update error: {e}")
        else:
            processed_field_name = field_data['field_alias'] if field_data['field_alias'] else field_data[
                'function_field_list']
            if field_data['field_name']:
                try:
                    field, created = Field.objects.update_or_create(
                        field_list=field_list,
                        source_list=source_list,
                        field_name=field_data['field_name'],  # if field_data['field_name'] else processed_field_name,
                        field_source=field_source,
                        # field_source_type=field_data['field_source_type'],
                        defaults={
                            'field_list': field_list,
                            'source_list': source_list,
                            'field_alias': field_data['field_alias'],
                            'field_source_type': field_data['field_source_type'],
                            # 'field_source': field_source,
                            'field_name': field_data['field_name'] if field_data['field_name'] else processed_field_name,
                            'field_value': field_data['field_value'],
                            'field_function': field_data['field_function'],
                            'function_field_list': field_data['function_field_list'],
                            'field_query_body': field_data['field_query_body'],
                            'field_description': field_data['field_description']
                        }
                    )
                except Exception as e:
                    import_result.append(f"Field {processed_field_name} create or update error: {e}")
                    print(f"Field {processed_field_name} create or update error: {e}")
            else:
                try:
                    field, created = Field.objects.update_or_create(
                        field_list=field_list,
                        source_list=source_list,
                        field_alias=field_data['field_alias'] if field_data['field_alias'] else processed_field_name,
                        field_source=field_source,
                        # field_source_type=field_data['field_source_type'],
                        defaults={
                            'field_list': field_list,
                            'source_list': source_list,
                            # 'field_alias': field_data['field_alias'],
                            'field_source_type': field_data['field_source_type'],
                            # 'field_source': field_source,
                            'field_name': field_data['field_name'] if field_data['field_name'] else processed_field_name,
                            'field_value': field_data['field_value'],
                            'field_function': field_data['field_function'],
                            'function_field_list': field_data['function_field_list'],
                            'field_query_body': field_data['field_query_body'],
                            'field_description': field_data['field_description']
                        }
                    )
                except Exception as e:
                    import_result.append(f"Field {processed_field_name} create or update error: {e}")
                    print(f"Field {processed_field_name} create or update error: {e}")
        processed_field_name = field_data['field_alias'] if field_data['field_alias'] else field_data['field_name']
        if not field_data['field_alias'] and not field_data['field_name']:
            processed_field_name = field_data['function_field_list']
        if created:
            import_result.append((processed_field_name, 'Field created'))
            print(f"Field {processed_field_name} Field created")
        else:
            import_result.append((processed_field_name, 'Field updated'))
            print(f"Field {processed_field_name} Field updated")
    except Exception as e:
        import_result.append(f"Field {processed_field_name} create or update error: {e}")
        print(f"Field {processed_field_name} create or update error: {e}")

    return import_result


def process_source(source_data):
    """
    Creating data sources (Source) from JSON structure.
    """
    import_result = []
    try:
        source_union_list, created = SourceList.objects.get_or_create(source_list=source_data["source_union_list_name"])
        if created:
            import_result.append((source_data['source_union_list_name'], 'SourceList created'))
            print(f"SourceList {source_union_list.source_list} created")

        if source_data['source_type'] == 'query':
            table_name = None
            source_list = None
            source_system = None
            source_scheme = None
            # query_body = source_data['query_body']
            try:
                union_type = UnionType.objects.get(union_type=source_data['union_type'])
            except Exception as e:
                import_result.append(f"UnionType {source_data['union_type']} getting error: {e}")
                print(f"UnionType {source_data['union_type']} getting error: {e}")

            try:
                query_name, created = Query.objects.get_or_create(
                    query_name=source_data['source_name']
                )
                if created:
                    import_result.append((source_data['source_name'], 'Query created'))
                    print(f"Query {query_name.query_name} created")
                else:
                    import_result.append((source_data['source_name'], 'Query already exist'))
                    print(f"Query {query_name.query_name} already exist")
            except Exception as e:
                import_result.append(f"Query {source_data['source_name']} creation error: {e}")
                print(f"Query {source_data['source_name']} creation error: {e}")

        elif source_data['source_type'] == 'data_source':
            source_list = SourceList.objects.get(source_list=source_data['source_name'])
            query_name = None
            table_name = None
            source_system = None
            source_scheme = None
            union_type = UnionType.objects.get(union_type=source_data['union_type'])

        elif source_data['source_type'] == 'table':
            table_name = source_data['source_name']
            if source_data['source_system']:
                source_system, _ = SourceSystem.objects.get_or_create(
                    source_system_name=source_data['source_system'].upper())
            else:
                source_system = None
            if source_data['source_scheme']:
                source_scheme, _ = SourceScheme.objects.get_or_create(
                    source_scheme_name=source_data['source_scheme'].upper())
            else:
                source_scheme = None
            if source_data['union_type']:
                union_type, _ = UnionType.objects.get_or_create(union_type=source_data['union_type'].upper())
            else:
                union_type = None
            query_name = None
            source_list = None

        source_alias = source_data['source_alias'] if source_data['source_alias'] else source_data['source_name']
        source, created = Source.objects.update_or_create(
            source_union_list=source_union_list,
            source_alias=source_alias,
            source_type=source_data['source_type'],

            defaults={
                'query_name': query_name,
                'source_list': source_list,
                'table_name': table_name,
                'source_system': source_system,  # if source_system else None,
                'source_scheme': source_scheme,  # if source_scheme else None,
                'union_type': union_type,
                'union_condition': source_data['union_condition'],
                'source_description': source_data['source_description'],
                'query_body': source_data['source_query_body']
            }
        )
        processed_source_alias = source_data['source_alias'] if source_data['source_alias'] else source_data[
            'source_name']
        if created:
            import_result.append(f"{processed_source_alias} DataSource created")
            print(f"DataSource {processed_source_alias} created")
        else:
            import_result.append(f"{processed_source_alias} DataSource updated")
            print(f"DataSource {processed_source_alias} updated")

    except Exception as e:
        import_result.append(f"{source_data['source_alias']}: {e}")
        print(f"Error inserting data: {e}")

    return import_result


def create_report(query_name, report_name):
    """
    Fetch the Report with the highest version for a given report_name.
    If no such report exists, create a new one.
    """
    import_result = []
    try:
        report = Report.objects.get(report_name=report_name)
        if report:
            # current_query = report.report_query.query_name
            current_version = report.version
            # current_description = report.description
            current_change_description = report.change_description

            report.report_query = query_name
            report.report_description = query_name.query_description,
            report.version = str(float(current_version) + 1) if current_version else "1.0"
            report.change_description = f'{current_change_description}' \
                                        f'\n--------------------------------------------------------' \
                                        f'\n{now().strftime("%Y-%m-%d %H:%M:%S")}' \
                                        f'\nReport version: {report.version}' \
                                        f'\nReport description:{query_name.query_description}' \
                                        f'\nReport Query: {query_name.query_name}'
            report.change_date = now().strftime("%Y-%m-%d %H:%M:%S")
            # report.changed_by=changed_by_user

            report.save()
            import_result.append(f"Report {report_name} updated")

            return True, import_result

    except Report.DoesNotExist:
        # print("No report found")
        import_result.append(f"Report {report_name} does not exist. Trying to create a new.")
        try:
            report = Report.objects.create(report_name=report_name,
                                           report_query=query_name,
                                           version="1.0",
                                           report_description=query_name.query_description,
                                           change_description=f'{now().strftime("%Y-%m-%d %H:%M:%S")}'
                                                              f'\nInitial version'
                                                              f'\n{query_name.query_description}',
                                           change_date=now().strftime("%Y-%m-%d %H:%M:%S"),
                                           # changed_by=changed_by_user
                                           )
            if report:
                import_result.append(f"Report {report_name} created.")
                return True, import_result
        except Exception as e:
            import_result.append(f"Report {report_name} did not created: {e}")
            return False, import_result
    except Report.MultipleObjectsReturned:
        import_result.append(f"Report {report_name} did not created. Error: Multiple reports found!")
        return False, import_result
    except Exception as e:
        import_result.append(f"Report {report_name} did not created. Error: {e}")
        return False, import_result


def process_query(query_data, parent_query=None, query_json=None):
    """
    Recursive function for processing queries and their nesting.
    """
    import_result = []
    # Creating a SourceList for a query
    try:
        source_list, source_list_created = SourceList.objects.get_or_create(
            source_list=query_data["query_source"],
            defaults={'source_list_description': None}
        )
        if source_list_created:
            import_result.append((query_data['query_source'], 'SourceList created'))
            # print(f"Source {source_list.source_list} SourceList created")
        if source_list:
            # Creating a FieldList for a query
            field_list, field_list_created = FieldList.objects.get_or_create(
                field_list_name=query_data["query_fields"],
                data_source=SourceList.objects.get(id=source_list.id),
                defaults={'field_list_description': None}
            )
            if field_list_created:
                import_result.append((query_data['query_fields'], 'FieldList created'))

        # Creating a request
        query_name, created = Query.objects.update_or_create(
            query_name=query_data['query_name'],
            defaults={
                'field_list': field_list,
                'source_list': source_list,
                'query_conditions': query_data['query_conditions'],
                'query_alias': query_data['query_alias'],
                'query_description': query_data['query_description'],
                'query_body': query_data['query_body'],
                'query_json': query_json,
            }
        )
        if created:
            if query_data['report_name']:
                report_created, creation_result = create_report(query_name, query_data['report_name'])
                import_result.append(creation_result)
            import_result.append((query_data['query_name'], 'Query created'))
            print(f"Query {query_name.query_name} Query created")
        else:
            if query_data['report_name']:
                report_created, creation_result = create_report(query_name, query_data['report_name'])
                import_result.append(creation_result)
            import_result.append((query_data['query_name'], 'Query updated'))
            print(f"Query {query_name.query_name} Query updated")
    except Exception as e:
        import_result.append(f"Query {query_data['query_name']} creation error: {e}")
        print(f"Query {query_data['query_name']} creation error: {e}")

    # return import_result

    # ----------------------------------------------------------------
    #     query = Query.objects.create(
    #         query_name=query_data["query_name"],
    #         field_list=query_field_list,
    #         query_conditions=query_data.get("query_conditions"),
    #         query_description=query_data.get("query_description"),
    #         query_alias=query_data.get("query_alias"),
    #         source_list=SourceList.objects.get(source_list=query_data["query_source"]),
    #     )

    # Source processing
    for source in query_data.get("sources", []):
        # pass
        result = process_source(source)
        import_result.append(result)
        print(result)

    # Column processing
    for column in query_data.get("columns", []):
        # pass
        result = process_field_list(column)
        import_result.append(result)
        print(result)

    # Handling nested queries
    for nested_query in query_data.get("nested", []):
        if nested_query:
            result = process_query(nested_query, parent_query='query_name_')
        else:
            result = ("No nested query data found",)
        import_result.append(result)
        print(result)

    return import_result


# Basic processing process
def nested_queryies_load(nested_queries):
    query_import_result = []
    query_json = nested_queries
    cleaned_string = re.sub(r"\s+", " ", nested_queries).strip()
    json_data = json.loads(cleaned_string)
    try:
        for query in json_data.get("queries", []):
            result = process_query(query, None, query_json)
            query_import_result.append(result)
            # query_json = None
        return True, f"Imported successfully:<br>{query_import_result}"
    except Exception as e:
        return False, f"Nested query load error: {str(e)}"


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
