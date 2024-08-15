from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
# from .models import *
# from storage.models import *
from .forms import *
import json
import logging
import os

log_file_path = os.path.join(os.path.dirname(__file__), r"dgf.log")
logging.basicConfig(
    filename=log_file_path,  # Specify the log file name
    level=logging.DEBUG,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s [%(levelname)s] - %(message)s',  # Define the log message format
    datefmt='%Y-%m-%d %H:%M:%S'  # Define the date and time format
)

# logging.debug(f"Start")
# FormSourceList

nav_bar = '''
    <nav class="navbar navbar-expand-lg bg-body-tertiary">
      <div class="container-fluid">
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarSupportedContent">
          <ul class="navbar-nav me-auto mb-2 mb-lg-0">
            <li class="nav-item">
              <a class="nav-link active" aria-current="page" href="/dm/reports/">Reports</a>
            </li>
            <li class="nav-item">
              <a class="nav-link active" aria-current="page" href="/dm/queries/">Queries</a>
            </li>
            <li class="nav-item">
                <a class="nav-link active" aria-current="page" href="/dm/field_lists/">Field Lists</a>
            </li>
            <li class="nav-item">
                <a class="nav-link active" aria-current="page" href="/dm/fields/">Fields</a>
            </li>
            <li class="nav-item">
                <a class="nav-link active" aria-current="page" href="/dm/source_lists/">Source Lists</a>
            </li>
            <li class="nav-item">
                <a class="nav-link active" aria-current="page" href="/dm/sources/">Sources</a>
            </li>
          </ul>
        </div>
      </div>
    </nav>
'''

bootstrap_link = '''<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">'''


def main(request):
    context = {
        'nav_bar': nav_bar
    }
    return render(request, 'dm/main.html', context)


def fields(request):
    all_fields = Field.objects.all()
    all_field_lists = FieldList.objects.all()
    context = {
        'fields': all_fields,
        'field_lists': all_field_lists,
        'nav_bar': nav_bar
    }
    return render(request, 'dm/fields.html', context)


# def field_edit(request, field_id: str):
#     context = {
#         'nav_bar': nav_bar,
#         'bootstrap_link': bootstrap_link
#     }
#     if field_id != "new":
#         field = get_object_or_404(Field, id=field_id)
#         context['edit'] = True
#         context['add'] = False
#     else:
#         field = None
#         context['edit'] = True
#         context['add'] = True
#
#     if request.method == 'POST':
#         form = FieldForm(request.POST, instance=field)
#         if form.is_valid():
#             form.save()
#             return redirect('/dm/fields/')  # Redirect to a new URL
#     else:
#         form = FieldForm(instance=field)
#
#     context['form'] = form
#     return render(request, 'dm/field.html', context)


def field_list_item(request, fields_list_id):
    field_list = FieldList.objects.get(id=fields_list_id)
    filtered_fields = Field.objects.filter(field_list=field_list)
    all_field_lists = FieldList.objects.all()
    context = {
        'fields': filtered_fields,
        'field_lists': all_field_lists,
        'current_field_list': field_list,
        'nav_bar': nav_bar
    }
    return render(request, 'dm/fields.html', context)


def field_item(request, field_source_id, field_id):
    if field_source_id and field_id:
        field_source = Source.objects.get(id=field_source_id)
        field = get_object_or_404(Field, field_source=field_source, id=field_id)
    else:
        field = None

    context = {
        'fields': (field,),
        'field': field,
        'field_source': field_source,
        'field_lists': None,
        'current_field_list': None,
        'nav_bar': nav_bar,
        'bootstrap_link': bootstrap_link
    }
    return render(request, 'dm/fields.html', context)


def field_lists(request):
    all_field_lists = FieldList.objects.all()
    context = {
        'field_lists': all_field_lists,
        'nav_bar': nav_bar
    }
    return render(request, 'dm/field_lists.html', context)


