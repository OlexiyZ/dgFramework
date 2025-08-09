from django.shortcuts import render, redirect
import requests
from django.http import HttpResponse, HttpRequest, JsonResponse, Http404, FileResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from openpyxl import load_workbook
import json
import pandas as pd
import psycopg2
from django.core.files.storage import FileSystemStorage
import os
from .models import *
from django.core.management import call_command
from datetime import datetime
import glob
from .sql_parser import find_select_from_where
from .query_load import nested_queryies_load
import random
import string
# from mozilla_django_oidc.views import OIDCAuthenticationCallbackView
from django.contrib.auth import login
import jwt
from jwt import PyJWKClient, ExpiredSignatureError, InvalidTokenError
from django.contrib.auth.models import User
from django.conf import settings
import platform

wb = None


# def validate_token_and_get_user(token):
#     pass
#
#
# def oidc_login_view(request):
#     token = request.POST.get('token')
#     user = validate_token_and_get_user(token)  # ваша функція валідації токена
#     if user is None:
#         return JsonResponse({'error': 'Invalid token'}, status=400)
#     login(request, user)  # створюється сесія
#     return JsonResponse({'redirect': '/admin/'})


# Налаштування Okta
OKTA_DOMAIN = settings.OKTA_DOMAIN
CLIENT_ID = settings.CLIENT_ID
JWKS_URL = settings.JWKS_URL
PROXY_HOST = settings.PROXY_HOST
okta_access_token = ""

# OKTA_DOMAIN = "https://dev-24630760.okta.com"  # замініть на свій Okta domain
#! OKTA_DOMAIN = "https://dev-04812975.okta.com/"
#! BANK_OKTA_DOMAIN ="https://eu-bankaletihad.okta.com"
# # CLIENT_ID = "0oanssrjqw0KXnJuH5d7"  # замініть на свій Client ID
#! CLIENT_ID = "0oalk1pa5nk7rvIGq5d7"
#! BANK_CLIENT_ID = "0oanqdcd6k9nLoAp9417"
# JWKS_URL = f"{OKTA_DOMAIN}/oauth2/default/v1/keys"  # Endpoints для отримання ключів
#! JWKS_URL = f"{OKTA_DOMAIN}/oauth2/v1/keys"


def send_roles(request):
    proxy_host = settings.PROXY_HOST
    username = request.user.username
    try:
        user = OktaUser.objects.get(username=username)
        access_token = user.access_token
    except OktaUser.DoesNotExist:
        return None

    # Контекст для передачі в шаблон
    context = {
        'auth_token': access_token,
        'proxy_host': proxy_host,
    }
    # context = {
    #     'clientId': request.session.get('clientId', ''),
    #     'id_token': request.session.get('id_token', ''),
    #     'access_token': request.session.get('access_token', ''),
    #     'proxy_host': request.session.get('proxy_host', ''),
    # }
    return render(request, 'send_roles.html', context)


def check_role(request):
    proxy_host = settings.PROXY_HOST
    username = request.user.username
    try:
        user = OktaUser.objects.get(username=username)
        access_token = user.access_token
    except OktaUser.DoesNotExist:
        return None

    # Контекст для передачі в шаблон
    context = {
        'auth_token': access_token,
        'proxy_host': proxy_host,
    }

    return render(request, 'check_role.html', context)


def get_public_key():
    """
    Отримує публічний ключ JWKS для перевірки підпису токенів.
    """
    jwks_client = PyJWKClient(JWKS_URL)
    return jwks_client


def validate_id_token(id_token):
    """
    Перевіряє підпис, термін дії, issuer і аудиторію id_token.
    """
    try:
        # Отримуємо список ключів Okta
        jwks_client = get_public_key()

        # Отримуємо заголовок токена для визначення ключа
        header = jwt.get_unverified_header(id_token)
        signing_key = jwks_client.get_signing_key(header["kid"]).key

        # Декодуємо та перевіряємо токен
        decoded = jwt.decode(
            id_token,
            signing_key,
            algorithms=["RS256"],
            audience=CLIENT_ID,  # Має відповідати Client ID
            issuer=f"{OKTA_DOMAIN}/oauth2/default",  # Має відповідати issuer
        )
        return decoded  # Повертаємо декодований токен, якщо він валідний

    except ExpiredSignatureError:
        return {"error": "Token has expired"}
    except InvalidTokenError as e:
        return {"error": str(e)}


