from django import forms
from storage.models import *


class SourceListForm(forms.ModelForm):
    class Meta:
        model = SourceList
        fields = ['source_list', 'source_list_description']
        widgets = {
            'source_list': forms.TextInput(attrs={'class': 'form-control'}),
            'source_list_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FieldListDisplayForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FieldListDisplayForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].disabled = True  # Disable all fields to make the form read-only

    class Meta:
        model = FieldList
        fields = ['data_source', 'field_list_name', 'field_list_description']


class FieldListForm(forms.ModelForm):
    class Meta:
        model = FieldList
        fields = ['data_source', 'field_list_name', 'field_list_description']
        widgets = {
            'data_source': forms.Select(attrs={'class': 'form-control'}),
            'field_list_name': forms.TextInput(attrs={'class': 'form-control'}),
            'field_list_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FieldDisplayForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FieldDisplayForm, self).__init__(*args, **kwargs)
        for field_name in self.fields:
            field = self.fields.get(field_name)
            if field:
                field.disabled = True  # Make field not editable

    class Meta:
        model = Field
        exclude = []  # Include all model fields in the form



# class FormQuery(forms.Form):
#     query_name = forms.CharField(lable='query_name', max_length=10)