def field_list(request, field_list_id):
    if field_list_id:
        fieldlist = get_object_or_404(FieldList, id=field_list_id)
    else:
        fieldlist = None

    form = FieldListForm(instance=fieldlist)

    for field in form.fields:
        form.fields[field].disabled = True

    context = {
        'form': form,
        'edit': False,
        # 'add': True,
        'nav_bar': nav_bar,
        'bootstrap_link': bootstrap_link
    }
    return render(request, 'dm/field_list.html', context)


def field_list_edit(request, field_list_id):
    context = {
        'nav_bar': nav_bar,
        'bootstrap_link': bootstrap_link
    }

    if field_list_id != 'new':
        fieldlist = get_object_or_404(FieldList, id=field_list_id)
        context['edit'] = True
        context['add'] = False
    else:
        fieldlist = None
        context['edit'] = True
        context['add'] = True

    if request.method == 'POST':
        form = FieldListForm(request.POST, instance=fieldlist)
        if form.is_valid():
            form.save()
            return redirect('/dm/field_lists/')
    else:
        form = FieldListForm(instance=fieldlist)

    context['form'] = form
    return render(request, 'dm/field_list.html', context)


def field(request, field_id):
    if field_id:
        field = get_object_or_404(Field, id=field_id)
    else:
        field = None

    form = FieldForm(instance=field)

    for form_field in form.fields:
        form.fields[form_field].disabled = True

    context = {
        'form': form,
        'edit': False,
        # 'add': True,
        'nav_bar': nav_bar,
        'bootstrap_link': bootstrap_link,
        'field_id': field.id,
        'field_source_id': field.field_source_id
    }
    return render(request, 'dm/field.html', context)


def field_edit(request, field_id):
    context = {
        'nav_bar': nav_bar,
        'bootstrap_link': bootstrap_link
    }

    if field_id != 'new':
        field = get_object_or_404(Field, id=field_id)
        context['edit'] = True
        context['add'] = False
    else:
        field = None
        context['edit'] = True
        context['add'] = True

    if request.method == 'POST':
        form = FieldForm(request.POST, instance=field)
        if form.is_valid():
            form.save()
            return redirect('/dm/field/')
    else:
        form = FieldForm(instance=field)

    context['form'] = form
    return render(request, 'dm/field.html', context)


def queries(request):
    all_queries = Query.objects.all()
    context = {
        'queries': all_queries,
        'nav_bar': nav_bar
    }
    return render(request, 'dm/queries.html', context)


def query(request, query_id):
    query_item = Query.objects.get(id=query_id)
    filtered_query = Query.objects.filter(query_name=query_item)
    # all_queries = Query.objects.all()
    context = {
        'query': query_item,
        'filtered_query': filtered_query,
        # 'queries': all_queries,
        'nav_bar': nav_bar,
        'bootstrap_link': bootstrap_link
    }
    return render(request, 'dm/query.html', context)


def source_lists(request):
    all_source_lists = SourceList.objects.all()
    context = {
        'source_lists': all_source_lists,
        'nav_bar': nav_bar
    }
    return render(request, 'dm/source_lists.html', context)


def source_list(request, source_list_id):
    if source_list:
        # sourcelist = get_object_or_404(Source, source_alias=source_list_name)
        sourcelist = get_object_or_404(SourceList, id=source_list_id)
    else:
        sourcelist = None

    form = SourceListForm(instance=sourcelist)

    for field in form.fields:
        form.fields[field].disabled = True

    context = {
        'form': form,
        'edit': False,
        'nav_bar': nav_bar,
        'bootstrap_link': bootstrap_link
    }
    return render(request, 'dm/source_list.html', context)


def source_list_edit(request, source_list_id):
    context = {
        'nav_bar': nav_bar,
        'bootstrap_link': bootstrap_link
    }
    if source_list != 'new':
        sourcelist = get_object_or_404(SourceList, id=source_list_id)
        context['edit'] = True
        context['add'] = False
    else:
        sourcelist = None
        context['edit'] = True
        context['add'] = True

    if request.method == 'POST':
        form = SourceListForm(request.POST, instance=sourcelist)
        if form.is_valid():
            form.save()
            return redirect('/dm/source_lists/')  # Redirect to a new URL
    else:
        form = SourceListForm(instance=sourcelist)

    context['form'] = form
    return render(request, 'dm/source_list.html', context)