def login_page(request):
    """
    Сторінка, де клієнт запускає аутентифікацію через Okta.
    """
    if platform.system() == "Windows":
        redirect_uri = "http://localhost:8000/storage/login/"
        issuer = f"{OKTA_DOMAIN}"  # /oauth2/default"
    else:
        redirect_uri = "https://datagov.baelab.net/storage/login/"
        issuer = f"{OKTA_DOMAIN}"  # /oauth2/default"
        # issuer = f"{OKTA_DOMAIN}/oauth2/v1/authorize"
    context = {
        "issuer": issuer,  # OKTA_DOMAIN,  # + "oauth2",     # "oauth2/default",
        "clientId": CLIENT_ID,
        "redirectUri": redirect_uri
    }
    return render(request, 'storage/login.html', context)


def get_user_info(token):
    token = token  # request.GET.get('token')
    iss = OKTA_DOMAIN  # request.GET.get('iss')

    if not token or not iss:
        return HttpResponseBadRequest("Token або issuer не надані.")

    # Формуємо URL для запиту
    url = f"{iss}/oauth2/v1/userinfo"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Виконуємо GET-запит до OAuth2 сервісу
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        user_info = response.json()
        return JsonResponse(user_info)
    else:
        return JsonResponse(
            {"error": "Не вдалося отримати інформацію про користувача", "status": response.status_code},
            status=response.status_code
        )


@csrf_exempt
def oidc_login(request):
    """
    Приймає POST-запит із access_token та id_token, перевіряє підпис
    та створює/оновлює користувача в Django.
    """
    global access_token

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            id_token = data.get('id_token')
            access_token = data.get('access_token')
            # username = request.user.username
            # print(f"Username: {username}")

            if not id_token:
                return JsonResponse({'error': 'ID Token is missing'}, status=400)

            # Валідація id_token
            decoded_token = get_user_info(access_token)
            # decoded_token = validate_id_token(id_token)

            if "error" in decoded_token:
                return JsonResponse({'error': decoded_token["error"]}, status=400)

            # Отримуємо email з токена
            json_str = decoded_token.content.decode('utf-8')
            user_info = json.loads(json_str)
            email = user_info.get('email', 'unknown@example.com')
            username = email  # Використовуємо email як username

            # Отримуємо або створюємо користувача
            user, created = User.objects.get_or_create(username=username, defaults={'email': email})

            if created:
                # Робимо користувача staff, якщо потрібно (щоб він мав доступ до admin panel)
                user.is_staff = True
                user.save()

            # Зберігаємо токени у сесії
            request.session['clientId'] = CLIENT_ID
            request.session['id_token'] = id_token
            request.session['access_token'] = access_token
            request.session.modified = True  # Повідомляємо Django, що сесію змінено
            # request.session.save()  # Примусове збереження сесії
            print("Session Data:", request.session.items())  # Друкуємо сесію у консоль

            # Логуємо користувача у Django (створюється сесія)
            login(request, user)

            username = request.user.username
            if username and access_token:
                user, created = OktaUser.objects.update_or_create(
                    username=username,
                    defaults={'access_token': access_token}
                )
                if created:
                    print(f"Created new user: {username}")
                else:
                    print(f"Updated token for user: {username}")

            # request.session.modified = True  # Повідомляємо Django, що сесію змінено
            # request.session.save()  # Примусове збереження сесії

            # return JsonResponse({'redirect': '/admin/'})
            return JsonResponse({'redirect': '/'})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'POST method required'}, status=400)


