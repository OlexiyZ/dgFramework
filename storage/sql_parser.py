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

# report_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
# query_counter = 0  # Счетчик для генерации уникальных имен запросов
# query_description = ""
report_id = ""
with_names = {}


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
    # global query_description
    pattern = r"^/\*[\s\S]*?\*/"

    # Check if a multiline comment exists
    match = re.match(pattern, sql_text.strip())

    if match:
        query_description = match.group()
        # Remove the comment from the string
        sql_text = re.sub(pattern, "", sql_text.strip(), count=1).strip()
    else:
        query_description = None

    return sql_text, query_description


def define_query_conditions_1(param):
    """
    Defines query conditions based on provided parameters.
    """
    query_conditions = None
    open_parentheses = 0
    parentheses_match = list(re.finditer(r"\(|\)", param.strip(), re.IGNORECASE))
    if parentheses_match:
        for match in parentheses_match:
            if match.group() == "(":
                open_parentheses += 1
            elif match.group() == ")" and open_parentheses > 0:
                open_parentheses -= 1
            else:
                query_conditions = param[:match.start()+1].strip()
                return query_conditions
    else:
        query_conditions = param.strip()

    return query_conditions


def define_query_conditions(condition, position):
    """
    Defines query conditions based on provided parameters.
    """
    query_conditions = None
    open_parentheses = 0
    i = 0
    match = re.search(r"[()]", condition)
    if match:
        for char in condition:
            if char == "(":
                open_parentheses += 1
            elif char == ")":
                open_parentheses -= 1
                query_conditions = condition[:i - 1].strip()
                position = position + i
            elif open_parentheses < 0:
                # query_conditions = condition[:i-1].strip()
                return query_conditions, position
                break
            i += 1
        return query_conditions, position + len(condition)  # position + i
    else:
        query_conditions = condition.strip()

    return query_conditions, position + len(condition)


def extract_with_as_1(sql):
    """
    Витягує element1 та element2 з конструкції "WITH element1 AS (element2)",
    враховуючи вкладені дужки.
    """
    pattern = re.compile(r"\bWITH\s+(\w+)\s+AS\s+\((.+)\)", re.IGNORECASE | re.DOTALL)

    match = pattern.search(sql)
    if not match:
        return None, None

    element1 = match.group(1)
    element2 = match.group(2)

    # Виділення element2 з урахуванням вкладених дужок
    open_brackets = 1
    element2_final = ""
    for i, char in enumerate(element2):
        if char == "(":
            open_brackets += 1
        elif char == ")":
            open_brackets -= 1

        element2_final += char

        if open_brackets == 0:
            break  # Завершили зчитування element2

    return element1, element2_final.strip()


def extract_with_as(sql):
    """
    Визначає element_Alias, element_1, element_2, ..., element_N, element_Main
    у конструкціях "WITH element_Alias AS (element_1), AS (element_2), ..., AS (element_N) element_Main"
    та "WITH RECURSIVE element_Alias AS (element_1), ..., element_N element_Main".
    """

    # Шукаємо "WITH" або "WITH RECURSIVE", а потім alias CTE
    pattern = re.compile(r"\bWITH(?:\s+RECURSIVE)?\s+(\w+)\s+AS\s+\(", re.IGNORECASE)
    match = pattern.search(sql)

    if not match:
        return None, None, None, None

    element_Alias = match.group(1)  # Отримуємо головний alias CTE
    rest_text = sql[match.end():]  # .strip()  # Текст після "WITH element_Alias AS ("

    elements = []  # Тут зберігатимемо знайдені element_1, element_2, ..., element_N
    open_brackets = 1
    current_element = ""

    for i, char in enumerate(rest_text):
        if char == "(":
            open_brackets += 1
        elif char == ")":
            open_brackets -= 1

        current_element += char

        if open_brackets == 0:  # Знайшли закриту `)`
            elements.append(current_element.strip())  # Додаємо `element_N`
            current_element = ""  # Починаємо новий пошук

            # Перевіряємо, чи залишилося ще `, AS (`
            next_match = re.match(r",\s*AS\s+\(", rest_text[i+1:], re.IGNORECASE)
            if next_match:
                rest_text = rest_text[i+next_match.end()+1:]  # Перемикаємось на новий блок
                open_brackets = 1  # Починаємо новий підзапит
            else:
                element_Main = rest_text[i+1:]   #.strip()  # Остання частина після `)`
                FROM = match.end() - 1
                FROM_end = i+match.end()
                break

    # return element_Alias, elements, element_Main
    return element_Alias, FROM, FROM_end