def sources(request):
    all_sources = Source.objects.all()
    all_source_lists = SourceList.objects.all()
    context = {
        'sources': all_sources,
        'source_lists': all_source_lists,
        'nav_bar': nav_bar
    }
    return render(request, 'dm/sources.html', context)


def source_list_item(request, source_list_id, type):
    # source_list = SourceList.objects.get(id=source_list_id)
    if type == 'union':
        filtered_sources = Source.objects.filter(source_union_list_id=source_list_id)
    else:
        filtered_sources = Source.objects.filter(id=source_list_id)
        # filtered_sources = Source.objects.filter(source_list_name=source_list)
    all_source_lists = SourceList.objects.all()
    context = {
        'sources': filtered_sources,
        'source_lists': all_source_lists,
        'current_source_list': source_list,
        'nav_bar': nav_bar
    }
    return render(request, 'dm/sources.html', context)


def reports(request):
    all_reports = Report.objects.all()
    context = {
        'reports': all_reports,
        'nav_bar': nav_bar
    }
    return render(request, 'dm/reports.html', context)


def report(request, report_name):
    report_item = Report.objects.get(report_name=report_name)
    filtered_report = Report.objects.filter(report_name=report_item)
    # all_queries = report.objects.all()
    context = {
        'report': report_item,
        'filtered_report': filtered_report,
        # 'queries': all_queries,
        'nav_bar': nav_bar,
        'bootstrap_link': bootstrap_link
    }
    return render(request, 'dm/report.html', context)


def diagram(request, source_type, source_name):
    linear = {}
    # if source_type == 'query':
    #     source = Query.objects.get()
    linear = linearization(source_type, source_name, "")
    context = {"model": linear}
    return render(request, 'dm/diagram.html', context)


