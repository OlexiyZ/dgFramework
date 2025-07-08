from django.contrib import admin
from .models import *
from django.utils.html import format_html

from django.contrib.admin import AdminSite
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.forms import Textarea
from django.db.models import QuerySet
import requests
from django.template.defaultfilters import truncatechars
from django.shortcuts import render
from django.conf import settings
import json
import platform


class DGFAdminSite(AdminSite):
    site_header = _("Data Governance Framework")
    site_title = _("DG Framework Site")
    index_title = _("Welcome to Data Governance Framework Portal")


# Create an instance of the custom admin site
dgf_admin = DGFAdminSite(name='dgf_admin')


# Register your models here.

class RulesInline(admin.TabularInline):
    model = Rule
    extra = 0
    list_display = ('name', 'rule_link', 'value', 'description', 'metadata')
    readonly_fields = ('name', 'rule_link', 'value', 'description', 'metadata')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 5, 'cols': 100})},
    }

    def rule_link(self, rule: Rule):
        return format_html(
            f"<a href=\"/admin/storage/rule/{str(rule.id)}/ \"target=\"_blank\">{rule.name}</a>")


class MetadataAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'metadata_rules', 'default_rule_link')
    search_fields = ('name',)
    ordering = ['name']
    inlines = (RulesInline,)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 5, 'cols': 100})},
    }

    def metadata_rules(self, metadata: Metadata):
        rules = ', '.join([rule.name for rule in metadata.rule_set.all()])
        return format_html(
            f"<a href=\"/storage/rule/?metadata__id__exact={str(metadata.id)}\" target=\"_blank\">{rules}</a>")

    def default_rule_link(self, metadata: Metadata):
        return format_html(
            f"<a href=\"/storage/rule/{str(metadata.default_rule_id)}/\" target=\"_blank\">{str(metadata.default_rule)}</a>")

    default_rule_link.short_description = "DEFAULT RULE"


# @admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'rule_list', 'source', 'description')
    # list_filter = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('rule',)
    ordering = ['name']
    # inlines = (RuleInline,)
    actions = ['send_roles', 'get_roles_from_proxy', 'check_role']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 5, 'cols': 100})},
    }

    def rule_list(self, obj):
        return ', '.join([rule.name for rule in obj.rule.all()])


    @admin.action(description='Check Role on the Proxy')
    def check_role(self, request, roles: QuerySet):
        proxy_host = settings.PROXY_HOST
        username = request.user.username

        try:
            user = OktaUser.objects.get(username=username)
            access_token = user.access_token
        except OktaUser.DoesNotExist:
            return None

        # rules_to_send = []
        data = {}
        # for role in roles:
        role = roles[0]
        role_id = role.okta_id
        # rules = role.rule.all()
        # for rule in rules:
        #     data[f"{rule.metadata}"] = f"{rule.value}"

        payload = {
            "query": """
                        GetRole($getRoleId: String!) {
                            getRole(id: $getRoleId) {
                                name
                                attrs
                                id
                            }
                        }
                    """,
            "variables": {
                "getRoleId": role_id
            }
        }

        context = {
            'auth_token': access_token,
            'proxy_host': proxy_host,
            'payload': json.dumps(payload),  # Перетворюємо payload в JSON рядок
            'role_id': role_id
        }

        return render(request, 'storage/check_role.html', context)


    @admin.action(description='Send Role`s rules to the Proxy')
    def send_roles(self, request, roles: QuerySet):
        proxy_host = settings.PROXY_HOST
        username = request.user.username

        try:
            user = OktaUser.objects.get(username=username)
            access_token = user.access_token
        except OktaUser.DoesNotExist:
            return None

        rules_to_send = []
        data = {}
        # for role in roles:
        role = roles[0]
        role_patch_id = role.okta_id
        rules = role.rule.all()
        for rule in rules:
            data[f"{rule.metadata}"] = f"{rule.value}"

        payload = {
            "query": """
                        mutation RolePatch($input: PatchRoleInput!, $rolePatchId: String!) {
                            rolePatch(input: $input, id: $rolePatchId) {
                                attrs
                                id
                            }
                        }
                    """,
            "variables": {
                "input": {
                    "attrs": data  # Перетворюємо на JSON
                },
                "rolePatchId": role_patch_id
            }
        }

        context = {
            'auth_token': access_token,
            'proxy_host': proxy_host,
            'payload': json.dumps(payload),  # Перетворюємо payload в JSON рядок
            'role_patch_id': role_patch_id
        }

        return render(request, 'storage/send_roles.html', context)


    @admin.action(description='Get Roles from Proxy')
    def get_roles_from_proxy(self, request, queryset: QuerySet):
        # Отримання параметрів із сесії
        # auth_token = request.session.get('auth_token', '')
        proxy_host = settings.PROXY_HOST
        username = request.user.username
        try:
            if username == "admin" and platform.system() != "Windows":
                user = OktaUser.objects.get(username="n.hamed@bankaletihad.com")
                access_token = user.access_token
            else:
                user = OktaUser.objects.get(username=username)
                access_token = user.access_token
        except OktaUser.DoesNotExist:
            return None

        # Контекст для передачі в шаблон
        context = {
            'auth_token': access_token,
            'proxy_host': proxy_host,
        }

        # Рендеринг сторінки get_roles.html з параметрами
        return render(request, 'storage/get_roles.html', context)


