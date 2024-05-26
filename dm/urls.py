from django.urls import path
from .views import *

urlpatterns = [
    # path("upload/", upload_file),
    path("", main),

    path("fields/", fields),
    path("fields/<str:fields_list_name>/", field_list_item),
    path("fields/<str:field_source_name>/<str:field_name>/", field_item),

    path("field_lists/", field_lists),
    path("field_list/<str:field_list_name>/", field_list),
    path("field_list_edit/<str:field_list_name>/", field_list_edit),
    path("field_list/new/", field_list_edit),

    path("sources/", sources),
    path("sources/<str:source_list>/<str:type>/", source_list_item),

    path("source_lists/", source_lists),
    path("source_list/<str:source_list_name>/", source_list),
    path("source_list_edit/<str:source_list_name>/", source_list_edit),
    path("source_list/new/", source_list_edit),

    path("queries/", queries),
    path("query/<str:query_name>/", query),

    path("reports/", reports),
    path("report/<str:report_name>/", report),

    path("diagram/<str:source_type>/<str:source_name>/", diagram),

    # path("test_static/", test_static),
]