def linearization(source_type, source_name, fields2content):
    blue_rect = "<svg width=\"10\" height=\"10\"> <rect x=\"0\" y=\"0\" width=\"10\" height=\"10\" fill=\"blue\" /></svg> "
    green_rect = "<svg width=\"10\" height=\"10\"> <rect x=\"0\" y=\"0\" width=\"10\" height=\"10\" fill=\"green\" /></svg> "
    brown_rect = "<svg width=\"10\" height=\"10\"> <rect x=\"0\" y=\"0\" width=\"10\" height=\"10\" fill=\"brown\" /></svg> "
    purple_rect = "<svg width=\"10\" height=\"10\"> <rect x=\"0\" y=\"0\" width=\"10\" height=\"10\" fill=\"purple\" /></svg> "
    yellow_rect = "<svg width=\"10\" height=\"10\"> <rect x=\"0\" y=\"0\" width=\"10\" height=\"10\" fill=\"yellow\" /></svg> "

    # End of recursive
    if source_name == None:
        # logging.debug(f"source_name == None, content: end")
        return {
            "content": "end"
        }
    elif source_type == 'table':
        # logging.debug(f"source_type == 'table', content: {source_type}, children: {source_name}")
        return {
            "content": source_type,
            "children": [
                {
                    "content": brown_rect + source_name
                }
            ]
        }

    # Begin recursive body
    children = []
    f_fields = []

    if source_type == 'query' or source_type == 'report':
        if source_type == 'report':
            source = Report.objects.get(id=source_name)
            sources, source_list, field_list, fields = get_data_source(source)
        elif source_type == 'query':
            # source = Query.objects.get(id=source_name)
            sources, source_list, field_list, fields = get_query_source(source_name)
            # sources = Source.objectsget(id=source_list)

        # f_fields = []
        for field in fields:
            field_name = {}
            if field.field_source_type in ('data_source', 'tbd'):
                field_name["content"] = f"<a href=\"/dm/fields/{field.field_source_id}/{field.id}/\">{field.field_alias}</a>"
            elif field.field_source_type == 'function':
                field_name["content"] = field.field_function
            elif field.field_source_type == 'value':
                field_name["content"] = field.field_value
            field_name["content"] = f"<a href=\"/dm/fields/{field.field_source_id}/{field.id}/\">{field.field_alias}</a>"
            f_fields.append(field_name)
        for source in sources:
            if source.source_type == 'data_source':
                f_source = source.id
            elif source.source_type == 'query':
                f_source = source.query_name_id
            elif source.source_type == 'table':
                f_source = source.table_name
            children.append(linearization(source.source_type, f_source, f_fields))

    elif source_type == 'data_source':
        source = Source.objects.get(id=source_name)
        sources, source_list, field_list, fields = get_data_source(source)
        for source in sources:
            if source.source_type == 'data_source':
                f_source = source.id
            elif source.source_type == 'query':
                f_source = source.query_name_id
            elif source.source_type == 'table':
                f_source = source.table_name
            children.append(linearization(source.source_type, f_source, f_fields))

    # elif source_type == 'report':

    elif source_type == 'table':
        children.append(linearization('table', source_name, None))

    # End recursive body
    if source_type == 'data_source':
        data_source_hyperlink = f"<a href=\"/dm/sources/{str(source.source_union_list_id)}/union/ \"target=\"_blank\">{source.source_union_list.source_list}</a>"
        content = blue_rect + data_source_hyperlink
    elif source_type == 'query':
        query = Query.objects.get(id=source_name)
        data_source_hyperlink = f"<a href=\"/dm/query/{source_name}/ \"target=\"_blank\">{str(query.query_name)}</a>"
        if query.query_description:
            description = f"<p>Metadata: {query.query_description}</p>"
            content = green_rect + data_source_hyperlink + description
        else:
            content = green_rect + data_source_hyperlink
    elif source_type == 'report':
        data_source_hyperlink = f"<a href=\"/dm/sources/{str(source.source_union_list_id)}/union/ \"target=\"_blank\">{source.source_union_list.source_list}</a>"
        description = f"<p>{source.source_description}</p>"
        content = purple_rect + data_source_hyperlink
    else:
        content = str(source_name)

    # Recursive return value
    if field_list:
        field_list_hyperlink = f"<a href=\"/dm/fields/{str(field_list.id)}/\" target=\"_blank\">{str(field_list)}</a>"
    else:
        field_list_hyperlink = f"<a href=\"/dm/fields/{str(field_list)}/\" target=\"_blank\">{str(field_list)}</a>"
    field_list_content = yellow_rect + field_list_hyperlink
    if source_type in ('query', 'report'):
        return {
            "content": source_type,
            "children": [
                {
                    "content": field_list_content,
                    "children": f_fields
                },
                {
                    "content": content,
                    "children": children
                }
            ]
        }
    else:
        return {
            "content": source_type,
            "children": [
                {
                    "content": content,
                    "children": children
                }
            ]
        }


def get_query_source(source):
    query = Query.objects.get(id=source)
    try:
        # source_list = SourceList.objects.filter(source_list=query.source_list)
        source_list = SourceList.objects.get(source_list=query.source_list)
    except SourceList.DoesNotExist:
        source_list = None
    try:
        sources = Source.objects.filter(source_union_list=source_list)
    except Source.DoesNotExist:
        sources = None
    try:
        field_list = FieldList.objects.get(field_list_name=query.field_list)
    except FieldList.DoesNotExist:
        field_list = None
    try:
        fields = Field.objects.filter(field_list=query.field_list)
    except Field.DoesNotExist:
        fields = None

    return sources, source_list, field_list, fields


def get_data_source(source):
    try:
        source_list = SourceList.objects.get(source_list=source.source_list)
    except SourceList.DoesNotExist:
        source_list = None
    try:
        sources = Source.objects.filter(source_union_list=source.source_list)
    except Source.DoesNotExist:
        sources = None
    try:
        field_list = FieldList.objects.get(data_source=source_list)
    except FieldList.DoesNotExist:
        field_list = None
    try:
        fields = Field.objects.filter(source_list=source_list)
    except Field.DoesNotExist:
        fields = None

    return sources, source_list, field_list, fields