class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'description', 'metadata')
    list_filter = ('metadata',)
    search_fields = ('name',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 5, 'cols': 100})},
    }


class FieldAdmin(admin.ModelAdmin):
    list_display = (
        'field_alias', 'field_erd', 'field_source_type', 'field_source_url', 'field_name', 'metadata', 'field_value',
        'field_function', 'function_field_list', 'field_list_url', 'source_list_url', 'field_description')
    list_filter = ('metadata', 'field_list', 'source_list')
    search_fields = ('field_alias', 'field_name', 'field_description')
    list_editable = ['metadata']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 100})},
    }

    def field_erd(self, field: Field):
        return format_html(
            f"<a href=\"/dm/field_diagram/{str(field.field_source_id)}/{str(field.id)}/\" target=\"_blank\">ERD</a>")

    def field_source_url(self, field: Field):
        if field.field_source_type == 'data_source' and field.field_source != None:
            return format_html(
                f"<a href=\"/admin/storage/source/{str(field.field_source.id)}/ \"target=\"_blank\">{field.field_source}</a>")
        else:
            return "-"

    def source_list_url(self, field: Field):
        if field.source_list != None:
            return format_html(
                f"<a href=\"/admin/storage/source/{str(field.source_list.id)}/ \"target=\"_blank\">{field.source_list}</a>")
        else:
            return "-"

    def field_list_url(self, field: Field):
        return format_html(
            f"<a href=\"/admin/storage/source/{str(field.field_list.id)}/ \"target=\"_blank\">{field.field_list}</a>")


class FieldsInline(admin.TabularInline):
    model = Field
    extra = 0
    # list_display = [
    #     'field_link', 'field_erd', 'field_source_type', 'field_source', 'field_name', 'metadata', 'field_value',
    #     'field_function', 'function_field_list', 'field_list', 'source_list', 'field_description']
    readonly_fields = [
        'field_link', 'field_alias', 'field_erd', 'field_source_type', 'field_source', 'field_name', 'metadata',
        'field_value',
        'field_function', 'function_field_list', 'field_list', 'source_list', 'field_description']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 50})},
    }

    def field_erd(self, field: Field):
        return format_html(
            f"<a href=\"/dm/field_diagram/{str(field.field_source_id)}/{str(field.id)}/\" target=\"_blank\">ERD</a>")

    def field_link(self, field: Field):
        return format_html(
            f"<a href=\"/admin/storage/field/{str(field.id)}/ \"target=\"_blank\">{field.field_alias}</a>")

    field_link.short_description = 'FIELD NAME'


class FieldListAdmin(admin.ModelAdmin):
    list_display = ('field_list_name', 'datasource_url', 'field_list_description')
    search_fields = ('field_list_name', 'data_source', 'field_list_description')
    # list_filter = ('id',)
    inlines = (FieldsInline,)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3})},
    }

    def datasource_url(self, field_list: FieldList):
        return format_html(
            f"<a href=\"/admin/storage/source/?source_union_list__id__exact={str(field_list.data_source.id)} \"target=\"_blank\">{field_list.data_source}</a>")

    datasource_url.short_description = 'DATA SOURCE'


