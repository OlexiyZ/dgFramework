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
with_names = {}  # dict of WITH datasource names and positions
main_query = {}  # report main query name and position


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


def compute_nesting_level(sql_script: str, pos: int) -> int:
    """
    Обчислює рівень вкладеності дужок у SQL‑скрипті до позиції pos.
    Computes the nesting level (number of open parentheses not yet closed) in the SQL script up to position pos.

    :param sql_script: Текст SQL‑скрипту / SQL script text.
    :param pos: Позиція, до якої обчислюється рівень вкладеності / position up to which to compute the nesting level.
    :return: Рівень вкладеності (ціле число) / the nesting level (integer).
    """
    level = 0
    in_quote = None
    i = 0
    while i < pos:
        ch = sql_script[i]
        if in_quote:
            if ch == in_quote:
                # Перевірка на подвійну лапку (escaped quote)
                # Check for an escaped quote.
                if i + 1 < pos and sql_script[i + 1] == in_quote:
                    i += 2
                    continue
                else:
                    in_quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_quote = ch
            i += 1
            continue
        if ch == '(':
            level += 1
        elif ch == ')':
            if level > 0:
                level -= 1
        i += 1
    return level


def parse_select_boundaries(sql_script: str, select_pos: int) -> dict:
    """
    Аналізує SQL‑скрипт і для конструкції SELECT (чи вкладеної конструкції (SELECT)
    визначає позиції:
      - select_start: початок конструкції SELECT
      - from_start: початок клаузи FROM, що належить цьому SELECT
      - where_start: початок клаузи WHERE (якщо є)
      - select_end: позиція закінчення всієї конструкції SELECT або (SELECT

    The function handles nested SELECT queries by tracking the parentheses nesting level and
    ignoring токени всередині вкладених конструкцій при пошуку ключових слів FROM і WHERE.

    :param sql_script: SQL‑скрипт (SQL script text)
    :param select_pos: Позиція початку ключового слова SELECT, для якого проводиться аналіз
                       (position of the SELECT keyword to be analyzed)
    :return: Словник з ключами:
             - "select_start": позиція початку SELECT,
             - "from_start": позиція початку FROM (якщо знайдено, інакше None),
             - "where_start": позиція початку WHERE (якщо знайдено, інакше None),
             - "select_end": позиція закінчення конструкції SELECT.
    """
    # Обчислюємо рівень вкладеності до початку SELECT (це дозволяє визначити, чи є SELECT вкладеним)
    starting_level = compute_nesting_level(sql_script, select_pos)
    result = {
        "select_start": select_pos,
        "from_start": None,
        "where_start": None,
        "select_end": None
    }
    pos = select_pos
    in_quote = None
    level = starting_level  # поточний рівень вкладеності
    while pos < len(sql_script):
        ch = sql_script[pos]

        # Якщо перебуваємо у лапках – пропускаємо вміст до їх закриття.
        # If inside a quoted string, skip until the closing quote.
        if in_quote:
            if ch == in_quote:
                # Перевірка на подвійну лапку (escaped quote)
                if pos + 1 < len(sql_script) and sql_script[pos + 1] == in_quote:
                    pos += 2
                    continue
                else:
                    in_quote = None
            pos += 1
            continue
        else:
            if ch in ("'", '"'):
                in_quote = ch
                pos += 1
                continue

        # Обробка дужок: збільшуємо або зменшуємо рівень вкладеності.
        # Handle parentheses: increase or decrease the nesting level.
        if ch == '(':
            level += 1
            pos += 1
            continue
        if ch == ')':
            # Якщо поточне закриття зменшує рівень нижче початкового,
            # це означає, що вкладена конструкція SELECT завершилася.
            # If the closing parenthesis reduces the level below the starting level,
            # it signals the end of the SELECT block.
            if level <= starting_level:
                result["select_end"] = pos
                return result
            else:
                level -= 1
                pos += 1
                continue

        # Якщо на верхньому рівні (тобто, level дорівнює starting_level)
        # перевіряємо на ключові слова.
        if level == starting_level:
            # Якщо зустріли символ ';' – припиняємо розбір (для головного SELECT).
            # If a semicolon is encountered at top level, consider it as the end of the SELECT block.
            if ch == ';':
                result["select_end"] = pos
                return result
            # Якщо символ є буквою, читаємо токен.
            if ch.isalpha():
                token_start = pos
                while pos < len(sql_script) and (sql_script[pos].isalnum() or sql_script[pos] == '_'):
                    pos += 1
                token = sql_script[token_start:pos]
                upper_token = token.upper()
                if upper_token == "FROM" and result["from_start"] is None:
                    result["from_start"] = token_start
                elif upper_token == "WHERE" and result["where_start"] is None:
                    result["where_start"] = token_start
                continue  # токен уже оброблено, продовжуємо цикл
        pos += 1

    # Якщо досягли кінця скрипта, встановлюємо select_end як останню позицію.
    result["select_end"] = pos
    return result