def extract_with_as_all(sql):
    """
    Визначає alias_1, alias_2, ..., alias_N
    у конструкціях "WITH alias_1 AS (element_1), ..., alias_N AS (element_N) element_Main"
    та "WITH RECURSIVE alias_1 AS (element_1), ..., alias_N AS (element_N) element_Main".

    Identifies alias_1, alias_2, ..., alias_N
    in "WITH alias_1 AS (element_1), ..., alias_N AS (element_N) element_Main"
    and "WITH RECURSIVE alias_1 AS (element_1), ..., alias_N AS (element_N) element_Main".
    """

    # 1️⃣ Знаходимо "WITH" або "WITH RECURSIVE"  /  Find "WITH" or "WITH RECURSIVE"
    pattern = re.compile(r"\bWITH(?:\s+RECURSIVE)?\s+", re.IGNORECASE)
    match = pattern.search(sql)

    if not match:
        return None  # Якщо "WITH" не знайдено / If "WITH" is not found

    rest_text = sql[match.end():].strip()  # Текст після "WITH" / Text after "WITH"

    with_alias_tokens = []
    aliases = []  # Список alias_N  /  List of alias_N
    open_brackets = 0
    alias = None
    current_element = ""

    # 2️⃣ Перебираємо всі токени, шукаючи alias_N  /  Iterate through all tokens, searching for alias_N
    tokens = re.finditer(r"(\w+)\s+AS\s*\(|\(|\)|,", rest_text, re.IGNORECASE)

    for token in tokens:
        text = token.group()

        if " AS (" in text:
            if alias:
                aliases.append(alias)  # Додаємо знайдений alias  /  Add found alias
            alias = text.split(" AS (")[0].strip()  # Витягуємо alias  /  Extract alias
            if "AS " in token.group():
                with_alias_tokens.append(token)
            open_brackets = 1  # Починаємо підрахунок вкладених дужок  /  Start tracking nested brackets
        elif text == "(":
            open_brackets += 1
        elif text == ")":
            open_brackets -= 1
            if open_brackets == 0:
                aliases.append(alias)  # Додаємо останній alias  /  Add last alias
                alias = None
        elif text == "," and open_brackets == 0:
            continue

    return with_alias_tokens


