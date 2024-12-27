# v11 - в функции extract_columns() добавляется парсиг столбцов с функциями - запятіми и кругліми скобками
import re
import json
import random
import string

sql = """
SELECT  
  kl.lookup_label as Business_Line,
  NVL(A1.field1, 0) AS qqq,
  A1.field2
FROM 
  (SELECT field1, field2 FROM business) A1,
  kyc_customer kc
  INNER JOIN kyc_customer_person kcp on kcp.customer_id = kc.id 
  INNER JOIN kyc_person_work_info kwi on kcp.person_id = kwi.kyc_person_id
  INNER JOIN kyc_lookup kl on kl.lookup_value = kwi.business_line
WHERE
  lookup_type = 'Business Line';
"""

report_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
query_counter = 0  # Счетчик для генерации уникальных имен запросов
query_description = ""


def query_cleaning(sql_text):
    """
    Removes single-line and multi-line comments from SQL text.
    """
    # Remove multi-line comments (/* ... */)
    sql_text = re.sub(r"/\*.*?\*/", "", sql_text, flags=re.DOTALL)
    # Remove single-line comments (-- ...)
    sql_text = re.sub(r"--.*?$", "", sql_text, flags=re.MULTILINE)
    # Таблиця символів для видалення
    # remove_chars = str.maketrans("", "", "\n\r\t")
    remove_chars = str.maketrans("\n\r\t", "   ", "")
    sql_text = sql_text.translate(remove_chars)
    # Замінити кілька пробільних символів одним пробілом
    sql_text = re.sub(r"\s+", " ", sql_text)
    # Видалити пробіли поряд з символами ( та )
    sql_text = sql_text.replace(" .", ".").replace("( ", "(").replace(" )", ")")
    # Remove extra whitespace and return cleaned SQL
    sql_text = sql_text.strip()

    return sql_text


def extract_query_description(sql_text):
    global query_description
    pattern = r"^/\*[\s\S]*?\*/"

    # Check if a multiline comment exists
    match = re.match(pattern, sql_text.strip())

    if match:
        query_description = match.group()
        # Remove the comment from the string
        sql_text = re.sub(pattern, "", sql_text.strip(), count=1).strip()

    return sql_text