class SourcesInline(admin.TabularInline):
    model = Source
    extra = 0
    fk_name = 'source_union_list'
    list_display = (
        'source_alias', 'source_union_list_url', 'source_type', 'query_name', 'source_list_url', 'table_name', 'source_system',
        'source_scheme', 'union_type', 'union_condition', 'source_description')
    readonly_fields = [field.name for field in Source._meta.fields]
    # readonly_fields = (
    #     'source_alias', 'source_union_list_url', 'source_type', 'query_name', 'source_list', 'table_name',
    #     'source_system',
    #     'source_scheme', 'union_type', 'union_condition', 'source_description')
    # list_filter = ('source_union_list', 'source_type', 'table_name', 'source_system', 'source_scheme')
    # search_fields = ('source_alias', 'source_description')


    def source_list_url(self, source: Source):
        if source.source_list != None:
            return format_html(
                f"<a href=\"/admin/storage/sourcelist/{str(source.source_list.id)}/ \"target=\"_blank\">{source.source_list}</a>")
        else:
            return "-"

    def source_union_list_url(self, source: Source):
        if source.source_union_list != None:
            return format_html(
                f"<a href=\"/admin/storage/source/?source_union_list__id__exact={str(source.source_union_list.id)} \"target=\"_blank\">{source.source_union_list}</a>")
        else:
            return "-"

    source_list_url.short_description = "SOURCE LIST"
    source_union_list_url.short_description = "SOURCE UNION LIST"


class SourceListAdmin(admin.ModelAdmin):
    list_display = ('source_list', 'datasource_url', 'source_list_description')
    search_fields = ('source_list', 'source_list_description')
    inlines = (SourcesInline,)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3})},
    }

    def datasource_url(self, source_list: SourceList):
        return format_html(
            f"<a href=\"/admin/storage/source/?source_union_list__id__exact={str(source_list.id)} \"target=\"_blank\">{source_list}</a>")

    datasource_url.short_description = 'DATA SOURCE'


class QueryAdmin(admin.ModelAdmin):
    # fields = (
    #     'query_name', 'erd', 'field_list_url', 'source_list_url', 'query_conditions', 'query_alias', 'query_description')
    list_display = (
        'query_name', 'erd', 'field_list_url', 'source_list_url', 'query_conditions_short', 'query_alias', 'query_description_short')
    list_filter = ('reports__report_name',)
    search_fields = ('query_name', 'query_alias', 'query_description')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 5, 'cols': 100})},
    }

    def erd(self, query: Query):
        return format_html(
            f"<a href=\"/dm/diagram/query/{str(query.id)}/\" target=\"_blank\">ERD</a>")

    def field_list_url(self, query: Query):
        if query.field_list != None:
            return format_html(
                f"<a href=\"/admin/storage/field/?field_list__id__exact={str(query.field_list.id)} \"target=\"_blank\">{query.field_list}</a>")
            # return format_html(
            #     f"<a href=\"/admin/storage/fieldlist/{str(query.field_list.id)}/ \"target=\"_blank\">{query.field_list}</a>")
        else:
            return "-"

    def source_list_url(self, query: Query):
        if query.source_list != None:
            return format_html(
                f"<a href=\"/admin/storage/source/?source_union_list__id__exact={str(query.source_list.id)} \"target=\"_blank\">{query.source_list}</a>")
        else:
            return "-"

    def query_conditions_short(self, obj: Query):
        return format_html("<span title='{}'>{}</span>", obj.query_conditions, truncatechars(obj.query_conditions, 50))

    def query_description_short(self, obj: Query):
        return format_html("<span title='{}'>{}</span>", obj.query_description, truncatechars(obj.query_description, 50))


    field_list_url.short_description = "FIELD LIST"
    source_list_url.short_description = "SOURCE LIST"
    query_conditions_short.short_description = "QUERY CONDITION"


class ReportVersionInline(admin.TabularInline):
    model = ReportVersion
    extra = 0
    fields = ['version', 'report_query']
    readonly_fields = [field.name for field in ReportVersion._meta.fields]