def find_select_from_where(sql, unique_id, report_name):
    global with_names
    # global query_counter
    # report_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    global report_id
    report_id = unique_id
    # query_counter = None
    query_counter = 1
    sql, query_description = extract_query_description(sql)
    sql = query_cleaning(sql).strip()
    # lement_Alias, elements, element_Main = extract_with_as(sql)
    tokens = []
    stack = []  # Стек для отслеживания вложенных SELECT
    queries = []  # Список найденных SELECT-FROM-WHERE конструкций
    current_query = None
    # parentheses = False
    parentheses = 0

    # Find all "WITH" or "WITH RECURSIVE"
    with_pattern = re.compile(r"\bWITH(?:\s+RECURSIVE)?\s+(\w+)\s+AS\s*\(", re.IGNORECASE)
    with_matches = list(with_pattern.finditer(sql))  # Знаходимо всі входження

    tokens = list(re.finditer(r"^SELECT|\(SELECT|\bSELECT\b|\b SELECT \b|\bFROM\b|\bWHERE\b|;|\(|\)", sql, re.IGNORECASE))
    # Add with_matches to tokens
    tokens.extend(with_matches)
    # Sort tokens by span()[0] (starting index in the string)
    tokens.sort(key=lambda match: match.span()[0])

    for match in tokens:
        keyword = match.group().upper().strip()
        position = match.start()
        position_end = match.end()

        if "WITH" in keyword:
            if current_query:
                stack.append(current_query)
            # element_Alias, FROM, FROM_end = extract_with_as(sql[position:])
            element_Alias, FROM, FROM_end = extract_with_as(sql)
            with_names = {element_Alias: position}
            current_query = {
                "report_name": None,
                "query_name": f"Q_{report_id}_{position}",
                "SELECT": position,
                "SELECT_end": position_end - 2,
                "FROM": position_end - 1,
                "FROM_end": position_end - 1,
                "WHERE": None,
                "WHERE_end": None,
                "query_end": FROM_end,
                "query_fields": f"FL_{report_id}_{position}",
                "query_source": f"DS_{report_id}_{position}",
                "query_conditions": None,
                "query_alias": element_Alias,
                "query_description": None,
                "query_body": sql[FROM:FROM_end],
                "columns": [
                    {
                        "field_list": f"FL_{report_id}_{position}",
                        "source_list_name": f"DS_{report_id}_{position}",
                        "field_alias": None,
                        "field_source_type": "data_source",
                        "data_source_type": "table",
                        "field_source": None,
                        "field_name": "*",
                        "field_value": None,
                        "field_function": None,
                        "function_field_list": None,
                        "field_description": None,
                        "field_query_body": None
                    }
                ],
                "sources": [
                    {
                        "source_union_list_name": f"DS_{report_id}_{position}",
                        "source_alias": None,
                        "source_type": "query",
                        "source_name": f"Q_{report_id}_{position_end}",
                        "source_position": position_end,
                        "source_scheme": None,
                        "source_system": None,
                        "union_type": None,
                        "union_condition": None,
                        "source_description": None,
                        "source_query_body": None,
                    }
                ],
                "nested": []
            }
            query_description = None
            report_name = None

        elif keyword == "SELECT":  # or re.sub(r"[\s]+", "", keyword) == "(SELECT":
            query_counter = 0 if not query_counter else query_counter
            if current_query:
                stack.append(current_query)
            # query_counter += 1
            current_query = {
                "report_name": report_name if report_name else None,
                # "query_name": f"Q_{report_id}_{query_counter}",
                "query_name": f"Q_{report_id}_{position}" if query_counter != 0 else f"Q_{report_id}_main",
                "SELECT": position,
                "SELECT_end": position_end,
                "FROM": None,
                "FROM_end": None,
                "WHERE": None,
                "WHERE_end": None,
                "query_end": None,
                "query_fields": f"FL_{report_id}_{position}" if query_counter != 0 else f"FL_{report_id}_main",
                "query_source": f"DS_{report_id}_{position}" if query_counter != 0 else f"DS_{report_id}_main",
                "query_conditions": None,
                "query_alias": None,
                "query_description": query_description,
                "query_body": None,
                "columns": [],
                "sources": [],
                "nested": []
            }
            query_description = None
            report_name = None
            query_counter += 1

        elif "FROM" in keyword:  # elif keyword == "FROM":
            if current_query is None or (current_query is not None and current_query["FROM"] is None):
                current_query["FROM"] = position
                current_query["FROM_end"] = position_end + 1
                # Извлечение столбцов
                select_text = sql[current_query["SELECT"]:position].strip()
                field_list_name = current_query["query_fields"]
                source_list_name = current_query["query_source"]
                columns = extract_columns(select_text, current_query["SELECT_end"], field_list_name, source_list_name)
                current_query["columns"] = columns

                # Извлечение источников
                from_text, query_end = extract_from(sql, position)
                current_query["query_end"] = query_end if query_end else None
                current_query["query_body"] = sql[current_query["SELECT"]:query_end].strip() if query_end else None
                sources = extract_sources(from_text, current_query["FROM_end"], source_list_name)
                current_query["sources"] = sources

        elif keyword == "WHERE":
            if current_query and current_query["WHERE"] is None:
                current_query["WHERE"] = position
                current_query["WHERE_end"] = position_end
                query_conditions, query_end = define_query_conditions(sql[position_end:], position_end)
                # query_conditions = define_query_conditions_1(sql[position_end:])
                current_query["query_conditions"] = query_conditions if query_conditions else None
                current_query["query_end"] = query_end if query_end else None
                current_query["query_body"] = sql[current_query["SELECT"]:query_end].strip() if query_end else None


        elif re.sub(r"[\s]+", "", keyword) == "(SELECT":
            query_counter = 0 if not query_counter else query_counter
            if current_query:
                stack.append(current_query)
            # query_counter += 1
            select_position = position + 1
            current_query = {
                # "query_name": f"Q_{report_id}_{query_counter}",
                # "query_name": f"Q_{report_id}_{position}",
                "report_name": report_name if report_name else None,
                "query_name": f"Q_{report_id}_{select_position}" if query_counter != 0 else f"Q_{report_id}_main",
                "SELECT": select_position,  # position
                "SELECT_end": position_end,
                "FROM": None,
                "FROM_end": None,
                "WHERE": None,
                "WHERE_end": None,
                "query_end": None,
                # "query_fields": f"FL_{report_id}_{position}",
                # "query_source": f"DS_{report_id}_{position}",
                "query_fields": f"FL_{report_id}_{select_position}" if query_counter != 0 else f"FL_{report_id}_main",
                "query_source": f"DS_{report_id}_{select_position}" if query_counter != 0 else f"DS_{report_id}_main",
                "query_conditions": None,
                "query_alias": None,
                "query_description": query_description,
                "query_body": None,
                "columns": [],
                "sources": [],
                "nested": []
            }
            query_description = None
            report_name = None
            # parentheses = True
            query_counter += 1

        elif keyword == "(":
            # parentheses = True
            parentheses += 1
            # if current_query:
            #     stack.append(current_query)
            #     current_query = None

        elif keyword == ")":
            # if current_query and not parentheses:
            if current_query and parentheses <= 0:
                if stack:
                    parent_query = stack.pop()
                    parent_query["nested"].append(current_query)
                    current_query = parent_query
                else:
                    queries.append(current_query)
                    current_query = None
            else:
                # parentheses = False
                parentheses -= 1
        elif keyword == ";":
            if current_query:
                # Обработка незавершенного SELECT, если FROM не найден
                if current_query["FROM"] is None:
                    select_text = sql[current_query["SELECT"]:position].strip()
                    current_query["columns"] = extract_columns(select_text)
                if stack:
                    parent_query = stack.pop()
                    parent_query["nested"].append(current_query)
                    current_query = parent_query
                else:
                    queries.append(current_query)
                    current_query = None

    # Если остались незакрытые запросы
    if current_query:
        if stack:
            while stack:
                parent_query = stack.pop()
                parent_query["nested"].append(current_query)
                # current_query = parent_query
                queries.append(parent_query)
                current_query = None
        else:
            queries.append(current_query)
            current_query = None
    return {
        "queries": queries
    }