def find_select_from_where(sql):
    global query_counter
    sql = extract_query_description(sql)
    sql = query_cleaning(sql).strip()
    tokens = []
    # tokens = list(re.finditer(r"(SELECT|FROM|WHERE|;|\(|\))", sql, re.IGNORECASE))
    # tokens = list(re.finditer(r"(SELECT|FROM|WHERE|;)", sql, re.IGNORECASE))
    # tokens = list(re.finditer(r"(\bSELECT\b|\bFROM\b|\bWHERE\b|;)", sql, re.IGNORECASE))
    # tokens = list(re.finditer(r"(\bSELECT\b|\bFROM\b|\bWHERE\b|;|\(\s*SELECT|\(|\))", sql, re.IGNORECASE))
    # tokens = list(re.finditer(r"\bFROM \(|\bFROM\b|\bSELECT\b|\bWHERE\b|;|\(\s*SELECT|\(|\)", sql, re.IGNORECASE))
    # tokens = list(re.finditer(r"\bFROM \(|\bFROM\b|\bSELECT\b|\bWHERE\b|;|\b\(SELECT\b|\(|\)", sql, re.IGNORECASE))
    # tokens = list(re.finditer(r"\bFROM \(|\bFROM\b|\b\(SELECT\b|\bSELECT\b|\bWHERE\b|;|\(|\)", sql, re.IGNORECASE))
    # tokens_p_select = list(re.finditer(r"\(SELECT", sql, re.IGNORECASE))
    # tokens_select_w = list(re.finditer(r"\b SELECT \b", sql, re.IGNORECASE))
    # tokens_select = list(re.finditer(r"^SELECT\b", sql, re.IGNORECASE))
    # tokens_from_p = list(re.finditer(r"\bFROM \(", sql, re.IGNORECASE))
    # tokens_from = list(re.finditer(r"\bFROM\b", sql, re.IGNORECASE))
    # tokens_where = list(re.finditer(r"\bWHERE\b", sql, re.IGNORECASE))
    # tokens_p = list(re.finditer(r";|\(|\)", sql, re.IGNORECASE))
    # tokens.append(tokens_p_select)
    stack = []  # Стек для отслеживания вложенных SELECT
    queries = []  # Список найденных SELECT-FROM-WHERE конструкций
    current_query = None
    parentheses = False

    # queries.append(
    #     {
    #         "query_description": query_description
    #     }
    # )

    tokens = list(re.finditer(r"^SELECT|\(SELECT|\b SELECT \b|\bFROM\b|\bWHERE\b|;|\(|\)", sql, re.IGNORECASE))

    for match in tokens:
        keyword = match.group().upper().strip()
        position = match.start()
        position_end = match.end()

        if keyword == "SELECT":  # or re.sub(r"[\s]+", "", keyword) == "(SELECT":
            if current_query:
                stack.append(current_query)
            query_counter += 1
            current_query = {
                "query_name": f"Q_{query_counter}_{report_id}",
                "SELECT": position,
                "SELECT_end": position_end,
                "FROM": None,
                "FROM_end": None,
                "WHERE": None,
                "WHERE_end": None,
                "query_fields": f"FL_{query_counter}_{report_id}",
                "query_source": f"DS_{query_counter}_{report_id}",
                "columns": [],
                "sources": [],
                "nested": []
            }

        elif "FROM" in keyword:  # elif keyword == "FROM":
            if current_query is None or (current_query is not None and current_query[
                "FROM"] is None):  # current_query and current_query["FROM"] is None
                current_query["FROM"] = position
                current_query["FROM_end"] = position_end + 1
                # Извлечение столбцов
                select_text = sql[current_query["SELECT"]:position].strip()
                field_list_name = current_query["query_fields"]
                source_list_name = current_query["query_source"]
                columns = extract_columns(select_text, current_query["SELECT_end"], field_list_name, source_list_name)
                current_query["columns"] = columns

                # Извлечение источников
                from_text = extract_from(sql, position)
                sources = extract_sources(from_text, current_query["FROM_end"], source_list_name)
                current_query["sources"] = sources

        elif keyword == "WHERE":
            if current_query and current_query["WHERE"] is None:
                current_query["WHERE"] = position
                current_query["WHERE_end"] = position_end

        elif re.sub(r"[\s]+", "", keyword) == "(SELECT":
            # if current_query:
            #     stack.append(current_query)
            #     current_query = None
            # parentheses = True
            if current_query:
                stack.append(current_query)
            query_counter += 1
            current_query = {
                "query_name": f"Q_{query_counter}_{report_id}",
                "SELECT": position,  # position+1
                "SELECT_end": position_end,
                "FROM": None,
                "FROM_end": None,
                "WHERE": None,
                "WHERE_end": None,
                "query_fields": f"FL_{query_counter}_{report_id}",
                "query_source": f"DS_{query_counter}_{report_id}",
                "columns": [],
                "sources": [],
                "nested": []
            }

        elif keyword == "(":
            parentheses = True
            # if current_query:
            #     stack.append(current_query)
            #     current_query = None

        elif keyword == ")":
            if current_query and not parentheses:
                if stack:
                    parent_query = stack.pop()
                    parent_query["nested"].append(current_query)
                    current_query = parent_query
                else:
                    queries.append(current_query)
                    current_query = None
            else:
                parentheses = False

        elif keyword == ";":
            if current_query:
                # Обработка незавершенного SELECT, если FROM не найден
                if current_query["FROM"] is None:
                    select_text = sql[current_query["SELECT"]:position].strip()
                    current_query["columns"] = extract_columns(select_text)
                queries.append(current_query)
                current_query = None

    # Если остались незакрытые запросы
    if current_query:
        # queries.append(current_query)
        if stack:
            parent_query = stack.pop()
            parent_query["nested"].append(current_query)
            current_query = parent_query
        else:
            queries.append(current_query)
            current_query = None
    return {
        "description": query_description,
        "queries": queries
    }


