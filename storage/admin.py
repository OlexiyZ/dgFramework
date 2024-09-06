from django.contrib import admin
from .models import *
from django.utils.html import format_html

from django.contrib.admin import AdminSite
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.forms import Textarea
from django.db.models import QuerySet
import requests


class DGFAdminSite(AdminSite):
    site_header = _("Data Governance Framework")
    site_title = _("DG Framework Site")
    index_title = _("Welcome to Data Governance Framework Portal")


# Create an instance of the custom admin site
dgf_admin = DGFAdminSite(name='dgf_admin')


# Register your models here.

class RulesInline(admin.TabularInline):
    model = Rule
    extra = 1
    list_display = ('name', 'rule_link', 'value', 'description', 'metadata')
    readonly_fields = ('name', 'rule_link', 'value', 'description', 'metadata')

    def rule_link(self, rule: Rule):
        return format_html(
            f"<a href=\"/admin/storage/rule/{str(rule.id)}/ \"target=\"_blank\">{rule.name}</a>")


class MetadataAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'metadata_rules', 'default_rule_link')
    search_fields = ('name',)
    ordering = ['name']
    inlines = (RulesInline,)

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
    list_display = ('name', 'rule_list', 'description')
    # list_filter = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('rule',)
    ordering = ['name']
    # inlines = (RuleInline,)
    actions = ['send_role']

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3})},
    }

    def rule_list(self, obj):
        return ', '.join([rule.name for rule in obj.rule.all()])

    @admin.action(description='Send Role`s rules to the Proxy')
    def send_role(self, request, roles: QuerySet):
        url = 'http://proxy.test.url'
        count_updated = 0
        count_not_updated = 0
        for role in roles:
            rules = role.rule.all()
            rules_string = ''
            var_counter = 1
            for rule in rules:
                rules_string = rules_string + f"&var{var_counter}=dashboard.variables['{rule.metadata}']&val{var_counter}='{rule.value}'"
                var_counter += 1
            # print(rules_string)
            data = {
                'role': role.name,
                'rules': rules_string
            }
            try:
                response = requests.post(url, json=data)
                if response.status_code == 200:
                    count_updated += 1
                else:
                    count_not_updated += 1
            except Exception as e:
                count_not_updated += 1
                # print("Something went wrong:", e)
        # count_updated = roles.update()
        if count_updated == 0:
            self.message_user(
                request,
                f"{count_updated} Role(s) have been sent to the Proxy. {count_not_updated} was not updated.",
                messages.ERROR
            )
        else:
            self.message_user(
                request,
                f"{count_updated} Role(s) have been sent to the Proxy. {count_not_updated} was not updated."
            )


class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'description', 'metadata')
    list_filter = ('metadata',)
    search_fields = ('name',)


class FieldAdmin(admin.ModelAdmin):
    list_display = (
        'field_alias', 'field_erd', 'field_source_type', 'field_source_url', 'field_name', 'metadata', 'field_value',
        'field_function', 'function_field_list', 'field_list_url', 'source_list_url', 'field_description')
    list_filter = ('metadata', 'field_list', 'source_list')
    search_fields = ('field_alias', 'field_name', 'field_description')
    list_editable = ['metadata']

    def field_erd(self, field: Field):
        return format_html(
            f"<a href=\"/dm/field_diagram/{str(field.field_source_id)}/{str(field.id)}/\" target=\"_blank\">ERD</a>")

    def field_source_url(self, field: Field):
        if field.field_source_type == 'data_source':
            return format_html(
                f"<a href=\"/admin/storage/source/{str(field.field_source.id)}/ \"target=\"_blank\">{field.field_source}</a>")
        else:
            return field.field_source

    def source_list_url(self, field: Field):
        return format_html(
            f"<a href=\"/admin/storage/source/{str(field.source_list.id)}/ \"target=\"_blank\">{field.source_list}</a>")

    def field_list_url(self, field: Field):
        return format_html(
            f"<a href=\"/admin/storage/source/{str(field.field_list.id)}/ \"target=\"_blank\">{field.field_list}</a>")


class FieldsInline(admin.TabularInline):
    model = Field
    extra = 1
    list_display = [
        'field_link', 'field_erd', 'field_source_type', 'field_source', 'field_name', 'metadata', 'field_value',
        'field_function', 'function_field_list', 'field_list', 'source_list', 'field_description']
    readonly_fields = [
        'field_link', 'field_alias', 'field_erd', 'field_source_type', 'field_source', 'field_name', 'metadata',
        'field_value',
        'field_function', 'function_field_list', 'field_list', 'source_list', 'field_description']

    def field_erd(self, field: Field):
        return format_html(
            f"<a href=\"/dm/field_diagram/{str(field.field_source_id)}/{str(field.id)}/\" target=\"_blank\">ERD</a>")

    def field_link(self, field: Field):
        return format_html(
            f"<a href=\"/admin/storage/field/{str(field.id)}/ \"target=\"_blank\">{field.field_alias}</a>")


class FieldListAdmin(admin.ModelAdmin):
    list_display = ('field_list_name', 'datasource_url', 'field_list_description')
    search_fields = ('field_list_name', 'data_source', 'field_list_description')
    inlines = (FieldsInline,)

    def datasource_url(self, field_list: FieldList):
        return format_html(
            f"<a href=\"/admin/storage/sourcelist/{str(field_list.data_source.id)}/ \"target=\"_blank\">{field_list.data_source}</a>")

    datasource_url.short_description = 'DATA SOURCE'


admin.site.register(UnionType)
admin.site.register(SourceSystem)
admin.site.register(SourceScheme)
admin.site.register(SourceList)
admin.site.register(Source)
admin.site.register(FieldList)
admin.site.register(Field, FieldAdmin)
admin.site.register(Query)
admin.site.register(Report)
admin.site.register(Metadata, MetadataAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Rule, RuleAdmin)

dgf_admin.register(SourceList)
dgf_admin.register(Source)
dgf_admin.register(FieldList, FieldListAdmin)
dgf_admin.register(Field, FieldAdmin)
dgf_admin.register(Query)
dgf_admin.register(Report)
dgf_admin.register(Metadata, MetadataAdmin)
dgf_admin.register(Role, RoleAdmin)
dgf_admin.register(Rule, RuleAdmin)