# Create your views here.
# @csrf_exempt
def excelImport(request: HttpRequest):
    context = {
        "text": "Excel Import!!!"
    }
    return render(request, 'storage/excelimport.html', context)


@csrf_exempt
# @require_POST
def upload_file(request):
    global wb
    # context = {'message': 'Файл успешно загружен'}
    context = {}
    if request.FILES.get('excelFile'):
        file = request.FILES.get('excelFile')
        if not file:
            return JsonResponse({'error': 'No file to download'}, status=400)

        # Здесь вы можете обрабатывать файл, например, сохранять его на сервере
        fss = FileSystemStorage()
        filename = fss.save(file.name, file)
        # file_url = fss.url(filename)
        file_path = fss.path(filename)
        context = {'message': 'File uploaded successfully', 'file_path': file_path}
        wb = load_workbook(file)

        sheets = dict()
        # Adding items to Listbox
        for sheet_item in wb.worksheets:
            tables = []
            sheet_title = sheet_item.title
            # sheets.append(sheet_title)
            selected_sheet = wb[sheet_title]
            for table_item in selected_sheet.tables:
                tables.append(table_item)
            sheets[sheet_title] = tables

        context['sheets'] = sheets
        # return JsonResponse(sheets)
        return JsonResponse(context)

    return render(request, 'storage/excelimport.html', context)


def select_table(request):
    global wb
    print('wb type: ', type(wb))
    if request.method == 'POST':
        sheet_name = request.POST.get('sheet')
        table_name = request.POST.get('table')
        selected_sheet = wb[sheet_name]
        lookup_table = selected_sheet.tables[table_name]
        data = selected_sheet[lookup_table.ref]
        rows_list = []

        for row in data:
            cols = []
            # print(type(row), '\n')
            for col in row:
                cols.append(col.value)
            rows_list.append(cols)

        df = pd.DataFrame(data=rows_list[1:], index=None, columns=rows_list[0])
        df.to_csv(f'{sheet_name}-{table_name}.csv', index=False)

        data_rows = df.to_dict(orient='records')
        column_names = df.columns.tolist()
        context = {'column_names': column_names, 'data_rows': data_rows}
        return render(request, 'storage/table_display.html', context)
    else:
        return HttpResponse("Method not allowed", status=405)


def sanitize_for_import(value):
    if isinstance(value, str):
        escaped_value = value.replace("'", "''")
        return escaped_value
    elif isinstance(value, list):
        value_list = json.dumps(value)
        return value_list
    elif isinstance(value, dict):
        str_value = str(value)
        escaped_value = str_value.replace("'", '"')
        return escaped_value
    elif isinstance(value, set):
        str_value = str(value)
        escaped_value = str_value.replace("'", "''")
        return escaped_value
    elif not value:
        escaped_value = None
        return escaped_value
    else:
        return value


def load2db(self, df):
    def __sanitize_for_sql(value):
        if isinstance(value, str):
            escaped_value = value.replace("'", "''")
            return escaped_value
        elif isinstance(value, list):
            value_list = json.dumps(value)
            return value_list
        elif isinstance(value, dict):
            str_value = str(value)
            escaped_value = str_value.replace("'", '"')
            return escaped_value
        elif isinstance(value, set):
            str_value = str(value)
            escaped_value = str_value.replace("'", "''")
            return escaped_value
        else:
            return value

    # Establish a connection to the PostgreSQL database:
    dbname = "dg_bae"
    user = "postgres"
    password = "postgres"
    host = "localhost"
    port = "5432"

    connection = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )

    connection.autocommit = True
    cursor = connection.cursor()

    try:
        # Populate rows
        for _, row in df.iterrows():
            query = f"""INSERT INTO storage_field (
                    field_list_id, 
                    source_list_id, 
                    field_alias, 
                    field_source_type, 
                    field_source_id,
                    field_name, 
                    field_value, 
                    field_function, 
                    function_field_list, 
                    field_description) 
                    VALUES (
                        (select id 
                        from storage_fieldlist 
                        where field_list_name like '{row['field_list']}'),
                    
                        COALESCE((select id 
                        from storage_sourcelist 
                        where source_list_name like '{row['source_list']}'), NULL),
                    
                        '{row['field_alias']}', 
                        '{row['field_source_type']}', 
                    
                        COALESCE((select id
                        from storage_source 
                        where source_alias like '{row['field_source']}' and source_union_list_name_id = (select id 
                        from storage_sourcelist 
                        where source_list_name like '{row['source_list']}')), NULL), 
                    
                        '{row['field_name']}', 
                        '{row['field_value']}', 
                        '{__sanitize_for_sql(row['field_function'])}', 
                        '{row['function_field_list']}', 
                        '{row['field_description']}'
                    );"""

            cursor.execute(query)
            # connection.commit()
        print("Data inserted successfully")
    except Exception as e:
        print(f"Error inserting data: {e}")

        cursor.close()
        connection.close()