def extract_columns(select_text, select_position_end, field_list_name, source_list_name):
    """
    Extracts column names, aliases, and source aliases from a SELECT clause.
    Handles functions with parentheses and commas.
    """
    # select_text = re.sub(r"(?i)(\(SELECT)", r"", select_text, count=1).strip()
    select_text = re.sub(r"(?i)(\bSELECT\b)", "", select_text, count=1)  # .strip()

    position_counter = select_position_end + 1

    match_distinct = re.match(r"(?i)(^\()", select_text.strip())
    if match_distinct:
        position_counter = select_position_end + len(match_distinct.group())
        select_text = re.sub(r"(?i)(^\()", "", select_text, count=1)  # .strip()

    match_distinct = re.match(r"(?i)(\bDISTINCT\s)", select_text.strip())
    if match_distinct:
        position_counter = select_position_end + len(match_distinct.group()) + 1
        select_text = re.sub(r"(?i)(\bDISTINCT\s)", "", select_text, count=1).strip()

    columns = []

    # position_counter = select_position_end

    # Split columns by commas, ignoring commas inside parentheses
    def split_columns(text, position_counter):
        result = []
        current = []
        open_parentheses = 0
        # position_counter = select_position_end

        for char in text:
            if char == ',' and open_parentheses == 0:
                column = ''.join(current).strip()
                # result.append((''.join(current).strip(), position_counter))
                result.append((column, position_counter - len(column) + 1))
                current = []
            else:
                if char == '(':
                    open_parentheses += 1
                elif char == ')':
                    open_parentheses -= 1
                current.append(char)
            position_counter += 1
        # Add the last column
        if current:
            column = ''.join(current).strip()
            result.append((column, position_counter - len(column) + 1))
        return result

    def define_function_fields(text):
        words_to_remove = ["NVL", "NVL2", "MAX", "CASE", "WHEN", "THEN", "END", "IN", "ELSE", "SELECT", "FROM", \
                           "WHERE", "BETWEEN", "AND", "OR"]
        symbols_to_remove = ["(", ")"]

        for word in words_to_remove:
            text = re.sub(fr"\b{word}\b", ",", text, flags=re.IGNORECASE)
            # text = text.replace(word, "")

        for symbol in symbols_to_remove:
            text = text.replace(symbol, ",").strip()

        text = re.sub(r"^.*?=", "", text).strip()
        text = re.sub(r"\+", ",", text).strip()
        text = re.sub(r"=", "", text).strip()
        # text = re.sub(r"\d", "", text).strip()
        text = re.sub(r" ", "", text).strip()
        text = re.sub(r",,", ",", text).strip()
        text = re.sub(r",,", ",", text).strip()
        text = text.strip(",")

        return text

    # Define column types
    def define_column_type(column_name, alias, source_alias, column_position):
        match = re.search(r"(\bSELECT\b|\(\s*SELECT|\bCASE\b)", column_name.strip(), re.IGNORECASE)
        if match and match.group().upper() == "CASE":
            field_list = define_function_fields(column_name.strip() if column_name else None)
            return {
                "field_list": field_list_name,
                "source_list_name": source_list_name,
                "field_alias": alias.strip() if alias else None,
                "field_source_type": "function",
                "data_source_type": None,
                "field_source": source_alias.strip() if source_alias else None,
                "field_name": None,
                "field_value": None,
                "field_function": column_name.strip() if column_name else None,
                "function_field_list": field_list,
            }
        elif match and "SELECT" in match.group().upper():
            column_position = column_position - 1 if match.group(1) == "(SELECT" else column_position
            return {
                "field_list": field_list_name,
                "source_list_name": source_list_name,
                "field_alias": alias.strip() if alias else None,
                "field_source_type": "data_source",
                "data_source_type": "query",
                "query_position": column_position,
                "field_source": source_alias.strip() if source_alias else None,
                "field_name": column_name.strip() if column_name else None,
                "field_value": None,
                "field_function": None,
                "function_field_list": None
            }
        elif '(' in column_name.strip() and ')' in column_name.strip():
            field_list = define_function_fields(column_name.strip() if column_name else None)
            return {
                "field_list": field_list_name,
                "source_list_name": source_list_name,
                "field_alias": alias.strip() if alias else None,
                "field_source_type": "function",
                "data_source_type": None,
                "field_source": source_alias.strip() if source_alias else None,
                "field_name": None,
                "field_value": None,
                "field_function": column_name.strip() if column_name else None,
                "function_field_list": field_list,
            }
        elif column_name.strip().replace('.', '').isdigit() or column_name.strip().upper() == 'NULL' \
                or "'" in column_name.strip():  # or '"' in column_name.strip():  #  or ('(' not in column_name.strip() and ')' not in column_name.strip())
            return {
                "field_list": field_list_name,
                "source_list_name": source_list_name,
                "field_alias": alias.strip() if alias else None,
                "field_source_type": "value",
                "data_source_type": None,
                "field_source": source_alias.strip() if source_alias else None,
                "field_name": None,
                "field_value": column_name.strip() if column_name else None,
                "field_function": None,
                "function_field_list": None
            }
        else:
            return {
                "field_list": field_list_name,
                "source_list_name": source_list_name,
                "field_alias": alias.strip() if alias else None,
                "field_source_type": "data_source",
                "data_source_type": "table",
                "field_source": source_alias.strip() if source_alias else None,
                "field_name": column_name.strip() if column_name else None,
                "field_value": None,
                "field_function": None,
                "function_field_list": None
            }

    # Split the SELECT text into individual column definitions
    column_definitions = split_columns(select_text, position_counter)

    # Process each column definition
    for col in column_definitions:
        # Match column expressions with optional alias
        # match_function = re.match(r"(.+?)\s+(?:AS\s+)?(\w+)$", col, re.IGNORECASE)
        match_function = re.match(r"(.+?)\s+(?:AS\s+)?(\w+)$", col[0].strip(),
                                  flags=re.DOTALL | re.IGNORECASE)  # (.+)\s+AS\s+(\w+)$
        if match_function:
            column_expr = match_function.group(1).strip()
            alias = match_function.group(2)
            # column_expr, alias = match_function.groups()
            # Check for source alias in column expression
            match_source_alias = re.match(r"(?:(\w+)\.)?(.+)", column_expr.strip(), re.DOTALL)
            if match_source_alias:
                source_alias, column_name = match_source_alias.groups()
                column_object = define_column_type(column_name, alias, source_alias, col[1])
                columns.append(column_object)
        else:
            # Simple expression without alias
            match_simple = re.match(r"(?:(\w+)\.)?(.+)", col[0])
            if match_simple:
                alias = None
                source_alias, column_name = match_simple.groups()
                column_object = define_column_type(column_name, alias, source_alias, col[1])
                columns.append(column_object)

    return columns


