from django.urls import path
from .views import *

urlpatterns = [
    path("import/", excelImport),
    path("upload_file/", upload_file),
    path("select_table/", select_table),
    path("import_csv/", import_csv),
    path("import_excel/", import_excel),
    path("db_management/", db_management),
    path("upload_db_json/", upload_db_json),
    path("download_db_json/", download_db_json),
    path("sql_parser/", sql_parser),
]