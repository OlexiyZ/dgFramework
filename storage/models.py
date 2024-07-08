from django.db import models
# from django.contrib.postgres.fields import ArrayField
# from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import UniqueConstraint


# from django.core.exceptions import ValidationError

# Create your models here.
class UnionType(models.Model):
    union_type = models.CharField(max_length=15, unique=True)

    def __str__(self):
        return self.union_type


class SourceSystem(models.Model):
    source_system_name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.source_system_name


class SourceScheme(models.Model):
    source_scheme_name = models.CharField(max_length=30, unique=True)
    source_system = models.ForeignKey(SourceSystem, on_delete=models.CASCADE)

    def __str__(self):
        return self.source_scheme_name


class SourceList(models.Model):
    source_list = models.CharField(max_length=30, unique=True)
    source_list_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.source_list


class Source(models.Model):
    SOURCE_TYPES = (
        ('tbd', 'To be defined'),
        ('table', 'Table'),
        ('data_source', 'Data Source'),
        ('query', 'Query'),
    )

    source_union_list = models.ForeignKey(SourceList, on_delete=models.CASCADE,
                                               related_name='source_list_names')
    source_alias = models.CharField(max_length=30)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPES, default='tbd')
    query_name = models.ForeignKey("Query", on_delete=models.SET_NULL, null=True, blank=True)
    source_list = models.ForeignKey(SourceList, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='source_names')
    table_name = models.CharField(max_length=30, blank=True, null=True)
    source_system = models.ForeignKey(SourceSystem, on_delete=models.SET_NULL, null=True, blank=True)
    source_scheme = models.ForeignKey(SourceScheme, on_delete=models.SET_NULL, null=True, blank=True)
    union_type = models.ForeignKey(UnionType, on_delete=models.SET_NULL, null=True, blank=True)
    union_condition = models.TextField(max_length=255, null=True, blank=True)
    source_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return str(self.source_union_list) + "." + str(self.source_alias)


class FieldList(models.Model):
    data_source = models.ForeignKey(SourceList, on_delete=models.CASCADE)
    field_list_name = models.CharField(max_length=255)
    field_list_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.field_list_name


class Field(models.Model):
    FIELD_SOURCE_TYPES = (
        ('tbd', 'To be defined'),
        ('data_source', 'Data Source'),
        ('function', 'Function'),
        ('value', 'Value'),
    )

    field_list = models.ForeignKey(FieldList, on_delete=models.CASCADE)
    source_list = models.ForeignKey(SourceList, on_delete=models.CASCADE, blank=True, null=True)
    field_alias = models.CharField(max_length=30)
    field_source_type = models.CharField(max_length=30, choices=FIELD_SOURCE_TYPES, default='tbd')
    field_source = models.ForeignKey(Source, on_delete=models.CASCADE, blank=True, null=True)
    field_name = models.CharField(max_length=30, blank=True, null=True)
    field_value = models.CharField(max_length=30, blank=True, null=True)
    field_function = models.TextField(max_length=255, blank=True, null=True)
    function_field_list = models.CharField(max_length=255, blank=True, null=True)
    field_description = models.TextField(blank=True, null=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['field_list', 'field_alias'], name='field_constraint')
        ]

    def __str__(self):
        return str(self.field_list) + "." + str(self.field_alias)


class Query(models.Model):
    query_name = models.CharField(max_length=30)
    field_list = models.ForeignKey(FieldList, on_delete=models.CASCADE, blank=True, null=True)
    source_list = models.ForeignKey(SourceList, on_delete=models.CASCADE, blank=True, null=True)
    query_conditions = models.TextField(blank=True, null=True)
    query_alias = models.CharField(max_length=30, blank=True, null=True)
    query_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.query_name


class Report(models.Model):
    report_name = models.CharField(max_length=30)
    field_list = models.ForeignKey(FieldList, on_delete=models.CASCADE, blank=True, null=True)
    source_list = models.ForeignKey(SourceList, on_delete=models.CASCADE, blank=True, null=True)
    report_description = models.TextField(blank=True, null=True)
    report_url = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=10, null=True)
    change_description = models.TextField(blank=True, null=True)
    change_date = models.TextField(blank=True, null=True)
    changed_by = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.report_name


class Test(models.Model):
    report_name = models.CharField(max_length=30)
    field_list = models.ForeignKey(FieldList, on_delete=models.CASCADE, blank=True, null=True)
    source_list = models.ForeignKey(SourceList, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.report_name