def extract_from(sql, from_position):
    """
    Извлечение текста после FROM.
    """
    stack_from = []
    parentheses_from = False
    current_from = None
    forms = []  # Список найденных WHERE конструкций
    from_text = sql[from_position:]

    current_from = from_text
    # stop_match = re.search(r"(\bWHERE\b|;|\(|\))", from_text, re.IGNORECASE)
    stop_match = list(re.finditer(r"(\bWHERE\b|;|\(|\))", from_text, re.IGNORECASE))
    # stop_match = list(re.finditer(r"\((SELECT.+)\)\s+(?:AS\s+)?(\w+)$)|(\bWHERE\b|;", from_text, re.IGNORECASE))

    for match in stop_match:
        keyword = match.group().upper()
        position = match.start()

        if keyword == "(":
            if current_from and not parentheses_from:
                stack_from.append(current_from)
                current_from = from_text[position:]
                # current_from = {"query": "", "nested": []}   ???

                # current_query = from_text[:match.start()].strip()
                # queries.append(current_query)
                # current_query = ""
                parentheses_from = True
            else:
                current_from = from_text[position:]

        elif keyword == ")":  # and not parentheses_from:  # or keyword in ("WHERE", ";"):
            # from_text = from_text[:match.start()]    # 1
            # from_text = re.sub(r"(?i)(\bFROM\b)", "", from_text).strip()
            # return from_text.strip()   #1
            if current_from and not parentheses_from:
                if stack_from:
                    parent_from = stack_from.pop()
                    # parent_from["nested"].append(current_from)
                    current_from = parent_from
                else:
                    # forms.append(current_from.strip())
                    current_from = None
            else:
                parentheses_from = False

        elif keyword in ("WHERE", ";"):
            if current_from and not parentheses_from:
                if stack_from:
                    parent_from = stack_from.pop()
                    # parent_from["nested"].append(current_from)
                    current_from = parent_from
                else:
                    # queries.append(current_query)
                    # current_from = None
                    from_text = from_text[:position]
                    return from_text.strip()

        else:
            parentheses_from = False

    if stop_match:
        # from_text = from_text[:position]
        return from_text.strip()