@csrf_exempt
def import_excel(request):
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)

    sheet = body_data.get('sheet')
    table = body_data.get('table')
    file_path = body_data.get('file_path')

    # print("Request data: ", request.body)
    # print("Request file_url: ", request.body['file_url'])
    df = import_table_from_excel(file_path, sheet, table)
    df_dict = df.to_dict(orient='records')
    context = {'text': 'CSV Loaded', 'csv': df_dict}
    return JsonResponse(context)
    # return render(request, 'storage/import_csv.html', context)
    # return redirect('import_csv.html', context)


@csrf_exempt
def import_csv(request):
    body_unicode = request.body.decode('utf-8')
    body_data = json.loads(body_unicode)

    sheet = body_data.get('sheet')
    table = body_data.get('table')
    file_path = body_data.get('file_path')

    df = import_table_from_excel(file_path, sheet, table)

    import_result = []
    if table[:3] == 'FL_':
        for index, row in df.iterrows():
            try:
                source_list, created = SourceList.objects.get_or_create(source_list=row['source_list'])
                if created:
                    import_result.append((row['source_list'], 'SourceList created'))
                    print(f"Field {source_list.source_list} SourceList created")

                field_list, created = FieldList.objects.get_or_create(field_list_name=row['field_list'],
                                                                      data_source=source_list)
                if created:
                    import_result.append((row['field_list'], 'FieldList created'))
                    print(f"Field {field_list.field_list_name} FieldList created")

                if row['field_source']:
                    field_source = Source.objects.get(source_union_list=source_list, source_alias=row['field_source'])
                else:
                    field_source = None
                # sanitized_field_name = sanitize_for_import(row['field_name'])
                # sanitized_field_value = sanitize_for_import(row['field_value'])
                # sanitized_field_function = sanitize_for_import(row['field_function'])
                # sanitized_function_field_list = sanitize_for_import(row['function_field_list'])
                # sanitized_field_description = sanitize_for_import(row['field_description'])

                if row['field_alias']:
                    field, created = Field.objects.update_or_create(
                        field_list=field_list,
                        source_list=source_list,
                        field_alias=row['field_alias'],
                        # field_source=field_source,
                        defaults={
                            'field_list': field_list,
                            'source_list': source_list,
                            'field_alias': row['field_alias'],
                            'field_source_type': row['field_source_type'],
                            'field_source': field_source,
                            'field_name': row['field_name'],
                            'field_value': row['field_value'],
                            'field_function': row['field_function'],
                            'function_field_list': row['function_field_list'],
                            'field_description': row['field_description']
                        }
                    )
                else:
                    field, created = Field.objects.update_or_create(
                        field_list=field_list,
                        source_list=source_list,
                        field_name=row['field_name'],
                        # field_source=field_source,
                        defaults={
                            'field_list': field_list,
                            'source_list': source_list,
                            'field_alias': row['field_alias'],
                            'field_source_type': row['field_source_type'],
                            'field_source': field_source,
                            'field_name': row['field_name'],
                            'field_value': row['field_value'],
                            'field_function': row['field_function'],
                            'function_field_list': row['function_field_list'],
                            'field_description': row['field_description']
                        }
                    )
                if created:
                    import_result.append((row['field_alias'], 'created'))
                    print(f"Field {field.field_alias} created")
                else:
                    import_result.append((row['field_alias'], 'updated'))
                    print(f"Field {field.field_alias} updated")
            except Exception as e:
                import_result.append(f"{row['field_alias']}: {e}")
                print(f"Error inserting data: {e}")


    elif table[:3] == 'DS_':
        for index, row in df.iterrows():
            try:
                source_union_list, created = SourceList.objects.get_or_create(
                    source_list=row['source_union_list_name']
                )
                if created:
                    import_result.append((row['source_union_list_name'], 'SourceList created'))
                    print(f"SourceList {source_union_list.source_list} created")

                if row['source_type'] == 'query':
                    table_name = None
                    source_list = None
                    source_system = None
                    source_scheme = None
                    union_type = UnionType.objects.get(union_type=row['union_type'])
                    query_name, created = Query.objects.get_or_create(
                        query_name=row['source_name']
                    )
                    if created:
                        import_result.append((row['source_name'], 'Query created'))
                        print(f"Query {query_name.query_name} created")
                    else:
                        import_result.append((row['source_name'], 'Query already exist'))
                        print(f"Query {query_name.query_name} already exist")

                elif row['source_type'] == 'data_source':
                    source_list = SourceList.objects.get(source_list=row['source_name'])
                    query_name = None
                    table_name = None
                    source_system = None
                    source_scheme = None
                    union_type = UnionType.objects.get(union_type=row['union_type'])

                elif row['source_type'] == 'table':
                    table_name = row['source_name']
                    try:
                        source_system = SourceSystem.objects.get(source_system_name=row['source_system'])
                    except SourceSystem.DoesNotExist:
                        source_system = None
                    try:
                        source_scheme = SourceScheme.objects.get(source_scheme_name=row['source_scheme'])
                    except SourceScheme.DoesNotExist:
                        source_scheme = None
                    try:
                        union_type = UnionType.objects.get(union_type=row['union_type'])
                    except UnionType.DoesNotExist:
                        union_type = None
                    query_name = None
                    source_list = None

                source, created = Source.objects.update_or_create(
                    source_union_list=source_union_list,
                    source_alias=row['source_alias'],
                    source_type=row['source_type'],
                    defaults={
                        # 'source_union_list': source_union_list,
                        # 'source_alias': row['source_alias'],
                        # 'source_type': row['source_type'],
                        'query_name': query_name,
                        'source_list': source_list,
                        'table_name': table_name,
                        'source_system': source_system,
                        'source_scheme': source_scheme,
                        'union_type': union_type,
                        'union_condition': row['union_condition'],
                        'source_description': row['source_description']
                    }
                )
                if created:
                    import_result.append((row['source_alias'], 'DataSource created'))
                    print(f"DataSource {source.source_alias} created")
                else:
                    import_result.append((row['source_alias'], 'DataSource updated'))
                    print(f"DataSource {source.source_alias} updated")

            except Exception as e:
                import_result.append(f"{row['source_alias']}: {e}")
                print(f"Error inserting data: {e}")

    elif table[:2] == 'Q_':
        for index, row in df.iterrows():
            query_alias = row.get('query_alias', None)
            try:
                field_list = FieldList.objects.get(field_list_name=row['query_fields'])
            except FieldList.DoesNotExist:
                field_list = None
            try:
                source_list = SourceList.objects.get(source_list=row['query_source'])
            except SourceList.DoesNotExist:
                source_list = None

            try:
                query_name, created = Query.objects.update_or_create(
                    query_name=row['query_name'],
                    defaults={
                        'field_list': field_list,
                        'source_list': source_list,
                        'query_conditions': row['query_conditions'],
                        'query_alias': query_alias,
                        'query_description': row['query_description']
                    }
                )
                if created:
                    import_result.append((row['query_name'], 'created'))
                    print(f"Query {query_name.query_name} created")
                else:
                    import_result.append((row['query_name'], 'updated'))
                    print(f"Query {query_name.query_name} updated")
            except Exception as e:
                import_result.append(f"{row['query_name']}: {e}")
                print(f"Error inserting data: {e}")

    else:
        print(f"This type of object do not support for import, {table}")
        import_result = f"This type of object do not support for import, {table}"

    context = {'import_result': import_result}
    return JsonResponse(context)