def parse_select_boundaries(sql_script: str, select_pos: int) -> dict:
    """
    Допоміжна функція для визначення меж повної конструкції SELECT.
    Determines the boundaries of a complete SELECT block starting at select_pos.

    :param sql_script: SQL‑скрипт.
    :param select_pos: Позиція першого символу "SELECT", що розбирається.
    :return: Словник з ключами:
             - "select_start": початкова позиція (select_pos)
             - "select_end": позиція, після якої завершується конструкція.
    """
    select_start = select_pos
    pos = select_pos
    level = 0
    in_quote = None
    while pos < len(sql_script):
        ch = sql_script[pos]
        # Обробка лапок
        if in_quote:
            if ch == in_quote:
                if pos + 1 < len(sql_script) and sql_script[pos + 1] == in_quote:
                    pos += 2
                    continue
                else:
                    in_quote = None
            pos += 1
            continue
        elif ch in ("'", '"'):
            in_quote = ch
            pos += 1
            continue
        # Обробка дужок
        if ch == '(':
            level += 1
        elif ch == ')':
            if level > 0:
                level -= 1
            else:
                break
        # При зустрічі символу ';' на рівні 0 – припиняємо розбір.
        if level == 0 and ch == ';':
            pos += 1
            break
        pos += 1
    return {"select_start": select_start, "select_end": pos}


