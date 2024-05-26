from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(UnionType)
admin.site.register(SourceSystem)
admin.site.register(SourceScheme)
admin.site.register(SourceList)
admin.site.register(Source)
admin.site.register(FieldList)
admin.site.register(Field)
admin.site.register(Query)
admin.site.register(Report)