# def import_table_from_excel(self, workbook_filename, sheet_name: str = '', table_name: str = ''):
def import_table_from_excel(workbook_filename, sheet_name: str = '', table_name: str = ''):
    wb = load_workbook(filename=workbook_filename)
    print(wb.sheetnames)
    sheet = wb[sheet_name]
    print(sheet.tables.keys(), '\n')
    lookup_table = sheet.tables[table_name]
    print(lookup_table.ref)

    data = sheet[lookup_table.ref]
    rows_list = []

    for row in data:
        cols = []
        for col in row:
            cols.append(col.value)
        rows_list.append(cols)

    df = pd.DataFrame(data=rows_list[1:], index=None, columns=rows_list[0])
    df.to_csv(f'{table_name}.csv', index=False)

    # self.display_df(df)
    return df


def db_management(request: HttpRequest):
    context = {
        "text": "Excel Import!!!"
    }
    return render(request, 'storage/dbmanagement.html', context)


@csrf_exempt
def upload_db_json(request):
    # context = {'message': 'Файл успешно загружен'}
    context = {}
    if request.FILES.get('dbJson'):
        file = request.FILES.get('dbJson')
        if not file:
            return JsonResponse({'error': 'No file to download'}, status=400)

        # Здесь вы можете обрабатывать файл, например, сохранять его на сервере
        fss = FileSystemStorage()
        filename = fss.save(file.name, file)
        # file_url = fss.url(filename)
        file_path = fss.path(filename)
        # context = {'message': 'File uploaded successfully', 'file_path': file_path}

        import_file = file_path
        try:
            call_command('loaddata', import_file)
            context = {'message': f'Data successfully loaded from {import_file}'}
            print(f"Data successfully loaded from {import_file}")
        except Exception as e:
            print(f"Error while data loading: {e}")

        try:
            os.remove(import_file)
            print(f"Deleted: {import_file}")
        except Exception as e:
            print(f"Error deleting {import_file}: {e}")

        # Знаходимо всі файли, що відповідають масці
        files_to_delete = glob.glob("dgf_storage_*.json")

        # Видаляємо знайдені файли
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

        return JsonResponse(context)

    return render(request, 'storage/dbmanagement.html', {'message': 'File do not uploaded'})