def parse_sql_sources(sql_script: str, from_pos: int):
    """
    Функція для розбору (парсингу) джерел даних з клаузи FROM головного SELECT.
    Function to parse data sources from the main SELECT's FROM clause.

    Параметри (Parameters):
      sql_script : str
          SQL‑скрипт (SQL script string)
      from_pos : int
          Позиція першого символу 'FROM' основного SELECT
          (position of the first character of FROM in the main SELECT)

    Повертає (Returns):
      Список словників, де кожен містить:
         - 'operator': оператор об’єднання, що передує даному джерелу
           (якщо джерела розділено комою – "COMA", для першого – порожній рядок);
         - 'type': тип джерела – "table" або "query"
           (якщо після видалених пробілів починається з дужки або слова SELECT – "query", інакше – "table");
         - 'position': абсолютна позиція першого символу цього джерела (source_start);
         - 'source': текст виділеного джерела даних.
    """
    termination_keywords = {"WHERE", "GROUP", "ORDER", "HAVING", "LIMIT", "OFFSET"}
    join_keywords = {"JOIN", "INNER", "LEFT", "RIGHT", "FULL", "CROSS", "OUTER", "NATURAL", "UNION"}

    # Починаємо після "FROM"
    pos = from_pos + 4  # припускаємо, що from_pos вказує на "F" у "FROM"
    while pos < len(sql_script) and sql_script[pos].isspace():
        pos += 1

    results = []
    pending_operator = ""

    # Головний цикл розбору джерел із FROM‑клаузи
    while pos < len(sql_script):
        # Перевіряємо: якщо поточний символ не '(' і є буквою, читаємо токен.
        if pos < len(sql_script) and sql_script[pos] != '(' and sql_script[pos].isalpha():
            temp = pos
            while temp < len(sql_script) and sql_script[temp].isalnum():
                temp += 1
            token = sql_script[pos:temp].upper()
            # Якщо токен дорівнює SELECT:
            if token == "SELECT":
                # Якщо є попередній оператор об’єднання (будь-який із join_keywords)
                # тоді це початок нового джерела, яке є повною SELECT-конструкцією.
                if pending_operator:
                    bounds = parse_select_boundaries(sql_script, pos)
                    new_source = sql_script[pos:bounds["select_end"]]
                    results.append({
                        "operator": pending_operator,
                        "type": "query",
                        "position": pos,
                        "source": new_source.strip()
                    })
                    pos = bounds["select_end"]
                    pending_operator = ""
                    continue
                else:
                    # Якщо pending_operator порожній, це означає, що ми вже вийшли із секції FROM.
                    break

        # Пропускаємо пробіли
        while pos < len(sql_script) and sql_script[pos].isspace():
            pos += 1
        # Якщо зустрічаємо termination keyword на рівні 0 – завершуємо розбір FROM‑клаузи.
        if pos < len(sql_script) and sql_script[pos].isalpha():
            temp = pos
            while temp < len(sql_script) and sql_script[temp].isalnum():
                temp += 1
            token = sql_script[pos:temp].upper()
            if token in termination_keywords:
                break

        # Зчитуємо нове джерело даних
        source_start = pos
        current_source = ""
        level = 0
        in_quote = None
        operator_for_next = ""
        terminated = False
        delimiter_found = False

        # Внутрішній цикл – зчитування символів для поточного джерела
        while pos < len(sql_script):
            ch = sql_script[pos]
            # Обробка лапок
            if in_quote:
                current_source += ch
                if ch == in_quote:
                    if pos + 1 < len(sql_script) and sql_script[pos + 1] == in_quote:
                        current_source += in_quote
                        pos += 2
                        continue
                    else:
                        in_quote = None
                pos += 1
                continue
            elif ch in ("'", '"'):
                in_quote = ch
                current_source += ch
                pos += 1
                continue

            # Обробка дужок
            if ch == '(':
                level += 1
                current_source += ch
                pos += 1
                continue
            if ch == ')':
                if level > 0:
                    level -= 1
                    current_source += ch
                    pos += 1
                    continue
                else:
                    if not current_source.lstrip().startswith("("):
                        break
                    else:
                        current_source += ch
                        pos += 1
                        continue

            # Розділювачі аналізуємо лише на рівні 0
            if level == 0:
                if ch == ',':
                    operator_for_next = "COMA"
                    delimiter_found = True
                    pos += 1
                    break
                if ch.isalpha():
                    token_start = pos
                    token_end = pos
                    while token_end < len(sql_script) and sql_script[token_end].isalnum():
                        token_end += 1
                    word = sql_script[token_start:token_end].upper()
                    if word in termination_keywords:
                        terminated = True
                        break
                    if word in join_keywords:
                        operator_for_next = word
                        pos = token_end
                        while pos < len(sql_script) and sql_script[pos].isspace():
                            pos += 1
                        op_tokens = [word]
                        while pos < len(sql_script) and sql_script[pos].isalpha():
                            sub_token_start = pos
                            while pos < len(sql_script) and sql_script[pos].isalnum():
                                pos += 1
                            sub_word = sql_script[sub_token_start:pos].upper()
                            if sub_word in join_keywords or sub_word == "ALL":
                                op_tokens.append(sub_word)
                                while pos < len(sql_script) and sql_script[pos].isspace():
                                    pos += 1
                            else:
                                pos = sub_token_start
                                break
                        operator_for_next = " ".join(op_tokens)
                        delimiter_found = True
                        break
            current_source += ch
            pos += 1

        if terminated:
            if current_source.strip():
                results.append({
                    "operator": pending_operator,
                    "type": "query" if current_source.lstrip().upper().startswith(
                        "SELECT") or current_source.lstrip().startswith("(") else "table",
                    "position": source_start,
                    "source": current_source.strip()
                })
            break

        results.append({
            "operator": pending_operator,
            "type": "query" if current_source.lstrip().upper().startswith(
                "SELECT") or current_source.lstrip().startswith("(") else "table",
            "position": source_start,
            "source": current_source.strip()
        })
        pending_operator = operator_for_next if operator_for_next is not None else ""
        if not delimiter_found:
            break

    return results


def extracted_sources_definition(source_definitions, source_list_name):
    sources = []
    for source in source_definitions:
        union_type = source["operator"] if source["operator"] != '' else "MAIN"
        source_type = source["type"]
        source_position = source["position"]
        source_body = source["source"]

        # Датасорсы с алиасами и кондишинами
        match_condition = re.match(r"^(.*?)\s+(\w+)\s+ON\s+(.*)$", source_body.strip(), re.IGNORECASE)
        if match_condition:
            datasource, alias, condition = match_condition.groups()
        else:
            # Датасорсы с алиасами без кондишинов
            match_alias = re.match(r"^(.*?)\s+(\w+)$", source_body.strip(), re.IGNORECASE)
            if match_alias:
                datasource, alias = match_alias.groups()
                condition = None
            else:
                # Простые таблицы
                datasource = source["source"].strip()
                alias = None
                condition = None

        # Подзапросы
        if source_type == "query":
            # source_position = source[1] + 1
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
                    "source_query_body": source_body.strip() if source_body else None,
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
                    source_position = with_names[table][0]
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