def get_report_source(source):
    try:
        source_list = SourceList.objects.get(source_list=source.source_list)
    except Report.DoesNotExist:
        source_list = None
    try:
        sources = Source.objects.filter(source_union_list=source_list)
    except Source.DoesNotExist:
        sources = None
    try:
        field_list = FieldList.objects.get(data_source=source_list)
    except FieldList.DoesNotExist:
        field_list = None
    try:
        fields = Field.objects.filter(source_list=source_list)
    except Field.DoesNotExist:
        fields = None

    return sources, source_list, field_list, fields


def field_diagram(request, source_id, field_id):
    if source_id != 'None':
        source = Source.objects.get(id=source_id)
    else:
        source = 'None'
    # field = Field.objects.get(id=field_id, field_source_id=source_id)
    field = Field.objects.get(id=field_id)
    logging.debug(f"Start {field.field_alias}/{field.field_name}")
    linear, fn_source = field_linearization(source, field)
    linear_m = {"content": str(field),
                "children": [linear]}
    context = {"model": linear_m}
    logging.debug(f"End: {fn_source}")
    return render(request, 'dm/diagram.html', context)


def field_linearization(source, field):
    blue_rect = "<svg width=\"10\" height=\"10\"> <rect x=\"0\" y=\"0\" width=\"10\" height=\"10\" fill=\"blue\" /></svg> "
    green_rect = "<svg width=\"10\" height=\"10\"> <rect x=\"0\" y=\"0\" width=\"10\" height=\"10\" fill=\"green\" /></svg> "
    brown_rect = "<svg width=\"10\" height=\"10\"> <rect x=\"0\" y=\"0\" width=\"10\" height=\"10\" fill=\"brown\" /></svg> "
    purple_rect = "<svg width=\"10\" height=\"10\"> <rect x=\"0\" y=\"0\" width=\"10\" height=\"10\" fill=\"purple\" /></svg> "
    yellow_rect = "<svg width=\"10\" height=\"10\"> <rect x=\"0\" y=\"0\" width=\"10\" height=\"10\" fill=\"yellow\" /></svg> "

# Recurrent end points
    if field is None:
        return {
            "content": "None"
        }

    match field.field_source_type:
        case 'function':
            fn_source = {"id": field.id, "field": field.field_name, "field_list": str(field.field_list),
                         "source_type": field.field_source_type, "function": field.field_function}
            logging.debug(f"rw = 602: {fn_source}")
            return {
                # "content": f"<a href=\"/dm/fields/{field.field_source_id}/{field.id}/ \"target=\"_blank\">{str(field.field_name)}</a>",  #TODO: remove field.field_source_id
                "content": "function",
                    "children": [
                    {
                        "content": purple_rect + field.field_function
                    }
                ]
            }, "function"
        case 'value':
            fn_source = {"id": field.id, "field": field.field_name, "field_list": str(field.field_list), "source_type": field.field_source_type, "value": field.field_value}
            logging.debug(f"rw = 614: {fn_source}")
            return {
                # "content": f"<a href=\"/dm/fields/{field.id}/ \"target=\"_blank\">{str(field.field_name)}</a>", #TODO: remove field.field_source_id
                "content": "value",
                "children": [
                    {
                        "content": green_rect + field.field_value
                    }
                ]
            }, "value"
        case 'table':
            fn_source = {"id": field.id, "field": field.field_name, "field_list": str(field.field_list),
                         "source_type": field.source_type, "value": field.field_value}
            logging.debug(f"rw = 614: {fn_source}")
            return {
                       "content": f"<a href=\"/dm/fields/{field.field_source_id}/{field.id}/ \"target=\"_blank\">{str(field.field_name)}</a>",
                       # TODO: remove field.field_source_id
                       "children": [
                           {
                               "content": brown_rect + field.field_value
                           }
                       ]
                   }, "value"
        case 'tbd':
            return {
                "content": f"<a href=\"/dm/fields/{field.field_source_id}/{field.id}/ \"target=\"_blank\">{str(field.field_name)}</a>", #TODO: remove field.field_source_id
                "children": [
                    {
                        "content": 'TBD'
                    }
                ]
            }, "tbd"
