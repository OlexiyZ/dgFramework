from django.contrib import admin
from .models import *


# Register your models here.

# class RuleInline(admin.TabularInline):
#     model = Rule
#     extra = 1

class MetadataAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'default_rule')
    # list_filter = ('name',)
    search_fields = ('name',)


class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'rule_list', 'description')
    # list_filter = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('rule',)
    # inlines = (RuleInline,)

    def rule_list(self, obj):
        # return ', '.join([rule.name for rule in obj.rule.all()])
        return ', '.join([rule.name for rule in obj.rule.all()])
    # def rule_choice_name(self, obj):
    #     for rule in obj.rule.all():

            # return obj.rule.name + ' ' + obj.rule.description

class RuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'description', 'metadata')
    list_filter = ('metadata',)
    search_fields = ('name',)


admin.site.register(UnionType)
admin.site.register(SourceSystem)
admin.site.register(SourceScheme)
admin.site.register(SourceList)
admin.site.register(Source)
admin.site.register(FieldList)
admin.site.register(Field)
admin.site.register(Query)
admin.site.register(Report)
admin.site.register(Metadata, MetadataAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Rule, RuleAdmin)
