from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("import/", excelImport),
    path("upload_file/", upload_file),
    path("select_table/", select_table),
    path("import_csv/", import_csv),
    path("import_excel/", import_excel),
    path("db_management/", db_management),
    path("upload_db_json/", upload_db_json),
    path("download_db_json/", download_db_json),
    path("sql_parsing/", sql_parsing),
    path("parse_sql_to_json/", parse_sql_to_json),
    path("upload_json/", upload_json),
    path("sql_matching/", sql_matching),
    # path('login/', auth_views.LoginView.as_view(), name='login'),
    path('login/', login_page, name='login'),
    path('oidc-login/', oidc_login, name='oidc_login'),
    path('storage/role/', role_view, name='role_view'),
    path('save_roles/', save_roles, name='save_roles'),
    path('check_role/', check_role, name='check_role'),
    # path('get_roles/', get_roles, name='get_roles'),
]