# Main recurrent function
    children = []
    field_chains = []
    if field.field_source_type == 'query':
        sources, source_list, field_list, fields = get_source(source)
        field_aliases = fields.values_list('field_alias', flat=True)
        if field.field_name in field_aliases:
            for source_item in sources:
                try:
                    field = Field.objects.get(field_alias=field.field_name, field_source_id=source_item.id)
                except Field.DoesNotExist:
                    field = field
                # logging.debug(f"rw = 647, source_item = {source_item}, field: {field}")
                fn_response, fn_source = field_linearization(source_item, field)
                # logging.debug(f"rw = 649, fn_response = {fn_response}, fn_source: {fn_source}")
                if fn_response['content'] != 'None':
                    children.append(fn_response)
                    field_chains.append(fn_source)
        else:
            # logging.debug(f"rw = 654, content = None, None")
            return {
                "content": "None"
            }, "None"
    elif field.field_source_type == 'data_source':
        sources, source_list, field_list, fields = get_source(source)
        for source_item in sources:
            try:
                field = Field.objects.get(field_alias=field.field_name, field_source_id=source_item.id)
            except Field.DoesNotExist:
                field = field
            # logging.debug(f"rw = 665, source_item = {source_item}, field: {field}")
            fn_response, fn_source = field_linearization(source_item, field)
            # logging.debug(f"rw = 667, fn_response = {fn_response}, fn_source: {fn_source}")
            if fn_response['content'] != 'None':
                # logging.debug(f"rw = 669, children = {children}, field_chains: {field_chains}")
                children.append(fn_response)
                field_chains.append(fn_source)

    elif field.field_source_type == 'table':  # and source.source_alias == field.field_source.source_alias:
        fn_source = {"field_id": field.id, "field": field.field_name, "field_list": str(field.field_list), "source_type": field.field_source_type, "table": field.field_source}
        logging.debug(f"rw = 672: {fn_source}")
        return {
            "content": source.source_type,
            "children": [
                {
                    "content": f"<a href=\"/dm/fields/{field.field_source_id}/{field.id}/ \"target=\"_blank\">{str(field.field_name)}</a>"
                },
                {
                    "content": source.table_name
                }
            ]
        }, field_chains
    else:
        # logging.debug(f"rw = 688, content = None, None")
        return {
            "content": "None"
        }, "None"