def find_max_fields_and_aliases(sql_text):
    """
    Функція знаходить всі поля, що використовуються у функції MAX та їх аліаси.
    The function identifies all fields used in the MAX function and their aliases.
    """
    pattern = re.compile(
        r"MAX\s*\((.*?)\)\s*(?:AS\s+(\w+)|(\w+))?",
        re.IGNORECASE | re.DOTALL
    )

    matches = pattern.findall(sql_text)
    fild_list = []
    # results = []

    for match in matches:
        field_content = match[0].strip()        # Поле всередині MAX(...)
        alias = match[1] or match[2] or None    # ALIAS через AS або пробіл

        # 📌 1. Якщо звичайне поле без складних виразів
        if re.match(r"^\w+(\.\w+)?$", field_content):
            fild_list.append(field_content)

        # 📌 2. Якщо арифметичний вираз (наприклад, salary + bonus)
        elif re.search(r"[\+\-\*/]", field_content):
            # Знаходимо всі поля в арифметичних виразах
            fields = re.findall(r"\b\w+\.\w+|\w+\b", field_content)
            unique_fields = list(set(fields))  # Унікальні значення
            # for field in unique_fields:
            #     results.append({"field": field, "alias": alias})
            fild_list = unique_fields

        # 📌 3. Якщо умовний вираз (CASE WHEN)
        elif re.search(r"\bCASE\b", field_content, re.IGNORECASE):
            case_fields = re.findall(r"\b(\w+\.\w+|\w+)\b", field_content)
            # for field in case_fields:
            #     results.append({"field": field, "alias": alias})
            fild_list = case_fields

        # 📌 4. Якщо інший складний вираз
        else:
            fild_list.append(field_content)

        if not alias:
            alias = "MAX_" + fild_list[0]
        fild_list = ", ".join(str(item) for item in fild_list)

    return fild_list, alias


