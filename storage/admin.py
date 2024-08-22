from django.contrib import admin
from .models import *
from django.utils.html import format_html

from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _
from django.forms import Textarea


class DGFAdminSite(AdminSite):
    site_header = _("Data Governance Framework")
    site_title = _("DG Framework Site")
    index_title = _("Welcome to Data Governance Framework Portal")


# Create an instance of the custom admin site
dgf_admin = DGFAdminSite(name='dgf_admin')


# Register your models here.

# class RuleInline(admin.TabularInline):
#     model = Rule
#     extra = 1

class MetadataAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'metadata_rules', 'default_rule_link')
    search_fields = ('name',)
    ordering = ['name']

    def metadata_rules(self, metadata: Metadata):
        rules = ', '.join([rule.name for rule in metadata.rule_set.all()])
        return format_html(
            f"<a href=\"/storage/rule/?metadata__id__exact={str(metadata.id)}\" target=\"_blank\">{rules}</a>")

    def default_rule_link(self, metadata: Metadata):
        return format_html(
            f"<a href=\"/storage/rule/{str(metadata.default_rule_id)}/\" target=\"_blank\">{str(metadata.default_rule)}</a>")

    default_rule_link.short_description = "DEFAULT RULE"


class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'rule_list', 'description')
    # list_filter = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('rule',)
    ordering = ['name']
    # inlines = (RuleInline,)

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3})},
    }

    def rule_list(self, obj):
        return ', '.join([rule.name for rule in obj.rule.all()])


class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'description', 'metadata')
    list_filter = ('metadata',)
    search_fields = ('name',)


class FieldAdmin(admin.ModelAdmin):
    list_display = ('field_alias', 'field_erd', 'field_source_type', 'field_source_url', 'field_name', 'metadata', 'field_value',
                    'field_function', 'function_field_list', 'field_list_url', 'source_list_url', 'field_description')
    list_filter = ('metadata', 'field_list', 'source_list')
    search_fields = ('field_alias', 'field_name', 'field_description')
    list_editable = ['metadata']

    def field_erd(self, field: Field):
        return format_html(
            f"<a href=\"/dm/field_diagram/{str(field.field_source_id)}/{str(field.id)}/\" target=\"_blank\">ERD</a>")

    def field_source_url(self, field: Field):
        if field.field_source_type == 'data_source':
            return format_html(f"<a href=\"/admin/storage/source/{str(field.field_source.id)}/ \"target=\"_blank\">{field.field_source}</a>")
        else:
            return field.field_source

    def source_list_url(self, field: Field):
        return format_html(f"<a href=\"/admin/storage/source/{str(field.source_list.id)}/ \"target=\"_blank\">{field.source_list}</a>")

    def field_list_url(self, field: Field):
        return format_html(f"<a href=\"/admin/storage/source/{str(field.field_list.id)}/ \"target=\"_blank\">{field.field_list}</a>")


class FieldListAdmin(admin.ModelAdmin):
    list_display = ('field_list_name', 'data_source', 'field_list_description')
    search_fields = ('field_list_name', 'data_source', 'field_list_description')


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