# Recurrent end function
    if source.source_type == 'data_source':
        data_source_hyperlink = f"<a href=\"/dm/sources/{str(source.id)}/{source.source_type}/ \"target=\"_blank\">{str(source.source_alias)}</a>"
        content = data_source_hyperlink
        return {
                   "content": source.source_type,
                   "children": [
                       # {
                       #     "content": f"<a href=\"/dm/fields/{field.field_source_id}/{field.id}/ \"target=\"_blank\">{str(field.field_name)}</a>"
                       # },
                       {
                           "content": content,
                           "children": children
                       }
                   ]
               }, "finish"
    elif source.source_type == 'query':
        fields_names = []
        for item in fields:
            if field.field_name != '':
                fields_names.append(item.field_name)
        if field.field_name in fields_names:
            data_source_hyperlink = f"<a href=\"/dm/sources/{str(source.id)}/{source.source_type}/ \"target=\"_blank\">{str(source.source_alias)}</a>"
            content = data_source_hyperlink
            return {
                       "content": source.source_type,
                       "children": [
                           {
                               "content": f"<a href=\"/dm/fields/{field.field_source_id}/{field.id}/ \"target=\"_blank\">{str(field.field_name)}</a>"
                           },
                           {
                               "content": content,
                               "children": children
                           }
                       ]
                   }, "finish"
        else:
            return {
                       "content": "None"
                   }, "None"
    elif source.source_type == 'table':
        if field.field_source.source_alias == source.source_alias:
            content = yellow_rect + str(source.table_name)
            return {
                       "content": source.source_type,
                       "children": [
                           {
                               "content": f"<a href=\"/dm/fields/{field.field_source_id}/{field.id}/ \"target=\"_blank\">{str(field.field_name)}</a>"
                           },
                           {
                               "content": content,
                               "children": children
                           }
                       ]
                   }, "finish"
        else:
            return {
                       "content": "None"
                   }, "None"
    elif source.source_type == 'report':
        data_source_hyperlink = f"<a href=\"/dm/sources/{str(source.id)}/union/ \"target=\"_blank\">{str(source.source_name)}</a>"
        content = data_source_hyperlink
    else:
        content = str(source.source_name)

    # logging.debug(
    #     f"rw = 707, Branch finish. content: {source.source_type}, children = {str(field.field_name)}, content: {source.table_name}, fn_source: finish")
    # match field.field_source_type:
    #     case 'function':
    #         diagram_source_type = 'function'
    #     case 'value':
    #         diagram_source_type = 'value'
    #     case _:
    #         diagram_source_type = source.source_type
    return {
        "content": source.source_type,
        "children": [
            {
                "content": f"<a href=\"/dm/fields/{field.field_source_id}/{field.id}/ \"target=\"_blank\">{str(field.field_name)}</a>"
            },
            {
                "content": content,
                "children": children
            }
        ]
    }, "finish"


def get_source(source):
    if source.source_type == 'query':  # isinstance(source, Query):
        query = Query.objects.get(query_name=source.query_name)
        try:
            source_list = SourceList.objects.get(source_list=query.source_list)
        except SourceList.DoesNotExist:   # 'SourceList matching query does not exist.'
            source_list = None
        try:
            sources = Source.objects.filter(source_union_list=source_list)
        except Source.DoesNotExist:
            sources = None
        try:
            field_list = FieldList.objects.get(field_list_name=query.field_list)
        except FieldList.DoesNotExist:
            field_list = None
        try:
            fields = Field.objects.filter(field_list=query.field_list)
        except Field.DoesNotExist:
            fields = None

        return sources, source_list, field_list, fields

    elif source.source_type == 'data_source':  # isinstance(source, Source):
        try:
            source_list = SourceList.objects.get(source_list=source.source_list)
        except SourceList.DoesNotExist:
            source_list = None
        try:
            sources = Source.objects.filter(source_union_list=source.source_list)
        except Source.DoesNotExist:
            sources = None
        try:
            field_list = FieldList.objects.get(data_source=source_list)
        except FieldList.DoesNotExist:
            field_list = None
        try:
            fields = Field.objects.filter(source_list=source_list, field_list=field_list)
        except Field.DoesNotExist:
            fields = None

        return sources, source_list, field_list, fields

    elif isinstance(source, Report):
        try:
            source_list = SourceList.objects.get(source_list=source.source_list)
        except Report.DoesNotExist:
            source_list = None
        try:
            sources = Source.objects.filter(source_union_list=source_list)
        except Source.DoesNotExist:
            sources = None
        try:
            field_list = FieldList.objects.get(data_source=source_list)
        except FieldList.DoesNotExist:
            field_list = None
        try:
            fields = Field.objects.filter(source_list=source_list)
        except Field.DoesNotExist:
            fields = None

        return sources, source_list, field_list, fields

    elif source.source_type == 'table':
        try:
            source_list = SourceList.objects.get(source_list=source.source_list)
        except SourceList.DoesNotExist:
            source_list = None
        try:
            sources = Source.objects.filter(source_union_list=source_list)
        except Source.DoesNotExist:
            sources = None
        try:
            field_list = FieldList.objects.get(data_source=source_list)
        except FieldList.DoesNotExist:
            field_list = None
        try:
            fields = Field.objects.filter(source_list=source_list)
        except Field.DoesNotExist:
            fields = None

        return sources, source_list, field_list, fields

    else:
        return None, None, None, None