def find_first_value_fields_and_aliases_1(sql_text):
    """
    Функція знаходить всі поля, що використовуються у функції FIRST_VALUE та їх аліаси.
    The function identifies all fields used in the FIRST_VALUE function and their aliases.
    """
    pattern = re.compile(
        r"FIRST_VALUE\s*\((.*?)\)\s*(?:AS\s+(\w+)|(\w+))?",
        re.IGNORECASE | re.DOTALL
    )

    matches = pattern.findall(sql_text)
    # results = []
    fild_list = []

    for match in matches:
        field_content = match[0].strip()        # Поле всередині FIRST_VALUE(...)
        alias = match[1] or match[2] or None    # ALIAS через AS або пробіл

        # 📌 1. Якщо звичайне поле без складних виразів
        if re.match(r"^\w+(\.\w+)?$", field_content):
            fild_list.append(field_content)

        # 📌 2. Якщо арифметичний вираз (наприклад, salary + bonus)
        elif re.search(r"[\+\-\*/]", field_content):
            # Знаходимо всі поля в арифметичних виразах
            fields = re.findall(r"\b\w+\.\w+|\w+\b", field_content)
            unique_fields = list(set(fields))  # Унікальні значення
            # for field in unique_fields:
            #     results.append({"field": field, "alias": alias})
            fild_list = unique_fields

        # 📌 3. Якщо умовний вираз (CASE WHEN)
        elif re.search(r"\bCASE\b", field_content, re.IGNORECASE):
            case_fields = re.findall(r"\b(\w+\.\w+|\w+)\b", field_content)
            # for field in case_fields:
            #     results.append({"field": field, "alias": alias})
            fild_list = case_fields

        # 📌 4. Якщо інший складний вираз
        else:
            fild_list.append(field_content)

        # if not alias:
        alias = "FIRST_VALUE_" + fild_list[0]
        fild_list = ", ".join(str(item) for item in fild_list)

    return fild_list, alias


def find_first_value_fields_and_aliases(sql_text):
    """
    Функція знаходить всі поля, що використовуються у функції FIRST_VALUE та їх аліаси.
    The function identifies all fields used in the FIRST_VALUE function and their aliases.
    """
    pattern = re.compile(
        r"FIRST_VALUE\s*\((.*?)\)\s*OVER\s*\(.*?ORDER BY\s+(.*?)\)\s*(?:AS\s+(\w+)|(\w+))?",
        re.IGNORECASE | re.DOTALL
    )

    matches = pattern.findall(sql_text)
    fild_list = []
    results = []

    for match in matches:
        first_value_field = match[0].strip()   # Поле всередині FIRST_VALUE(...)
        order_by_field = match[1].strip()      # Поле всередині ORDER BY
        alias = match[2] or match[3] or None   # ALIAS через AS або пробіл

        # 📌 Додаємо поле з FIRST_VALUE
        if first_value_field:
            # results.append({"field": first_value_field, "alias": alias})
            fild_list.append(first_value_field)

        # 📌 Додаємо поле з ORDER BY
        if order_by_field:
            # Можливість для декількох полів в ORDER BY
            order_by_fields = [f.strip() for f in order_by_field.split(",")]
            for field in order_by_fields:
                # results.append({"field": field, "alias": alias})
                fild_list.append(field)

        if not alias:
            alias = "FIRST_VALUE_" + fild_list[0]
        fild_list = ", ".join(str(item) for item in fild_list)

    return fild_list, alias


def define_function_params(sql_text):
    """
    Defines functions and parameters.
    """
    if "MAX" in sql_text:
        fild_list, alias = find_max_fields_and_aliases(sql_text)
        return "MAX", fild_list, alias

    elif "FIRST_VALUE" in sql_text:
        fild_list, alias = find_first_value_fields_and_aliases(sql_text)
        return "FIRST_VALUE", fild_list, alias

    else:
        return None, None, None