# def define_with_sources(main_query_position):
#     global main_query, report_id, with_names
#     sources = []
#
#     for with_source in with_names:
#         alias = with_source
#         with_source_position = with_names[with_source][0]
#         with_source_body = with_names[with_source][1]
#         sources.append(
#             {
#                 "source_union_list_name": f"DS_{report_id}_{main_query_position}",
#                 "source_alias": alias.strip() if alias else None,
#                 "source_type": "query",
#                 "source_name": f"Q_{report_id}_{with_source_position}",
#                 "source_position": with_source_position,
#                 "source_scheme": None,
#                 "source_system": None,
#                 "union_type": "COMA",
#                 "union_condition": None,
#                 "source_description": None,
#                 "source_query_body": with_source_body,
#             }
#         )
#
#     return sources


def find_select_from_where(sql, unique_id, report_name):
    global with_names
    global main_query
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

    tokens = list(re.finditer(r"^SELECT|\(SELECT|\bSELECT\b|\bSELECT \b|\bFROM\b|\bWHERE\b|;|\(|\)", sql, re.IGNORECASE))
    # Add with_matches to tokens
    tokens.extend(with_matches)
    # Sort tokens by span()[0] (starting index in the string)
    tokens.sort(key=lambda match: match.span()[0])

    for match in tokens:
        keyword = match.group().upper()
        position = match.start()
        if keyword[0] == " ":
            position += 1
        position_end = match.end()

        if "WITH" in keyword:
            if current_query:
                stack.append(current_query)
            # element_Alias, FROM, FROM_end = extract_with_as(sql[position:])
            element_Alias, FROM, FROM_end = extract_with_as(sql)
            query_body = sql[FROM:FROM_end]
            with_names = {element_Alias: [position, query_body]}
            select_end_position = position_end - 2
            from_position = position_end - 1
            from_end_position = position_end - 1
            current_query = {
                "report_name": None,
                "query_name": f"Q_{report_id}_{position}",
                "SELECT": position,
                "SELECT_end": select_end_position,
                "FROM": from_position,
                "FROM_end": from_end_position,
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
                        "source_name": f"Q_{report_id}_{from_end_position}",
                        "source_position": from_end_position,
                        "source_scheme": None,
                        "source_system": None,
                        "union_type": "MAIN",
                        "union_condition": None,
                        "source_description": None,
                        "source_query_body": None,
                    }
                ],
                "nested": []
            }
            query_description = None
            with_main_query_position = current_query["query_end"] + 2
            main_query["name"] = f"Q_{report_id}_{with_main_query_position}"
            main_query["position"] = with_main_query_position
            # report_name = None

        elif keyword in ["SELECT", " SELECT", " SELECT "]:  # or re.sub(r"[\s]+", "", keyword) == "(SELECT":
            query_counter = 0 if not query_counter else query_counter
            if current_query:
                stack.append(current_query)
            query_name = f"Q_{report_id}_{position}"
            query_report_name = report_name if query_name == main_query["name"] else None
            # query_counter += 1
            current_query = {
                # "report_name": report_name if report_name else None,
                "report_name": query_report_name,
                # "query_name": f"Q_{report_id}_{position}" if query_counter != 0 else f"Q_{report_id}_main",
                "query_name": query_name,
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
            # report_name = None
            query_counter += 1

        elif "FROM" in keyword:  # elif keyword == "FROM":
            if current_query is None or (current_query is not None and current_query["FROM"] is None):
                current_query["FROM"] = position
                current_query["FROM_end"] = position_end + 1
                # Извлечение столбцов
                select_text = sql[current_query["SELECT"]:position].strip()
                field_list_name = current_query["query_fields"]
                source_list_name = current_query["query_source"]
                columns = extract_columns(select_text, current_query["SELECT"], field_list_name, source_list_name)
                current_query["columns"] = columns

                # Извлечение источников
                from_text, query_end = extract_from(sql, position)
                extracted_sources = parse_sql_sources(sql, position)
                sources = extracted_sources_definition(extracted_sources, source_list_name)

                # if current_query["query_name"] == main_query["name"] and with_names:
                    # with_sources = define_with_sources(main_query["position"])
                    # sources.extend(with_sources)
                    # with_names = {}

                current_query["query_end"] = query_end if query_end else None
                current_query["query_body"] = sql[current_query["SELECT"]:query_end].strip() if query_end else None
                current_query["sources"] = sources

        elif keyword == "WHERE":
            if current_query and current_query["WHERE"] is None:
                current_query["WHERE"] = position
                current_query["WHERE_end"] = position_end
                query_conditions, query_end = define_query_conditions(sql[position_end:], position_end)
                current_query["query_conditions"] = query_conditions if query_conditions else None
                current_query["query_end"] = query_end if query_end else None
                current_query["query_body"] = sql[current_query["SELECT"]:query_end].strip() if query_end else None


        elif re.sub(r"[\s]+", "", keyword) == "(SELECT":
            query_counter = 0 if not query_counter else query_counter
            if current_query:
                stack.append(current_query)
            # query_counter += 1
            query_name = f"Q_{report_id}_{position}"
            query_report_name = report_name if query_name == main_query["name"] else None
            select_position = position
            current_query = {
                # "report_name": report_name if report_name else None,
                "report_name": query_report_name,
                # "query_name": f"Q_{report_id}_{select_position}" if query_counter != 0 else f"Q_{report_id}_main",
                "query_name": query_name,
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
            # report_name = None
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


def find_decode_fields_and_aliases(sql_text):
    """
    Функція знаходить всі поля, що використовуються у функції DECODE та їх аліаси.
    The function identifies all fields used in the DECODE function and their aliases.
    """
    # 📌 Патерн для знаходження функцій DECODE з можливим аліасом
    pattern = re.compile(
        r"DECODE\s*\((.*?)\)\s*(?:AS\s+(\w+)|(\w+))?",
        re.IGNORECASE | re.DOTALL
    )

    matches = pattern.findall(sql_text)
    results = []
    fild_list = []

    for match in matches:
        decode_content = match[0].strip()          # Вміст всередині DECODE(...)
        alias = match[1] or match[2] or None        # ALIAS через AS або пробіл

        # 📌 Розділення аргументів функції DECODE
        args = [arg.strip() for arg in re.split(r",(?![^()]*\))", decode_content)]

        # 📌 Перший аргумент — це поле для декодування
        if args:
            field = args[0]
            # results.append({"field": field, "alias": alias})
            fild_list.append(field)

        # 📌 Обробка додаткових аргументів (умови та значення)
        for arg in args[1:]:
            if re.match(r"^\w+(\.\w+)?$", arg):  # Просте поле (наприклад, L.STATUS)
                fild_list.append(arg)

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

    elif "DECODE" in sql_text:
        fild_list, alias = find_decode_fields_and_aliases(sql_text)
        return "DECODE", fild_list, alias

    else:
        return None, None, None


def extract_columns(select_text, select_position, field_list_name, source_list_name):
    """
    Extracts column names, aliases, and source aliases from a SELECT clause.
    Handles functions with parentheses and commas.
    """
    position_counter = select_position

    match_select = re.search(r"(?i)^(\(SELECT\s)", select_text)  # .strip())
    if match_select:  # "(SELECT" in match_select.group(0):
        # position_counter = select_position_end + len(match_distinct.group()) + 1
        position_counter = position_counter + match_select.end()
        select_text = re.sub(r"(?i)(\(SELECT\s)", "", select_text, count=1)  # .strip()

    match_select = re.search(r"(?i)^(\bSELECT\s)", select_text)  # .strip())
    if match_select:  # "(SELECT" in match_select.group(0):
        # position_counter = select_position_end + len(match_distinct.group()) + 1
        position_counter = position_counter + match_select.end()
        select_text = re.sub(r"(?i)(\bSELECT\s)", "", select_text, count=1)  # .strip()

    # old select_text = re.sub(r"(?i)(\(SELECT)", r"", select_text, count=1).strip()
    # 020225 select_text = re.sub(r"(?i)(\bSELECT\b)", "", select_text, count=1)  # .strip()

    match_parenthesis = re.match(r"(?i)(^\()", select_text)  # .strip())
    if match_parenthesis:
        # position_counter = select_position_end + len(match_parenthesis.group())
        position_counter = position_counter + len(match_parenthesis.group())
        select_text = re.sub(r"(?i)(^\()", "", select_text, count=1)  # .strip()

    # match_distinct = re.search(r"(?i)(\bSELECT\s)", select_text)  # .strip())
    # if match_distinct:
    #     position_counter = select_position_end + len(match_distinct.group()) + 1
    #     select_text = re.sub(r"(?i)(\bSELECT\s)", "", select_text, count=1)  # .strip()

    match_distinct = re.search(r"(?i)^(\bDISTINCT\s)", select_text)  # .strip())
    if match_distinct:  # "DISTINCT" in match_distinct.group(0):
        # position_counter = select_position_end + len(match_distinct.group()) + 1
        # position_counter = position_counter + len(match_distinct.group()) + 1
        position_counter = position_counter + match_distinct.end()
        select_text = re.sub(r"(?i)(\bDISTINCT\s)", "", select_text, count=1)   # .strip()

    match_unique = re.search(r"(?i)^(\bUNIQUE\s)", select_text)  # .strip())
    if match_unique:  # "UNIQUE" in match_unique.group(0):
        # position_counter = select_position_end + len(match_unique.group()) + 1
        position_counter = position_counter + match_unique.end()
        select_text = re.sub(r"(?i)(\bUNIQUE\s)", "", select_text, count=1)   # .strip()

    columns = []

    # position_counter = select_position_end

    # Split columns by commas, ignoring commas inside parentheses
    def split_columns(text, position_counter):
        result = []
        current = []
        open_parentheses = 0
        coma = 0
        # position_counter = select_position_end

        for char in text:
            if char == ',' and open_parentheses == 0:
                coma = 1
                column = ''.join(current)  # .strip()
                # result.append((''.join(current).strip(), position_counter))
                result.append((column, position_counter - len(column)))
                current = []
            elif char == ' ' and coma == 1:
                pass  # skip a ' ' character
            else:
                coma = 0
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
            column_detected_position = column_position
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
                "field_query_body": None,
                "field_position": column_detected_position if column_detected_position else None
            }
        elif match and "SELECT" in match.group().upper():
            # column_detected_position = column_position
            # column_position = column_position + 1 if match.group(1) == "(SELECT" else column_position
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
                "field_query_body": column_name if column_name else None,
                "field_position": column_position if column_position else None
            }
        elif '(' in column_name.strip() and ')' in column_name.strip():
            column_detected_position = column_position
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
                "field_query_body": None,
                "field_position": column_detected_position if column_detected_position else None
            }
        elif column_name.strip().replace('.', '').isdigit() or column_name.strip().upper() == 'NULL' \
                or "'" in column_name.strip():  # or '"' in column_name.strip():  #  or ('(' not in column_name.strip() and ')' not in column_name.strip())
            column_detected_position = column_position
            return {
                "field_list": field_list_name,
                "source_list_name": source_list_name,
                "field_alias": alias.strip() if alias else column_name,
                "field_source_type": "value",
                "data_source_type": None,
                "field_source": source_alias.strip() if source_alias else None,
                "field_name": None,
                "field_value": column_name.strip() if column_name else None,
                "field_function": None,
                "function_field_list": None,
                "field_description": None,
                "field_query_body": None,
                "field_position": column_detected_position if column_detected_position else None
            }
        else:
            column_detected_position = column_position
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
                "field_query_body": None,
                "field_position": column_detected_position if column_detected_position else None
            }

    # Split the SELECT text into individual column definitions
    column_definitions = split_columns(select_text, position_counter)

    # Process each column definition
    for col in column_definitions:
        # Match column expressions with optional alias
        # col[0] is the column, col[1] is the column_position
        # match_function = re.match(r"(.+?)\s+(?:AS\s+)?(\w+)$", col, re.IGNORECASE)
        match_alias = re.match(r"(.+?)\s+(?:AS\s+)?(\w+)$", col[0].strip(),
                                  flags=re.DOTALL | re.IGNORECASE)  # (.+)\s+AS\s+(\w+)$
        if match_alias:
            column_expr = match_alias.group(1).strip()
            alias = match_alias.group(2)
            # column_expr, alias = match_function.groups()
            # Check for source alias in column expression
            if column_expr[0] != "(" and column_expr[-1] != ")":
                match_source_alias = re.match(r"(?:(\w+)\.)?(.+)", column_expr, re.DOTALL)
                if match_source_alias:
                    source_alias, column_name = match_source_alias.groups()
                    column_object = define_column_type(column_name, alias, source_alias, col[1])
                    columns.append(column_object)
            else:
                source_alias = None
                column_name = column_expr
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
