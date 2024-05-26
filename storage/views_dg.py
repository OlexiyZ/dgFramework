from django.shortcuts import render
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from openpyxl import load_workbook
import json

# Create your views here.
@csrf_exempt
def excelImport(request: HttpRequest):
    context = {
        "text": "Excel Import!!!"
    }
    return render(request, 'storage/excelimport.html', context)


@csrf_exempt
# @require_POST
def upload_file(request):
    # context = {'message': 'Файл успешно загружен'}
    context = {}
    if request.FILES.get('excelFile'):
        file = request.FILES.get('excelFile')
        if not file:
            return JsonResponse({'error': 'Нет файла для загрузки'}, status=400)

        # Здесь вы можете обрабатывать файл, например, сохранять его на сервере
        context = {'message': 'Файл успешно загружен'}
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
        # Define the filename
        file_name = file.name.split('.', -1)[:-1]  # 'data.json'
        i = 0
        filename = ''
        for part in file_name:
            filename = filename + part + '.'

        # Open the file in write mode ('w') and write the JSON data
        with open(filename + 'json', 'w') as f:
            json.dump(sheets, f, indent=4)

    # return JsonResponse({'message': f'Файл {file.name} успешно загружен'})
    return render(request, 'storage/excelimport.html', context)


def select_table(request):
    if request.method == 'POST':
        print(request.POST.get('sheet'))
        print(request.POST.get('table'))
        