def extract_columns(select_text, select_position_end, field_list_name, source_list_name):
    """
    Extracts column names, aliases, and source aliases from a SELECT clause.
    Handles functions with parentheses and commas.
    """
    # select_text = re.sub(r"(?i)(\(SELECT)", r"", select_text, count=1).strip()
    select_text = re.sub(r"(?i)(\bSELECT\b)", "", select_text, count=1)  # .strip()

    position_counter = select_position_end + 1

    match_parenthesis = re.match(r"(?i)(^\()", select_text)  # .strip())
    if match_parenthesis:
        position_counter = select_position_end + len(match_parenthesis.group())
        select_text = re.sub(r"(?i)(^\()", "", select_text, count=1)  # .strip()

    match_distinct = re.search(r"(?i)(\bDISTINCT\s)", select_text)  # .strip())
    if match_distinct:
        position_counter = select_position_end + len(match_distinct.group()) + 1
        select_text = re.sub(r"(?i)(\bDISTINCT\s)", "", select_text, count=1)   # .strip()

    match_unique = re.search(r"(?i)(\bUNIQUE\s)", select_text)  # .strip())
    if match_unique:
        position_counter = select_position_end + len(match_unique.group()) + 1
        select_text = re.sub(r"(?i)(\bUNIQUE\s)", "", select_text, count=1)   # .strip()

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
                column = ''.join(current)  # .strip()
                # result.append((''.join(current).strip(), position_counter))
                result.append((column, position_counter - len(column)))   # + 1
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
            column = ''.join(current)  # .strip()
            result.append((column, position_counter - len(column)))  # + 1
        return result

    def define_function_fields(text):
        words_to_remove = ["NVL", "NVL2", "MAX", "CASE", "WHEN", "THEN", "END", "IN", "ELSE", "SELECT", "FROM", \
                           "WHERE", "BETWEEN", "AND", "OR", "MAX", "FIRST_VALUE", "IN", "OVER", "ORDER BY"]
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
        match = re.search(r"^(\bSELECT\b|\(\s*SELECT|\bCASE\b)", column_name.strip(), re.IGNORECASE)
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
                "field_description": None,
                "field_query_body": None
            }
        elif match and "SELECT" in match.group().upper():
            column_position = column_position + 1 if match.group(1) == "(SELECT" else column_position
            # column_position = column_position if match.group(1) == "(SELECT" else column_position
            return {
                "field_list": field_list_name,
                "source_list_name": source_list_name,
                "field_alias": alias.strip() if alias else None,
                "field_source_type": "data_source",
                "data_source_type": "query",
                "query_position": column_position,
                "field_source": source_alias.strip() if source_alias else f"Q_{report_id}_{column_position}",
                "field_name": None,
                "field_value": None,
                "field_function": None,
                "function_field_list": None,
                "field_description": None,
                "field_query_body": column_name[1:].strip() if column_name else None
            }
        elif '(' in column_name.strip() and ')' in column_name.strip():
            # If column_name has '(' and '}' symbols then define field as a function
            function_name, field_list, field_alias = define_function_params(column_name)
            if not function_name:
                field_list = define_function_fields(column_name.strip() if column_name else None)
            return {
                "field_list": field_list_name,
                "source_list_name": source_list_name,
                "field_alias": alias.strip() if alias else field_alias,
                "field_source_type": "function",
                "data_source_type": None,
                "field_source": source_alias.strip() if source_alias else None,
                "field_name": None,
                "field_value": None,
                "field_function": column_name.strip() if column_name else None,
                "function_field_list": field_list,
                "field_description": None,
                "field_query_body": None
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
                "function_field_list": None,
                "field_description": None,
                "field_query_body": None
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
                "function_field_list": None,
                "field_description": None,
                "field_query_body": None
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
            match_simple = re.match(r"^\s*(\w+)\s*\.\s*(\*|\w+)\s*$", col[0])
            if match_simple:
                alias = None
                source_alias, column_name = match_simple.groups()
                column_object = define_column_type(column_name, alias, source_alias, col[1])
                columns.append(column_object)
            else:
                alias = None
                source_alias = None
                column_name = col[0]
                column_object = define_column_type(column_name, alias, source_alias, col[1])
                columns.append(column_object)

    return columns


def extract_from(sql, from_position):
    """
    Извлечение текста после FROM.
    """
    stack_from = []
    # parentheses_from = False
    parentheses_from = 0
    current_from = None
    forms = []  # Список найденных WHERE конструкций
    from_text = sql[from_position:]
    first_from_match = re.match(r"^\s*FROM\b", from_text, re.IGNORECASE)
    first_from_start = first_from_match.start()
    first_from_end = first_from_match.end()

    from_text = from_text[first_from_end+1:]
    from_position = from_position + first_from_end + 1

    # stop_match = re.search(r"(\bWHERE\b|;|\(|\))", from_text, re.IGNORECASE)
    stop_match = list(re.finditer(r"(\bFROM\b|\bWHERE\b|;|\(|\))", from_text, re.IGNORECASE))
    # stop_match = list(re.finditer(r"\((SELECT.+)\)\s+(?:AS\s+)?(\w+)$)|(\bWHERE\b|;", from_text, re.IGNORECASE))

    for match in stop_match:
        keyword = match.group().upper()
        position = match.start()

        if keyword == "(":
            # if current_from and not parentheses_from:
            if current_from and parentheses_from <= 0:
                stack_from.append(current_from)
                current_from = from_text[position:]
                parentheses_from = True
            else:
                current_from = from_text[position:]

        elif keyword == ")":
            if current_from and parentheses_from <= 0:
                if stack_from:
                    parent_from = stack_from.pop()
                    current_from = parent_from
                else:
                    current_from = None
            else:
                # parentheses_from = False
                parentheses_from -= 1

        elif keyword in ("WHERE", ";", "FROM"):
            # if current_from and not parentheses_from:
            if current_from and parentheses_from <= 0:
                if stack_from:
                    parent_from = stack_from.pop()
                    current_from = parent_from
                else:
                    from_text = from_text[:position]
                    return from_text.strip(), from_position + position

        else:
            # parentheses_from = False
            parentheses_from -= 1

    # if stop_match:
    #     # from_text = from_text[:position]
    #     return from_text.strip()

    return from_text.strip(), from_position + len(from_text)


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
                    r"\bNATURAL JOIN\b|\bJOIN\b"
                ),
                source[0],
                re.IGNORECASE
            )
            if join_match:
                # union_type = ""
                # source_position = source[1] + len(source[2])+1 if len(source) > 2 else source[1]
                union_type = source[2] if len(source) > 2 and source[2] else "MAIN"
                current_source = (source[0][:join_match.start()], source[1], union_type)
                next_source = (source[0][join_match.end() + 1:], source[1] + join_match.end() + 1, join_match.group())
                source_list.insert(source_list.index(source) + 1, next_source)
                source_list[source_list.index(source)] = current_source
        return source_list

    source_definitions = split_coma_sources(from_text, from_position_end)
    source_definitions = split_join_sources(source_definitions)

    for source in source_definitions:  # .split(","):
        union_type = source[2] if len(source) > 2 and source[2] else "COMA"
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
        match_subquery = re.match(r"\(\s*SELECT\b", datasource.strip(), re.IGNORECASE)
        if match_subquery:
            # source_position = source[1] + len(union_type)+1 if union_type else source[1]
            source_position = source[1] + 1
            sources.append(
                {
                    "source_union_list_name": source_list_name,
                    "source_alias": alias.strip() if alias else None,
                    "source_type": "query",
                    # "source_name": datasource.strip() if datasource else None,
                    "source_name": f"Q_{report_id}_{source_position}",
                    "source_position": source_position,
                    "source_scheme": None,
                    "source_system": None,
                    "union_type": union_type.strip() if union_type else None,
                    "union_condition": condition.strip() if condition else None,
                    "source_description": None,
                    "source_query_body": source[0].strip() if source[0] else None,
                }
            )
        else:
            # Простые таблицы
            match = re.match(r"(?:(\w+)\.)?(\w+)(?:\s+(\w+))?", datasource.strip(), re.IGNORECASE)
            if match:
                schema = match.group(1).strip() if match.group(1) else match.group(1)  # Название схемы
                table = match.group(2).strip() if match.group(2) else match.group(2)  # Название таблицы
                # alias = match.group(3)   # Алиас

                if table in with_names:
                    source_type = "query"
                    source_position = with_names[table]
                    source_name = f"Q_{report_id}_{source_position}"
                else:
                    source_type = "table"
                    source_name = table if table else None
                    source_position = None

                sources.append({
                    "source_union_list_name": source_list_name,
                    "source_alias": alias.strip() if alias else None,
                    "source_type": source_type,
                    "source_name": source_name,   # table.strip() if table else None,
                    "source_position": source_position,
                    "source_scheme": schema if schema else None,
                    "source_system": None,
                    "union_type": union_type if union_type else None,
                    "union_condition": condition.strip() if condition else None,
                    "source_description": None,
                    "source_query_body": None,
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
    report_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    result = find_select_from_where(sql, report_id)

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