class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'report_name', 'erd', 'report_query_url', 'report_description_short', 'report_url', 'ver',
        'change_description_short', 'change_date', 'changed_by')
    search_fields = ('report_name', 'report_description', 'report_url', 'change_description')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 100})},
    }
    inlines = (ReportVersionInline,)

    def ver(self, report: Report):
        if report.version != None:
            return format_html(
                f"<a href=\"/admin/storage/reportversion/?report__id__exact={str(report.id)} \"target=\"_blank\">{report.version}</a>")
        else:
            return "-"

    def report_query_url(self, report: Report):
        if report.report_query != None:
            return format_html(
                f"<a href=\"/admin/storage/query/?id={str(report.report_query.id)} \"target=\"_blank\">{report.report_query}</a>")
        else:
            return "-"

    def erd(self, report: Report):
        if report.report_query:
            return format_html(
                f"<a href=\"/dm/diagram/query/{str(report.report_query.id)}/\" target=\"_blank\">ERD</a>")
        else:
            return "-"

    def change_description_short(self, obj: Report):
        return format_html("<span title='{}'>{}</span>", obj.change_description, truncatechars(obj.change_description, 50))
    change_description_short.short_description = "CHANGE DESCRIPTION"

    def report_description_short(self, obj: Report):
        return format_html("<span title='{}'>{}</span>", obj.report_description, truncatechars(obj.report_description, 50))
    report_description_short.short_description = "REPORT DESCRIPTION"


class ReportVersionAdmin(admin.ModelAdmin):
    list_display = (
        'report', 'version', 'report_query', 'version_description_short', 'script_short')
    search_fields = ('report', 'report_query')
    list_filter = ['report']
    actions = ['versions_compare']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 5, 'cols': 100})},
    }

    def version_description_short(self, obj: ReportVersion):
        return format_html("<span title='{}'>{}</span>", obj.version_description, truncatechars(obj.version_description, 50))

    version_description_short.short_description = "VERSION DESCRIPTION"

    def script_short(self, obj: ReportVersion):
        return format_html("<span title='{}'>{}</span>", obj.script, truncatechars(obj.script, 50))

    script_short.short_description = "SCRIPT"

    @admin.action(description='Compare versions (select only two versions)')
    def versions_compare(self, request, queries: QuerySet):
        # selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        selected = queries
        if len(selected) != 2:
            self.message_user(request, 'Please select exactly two versions to compare.')
            return

        new_object = selected[0]
        old_object = selected[1]
        # report_version_1 = ReportVersion.objects.get(id=selected[0])
        new_query = new_object.script
        new_version = str(new_object)
        # report_version_2 = ReportVersion.objects.get(id=selected[1])
        old_query = old_object.script
        old_version = str(old_object)

        return render(request, 'storage/sql_matching.html', {
            'old_query': old_query,
            'new_query': new_query,
            'old_version': old_version,
            'new_version': new_version
        })

class SourceAdmin(admin.ModelAdmin):
    list_display = (
        'source_alias', 'source_union_list_url', 'source_type', 'query_name', 'source_list_url', 'table_name', 'source_system',
        'source_scheme', 'union_type', 'union_condition', 'source_description')
    list_filter = ('source_union_list', 'source_type', 'table_name', 'source_system', 'source_scheme')
    search_fields = ('source_alias', 'source_description')
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 5, 'cols': 100})},
    }


    def source_list_url(self, source: Source):
        if source.source_list != None:
            return format_html(
                f"<a href=\"/admin/storage/sourcelist/{str(source.source_list.id)}/ \"target=\"_blank\">{source.source_list}</a>")
        else:
            return "-"

    def source_union_list_url(self, source: Source):
        if source.source_union_list != None:
            return format_html(
                f"<a href=\"/admin/storage/source/?source_union_list__id__exact={str(source.source_union_list.id)} \"target=\"_blank\">{source.source_union_list}</a>")
        else:
            return "-"

    source_list_url.short_description = "SOURCE LIST"
    source_union_list_url.short_description = "SOURCE UNION LIST"


admin.site.register(UnionType)
admin.site.register(SourceSystem)
admin.site.register(SourceScheme)
admin.site.register(SourceList, SourceListAdmin)
admin.site.register(Source, SourceAdmin)
admin.site.register(FieldList, FieldListAdmin)
admin.site.register(Field, FieldAdmin)
admin.site.register(Query, QueryAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(ReportVersion, ReportVersionAdmin)
admin.site.register(Metadata, MetadataAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Rule, RuleAdmin)

dgf_admin.register(SourceList, SourceListAdmin)
dgf_admin.register(Source, SourceAdmin)
dgf_admin.register(FieldList, FieldListAdmin)
dgf_admin.register(Field, FieldAdmin)
dgf_admin.register(Query, QueryAdmin)
dgf_admin.register(Report, ReportAdmin)
dgf_admin.register(ReportVersion, ReportVersionAdmin)
dgf_admin.register(Metadata, MetadataAdmin)
dgf_admin.register(Role, RoleAdmin)
dgf_admin.register(Rule, RuleAdmin)
