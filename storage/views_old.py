from django.shortcuts import render
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from openpyxl import load_workbook
import json
import pandas as pd
import psycopg2

# wb = None


# Create your views here.
# @csrf_exempt
def excelImport(request: HttpRequest):
    context = {
        "text": "Excel Import!!!"
    }
    return render(request, 'storage/excelimport.html', context)


# @csrf_exempt
# @require_POST
def upload_file(request):
    # global wb
    # context = {'message': 'Файл успешно загружен'}
    context = {}
    if request.FILES.get('excelFile'):
        file = request.FILES.get('excelFile')
        if not file:
            return JsonResponse({'error': 'No file to download'}, status=400)

        # Здесь вы можете обрабатывать файл, например, сохранять его на сервере
        context = {'message': 'File uploaded successfully'}
        # wb = load_workbook(file)

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
        # Define the filename
        file_name = file.name.split('.', -1)[:-1]  # 'data.json'
        i = 0
        csv_filename = ''
        for part in file_name:
            csv_filename = csv_filename + part + '.'

        # Open the file in write mode ('w') and write the JSON data
        with open(csv_filename + 'json', 'w') as f:
            json.dump(sheets, f, indent=4)

    # return JsonResponse({'message': f'Файл {file.name} успешно загружен'})
    return render(request, 'storage/excelimport.html', context)


def select_table(request):
    global wb
    if request.method == 'POST':
        sheet_name = request.POST.get('sheet')
        lookup_table = request.POST.get('table')
        selected_sheet = wb[sheet_name]
        data = selected_sheet[lookup_table.ref]
        rows_list = []

        for row in data:
            cols = []
            # print(type(row), '\n')
            for col in row:
                cols.append(col.value)
            rows_list.append(cols)

        df = pd.DataFrame(data=rows_list[1:], index=None, columns=rows_list[0])
        df.to_csv(f'{lookup_table}.csv', index=False)

        response_data = {
            'df': df
        }

        return JsonResponse(response_data)
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

        # Create Treeview widget
        # self.tree = ttk.Treeview(self)
        # self.tree.pack(expand=True, fill='both')
        #
        # # Define columns
        # self.tree["columns"] = list(df.columns)
        # self.tree["show"] = "headings"

        # Setup column headings
        # for column in self.tree["columns"]:
        #     self.tree.heading(column, text=column)

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

    # try:
        # connection = psycopg2.connect(
        #     dbname=dbname,
        #     user=user,
        #     password=password,
        #     host=host,
        #     port=port
        # )
    connection.autocommit = True
    cursor = connection.cursor()
    #     print("Connected to the database")
    # except Exception as e:
    #     print(f"Error: {e}")

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