def extract_sources(from_text, from_position_end, source_list_name):
    """
    Извлечение источников данных и их алиасов, включая подзапросы.
    """
    from_text = re.sub(r"(?i)\bFROM\b", "", from_text, count=1).strip()
    sources = []

    def split_coma_sources(text, from_position_end):
        result = []
        current = []
        open_parentheses = 0
        position_counter = from_position_end

        for char in text:
            if char == ',' and open_parentheses == 0:
                column = ''.join(current).strip()
                # result.append((''.join(current).strip(), position_counter))
                result.append((column, position_counter - len(column) + 1))
                current = []
            else:
                if char == '(':
                    open_parentheses += 1
                elif char == ')':
                    open_parentheses -= 1
                    if open_parentheses < 0:
                        break
                current.append(char)
            position_counter += 1
        # Add the last column
        if current:
            column = ''.join(current).strip()
            result.append((column, position_counter - len(column)))
        return result

    def split_join_sources(source_list):
        for source in source_list:
            join_match = re.search(
                (
                    r"\bUNION ALL\b|\bINNER JOIN\b|\bLEFT JOIN\b|\bLEFT OUTER JOIN\b|\bRIGHT JOIN\b|"
                    r"\bRIGHT OUTER JOIN\b|\bFULL JOIN\b|\bFULL OUTER JOIN\b|r\bCROSS JOIN\b|\bSELF JOIN\b|"
                    r"\bNATURAL JOIN\b"
                ),
                source[0],
                re.IGNORECASE
            )
            if join_match:
                # union_type = ""
                # source_position = source[1] + len(source[2])+1 if len(source) > 2 else source[1]
                union_type = source[2] if len(source) > 2 and source[2] else "main"
                current_source = (source[0][:join_match.start()], source[1], union_type)
                next_source = (source[0][join_match.end() + 1:], source[1] + join_match.end() + 1, join_match.group())
                source_list.insert(source_list.index(source) + 1, next_source)
                source_list[source_list.index(source)] = current_source
        return source_list

    source_definitions = split_coma_sources(from_text, from_position_end)
    source_definitions = split_join_sources(source_definitions)

    for source in source_definitions:  # .split(","):
        union_type = source[2] if len(source) > 2 and source[2] else "coma"
        # source = source[0].strip()
        # Датасорсы с алиасами и кондишинами
        match_condition = re.match(r"^(.*?)\s+(\w+)\s+ON\s+(.*)$", source[0].strip(), re.IGNORECASE)
        if match_condition:
            datasource, alias, condition = match_condition.groups()
        else:
            # Датасорсы с алиасами без кондишинов
            match_alias = re.match(r"^(.*?)\s+(\w+)$", source[0].strip(), re.IGNORECASE)
            if match_alias:
                datasource, alias = match_alias.groups()
                condition = None
            else:
                # Простые таблицы
                datasource = source[0].strip()
                alias = None
                condition = None
        # Подзапросы
        # match_subquery = re.match(r"\((SELECT.+)\)\s+(?:AS\s+)?(\w+)$", datasource.strip(), re.IGNORECASE)
        match_subquery = re.match(r"\(\s*SELECT\b", datasource.strip(), re.IGNORECASE)
        if match_subquery:
            # source_position = source[1] + len(union_type)+1 if union_type else source[1]
            sources.append(
                {
                    "source_union_list_name": source_list_name,
                    "source_alias": alias.strip() if alias else None,
                    "source_type": "query",
                    # "source_name": datasource.strip() if datasource else None,
                    "source_name": source[0],
                    "source_position": source[1],
                    "source_scheme": None,
                    "source_system": None,
                    "union_type": union_type.strip() if union_type else None,
                    "union_condition": condition.strip() if condition else None,
                    "source_description": None
                }
            )
        else:
            # Простые таблицы
            match = re.match(r"(?:(\w+)\.)?(\w+)(?:\s+(\w+))?", datasource.strip(), re.IGNORECASE)
            if match:
                schema = match.group(1)  # Название схемы
                table = match.group(2)  # Название таблицы
                # alias = match.group(3)   # Алиас
                sources.append({
                    "source_union_list_name": source_list_name,
                    "source_alias": alias.strip() if alias else None,
                    "source_type": "table",
                    "source_name": table.strip() if table else None,
                    # "source_position": source[1],
                    "source_scheme": schema.strip() if schema else None,
                    "source_system": None,
                    "union_type": union_type if union_type else None,
                    "union_condition": None,
                    "source_description": None
                })
            # else:
            #     # Если алиас не найден
            #     sources.append({"table": source, "alias": None})
    return sources


def queries_to_json(queries):
    def format_query(query):
        return {
            "name": query["name"],
            "SELECT": query["SELECT"],
            "SELECT_end": query["SELECT_END"],
            "FROM": query["FROM"],
            "FROM_end": query["FROM_end"],
            "WHERE": query["WHERE"],
            "WHERE_end": query["WHERE_end"],
            "columns": query["columns"],
            "sources": query["sources"],
            "nested": [format_query(nested_query) for nested_query in query["nested"]],
        }

    return [format_query(query) for query in queries]


# Основная программа
if __name__ == "__main__":
    try:
        with open("query4.sql", "r", encoding="utf-8") as file:
            sql = file.read()
    except FileNotFoundError:
        print("File not found!")
    except IOError:
        print("Error reading the file!")

    result = find_select_from_where(sql)

    # Преобразование результата в JSON
    if result:
        # qtj = queries_to_json(sql)
        # json_result = json.dumps(queries_to_json(result), indent=4)
        # json_result = json.dumps(result, indent=4)
        # print("Nested Queries in JSON Format:")
        # print(json_result)

        # Запись JSON в файл
        with open("nested_queries.json", "w", encoding="utf-8") as json_file:
            json.dump(result, json_file, indent=4, ensure_ascii=False)
        print("\nJSON записан в файл nested_queries.json.")
    else:
        print("\nNo queries found.")