@csrf_exempt
def download_db_json(request):
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_file = f"dgf_storage_{current_date}.json"
    # file_path = os.path.join('media', 'uploads', output_file)

    # Виконання команди dumpdata
    try:
        call_command('dumpdata', 'storage', '--indent', '2', '--output', output_file)
        print(f"Data successfully dumped to {output_file}")
    except Exception as e:
        print(f"Error while dumping data: {e}")

    # Перевіряємо, чи існує файл
    if not os.path.exists(output_file):
        raise Http404("File not found.")

    # Відправка файлу як відповідь
    response = FileResponse(open(output_file, 'rb'), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{output_file}"'

    return response


def sql_parsing(request: HttpRequest):
    context = {
        "text": "SQL parser!!!"
    }
    return render(request, 'storage/sql_parsing.html', context)


@csrf_exempt
def parse_sql_to_json(request):
    if request.method == 'POST':
        try:
            # Отримуємо вміст SQL із запиту
            body = json.loads(request.body)
            sql_content = body.get('sql', '')
            # report_name = body.get('filename', '')
            report_name = body.get('fileNameWithoutExt', '')

            # Простий приклад парсингу SQL у JSON
            # У реальних випадках тут можна викликати складний парсер SQL
            # parsed_data = {
            #     "query": sql_content.strip(),  # Упорядкований текст SQL
            #     "message": "SQL parsed successfully!"
            # }
            report_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            parsed_data = find_select_from_where(sql_content, report_id, report_name)

            # Повертаємо розпарсений SQL як JSON
            return JsonResponse(parsed_data, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)


@csrf_exempt
def upload_json(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            json_content = body.get('json', '')
            sql_content = body.get('sql', '')

            result, load_message = nested_queryies_load(json_content, sql_content)

            if result:
                load_message = load_message.replace(', [', ',<br>[')
                return JsonResponse({"message": load_message}, status=200)
            else:
                return JsonResponse({"error": load_message}, status=500)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=400)


@csrf_exempt
def sql_matching(request):
    old_query = "SELECT id, name FROM users WHERE active = 1;"
    old_version = "Query v 1.0"
    new_query = "SELECT id, name, email FROM users WHERE active = 1 ORDER BY name;"
    new_version = "Query v 2.0"

    # return render(request, 'storage/sql_matching.html', {'query1': query1, 'query2': query2})
    return render(request, 'storage/sql_matching.html', {
        'old_query': old_query,
        'new_query': new_query,
        'old_version': old_version,
        'new_version': new_version
    })


@csrf_exempt
def save_roles(request):
    if request.method == 'POST':
        try:
            # Отримуємо дані з тіла запиту
            data = json.loads(request.body)
            roles_data = data.get('roles', [])
            # roles_data = data.get('getRoles', {}).get('edges', [])

            if not roles_data:
                return JsonResponse({'error': 'No roles provided'}, status=400)

            for role_data in roles_data:
                node = role_data.get('node', {})
                if not node:
                    continue

                # Зберігаємо тільки name та okta_id
                okta_id = node.get('id')
                name = node.get('name')

                if not okta_id or not name:
                    continue

                # Перевіряємо, чи вже існує роль з таким okta_id
                role, created = Role.objects.update_or_create(
                    okta_id=okta_id,  # Використовуємо okta_id для пошуку або створення
                    defaults={
                        'name': name,  # Встановлюємо name
                        'source': 'okta',  # Встановлюємо source = 'okta'
                    }
                )

            return JsonResponse({'message': 'Roles successfully saved/updated'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    else:
        return JsonResponse({'error': 'Invalid HTTP method. Only POST is allowed.'}, status=405)


@csrf_exempt  # Дозволяє обробляти POST запити без CSRF токена
def role_view(request):
    if request.method == 'POST':
        # Отримуємо ролі з тіла запиту (JSON)
        try:
            data = json.loads(request.body)
            roles_data = data.get('roles', [])

            # Перевіряємо, чи є дані для ролей
            if not roles_data:
                return JsonResponse({'error': 'No roles provided'}, status=400)

            for role_data in roles_data:
                # Перевіряємо чи вже існує роль з таким окта ID
                role, created = Role.objects.update_or_create(
                    okta_id=role_data['node']['id'],  # Використовуємо окта ID для пошуку чи створення
                    defaults={
                        'name': role_data['node']['name'],
                        'source': 'okta',  # Встановлюємо значення source = 'okta'
                    }
                )
                # Оновлюємо або створюємо опис для ролі
                role.description = role_data['node'].get('description', '')
                role.save()

            return JsonResponse({'message': 'Roles successfully processed'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    else:
        # Якщо метод не POST, можемо просто рендерити шаблон або іншу сторінку
        return render(request, 'role_storage.html')


@csrf_exempt
def save_reports(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            reports = data.get('reports', [])

            # Save new reports
            for report_data in reports:
                node = report_data.get('node', {})
                report = ProxyReport(
                    report_id=node.get('id'),
                    name=node.get('name'),
                    link=node.get('link')
                )
                report.save()

            return JsonResponse({
                'status': 'success',
                'message': f'Successfully saved {len(reports)} reports'
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': 'Only POST method is allowed'
    }, status=405)