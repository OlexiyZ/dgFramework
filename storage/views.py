from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from openpyxl import load_workbook
import json
import pandas as pd
import psycopg2
from django.core.files.storage import FileSystemStorage
import os
from .models import *

wb = None


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
        context = {'message': 'File uploaded successfully'}
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
        return JsonResponse(sheets)

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


def import_csv(request):
    print("Request data: ", request.body)
    context = {'text': 'CSV Loaded'}
    return JsonResponse(context)
    # render(request, 'storage/import_csv.html', context)


def import_excel(request):
    if request.method == 'POST' and request.FILES['excelFile']:
        upload = request.FILES['excelFile']
        fss = FileSystemStorage()
        file = fss.save(upload.name, upload)
        file_url = fss.url(file)
        context = {'message': 'File uploaded successfully'}
        file_path = os.path.join('media/', file)
        wb = load_workbook(file_path)

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

        context['file_url'] = file_url
        context['sheets'] = sheets.keys()
        return render(request, 'storage/import_excel.html', context)
    elif request.method == 'POST' and request.body('firstSelect'):
        context = {'message': 'secondSelect'}
        return render(request, 'storage/import_excel.html', context)
    return render(request, 'storage/import_excel.html')


# def first_select(request):


# def fields(request):
#     all_fields = Field.objects.all()
#     context = {
#         'fields': all_fields,
#     }
#     return render(request, 'storage/fields.html', context)
#
#
# def field_lists(request):
#     all_field_lists = FieldList.objects.all()
#     context = {
#         'field_lists': all_field_lists
#     }
#     return render(request, 'storage/field_lists.html', context)
