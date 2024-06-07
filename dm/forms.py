from django import forms
from storage.models import *


# class FieldForm(forms.ModelForm):
#


class SourceListForm(forms.ModelForm):
    class Meta:
        model = SourceList
        fields = ['source_list', 'source_list_description']
        widgets = {
            'source_list': forms.TextInput(attrs={'class': 'form-control'}),
            'source_list_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FieldListForm(forms.ModelForm):
    class Meta:
        model = FieldList
        fields = ['data_source', 'field_list_name', 'field_list_description']
        widgets = {
            'data_source': forms.Select(attrs={'class': 'form-control'}),
            'field_list_name': forms.TextInput(attrs={'class': 'form-control'}),
            'field_list_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FieldForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FieldForm, self).__init__(*args, **kwargs)
        # for field_name, field in self.fields.items():
        #     if isinstance(field, forms.ChoiceField):
        #         field.widget = forms.Select(attrs={'class': 'form-control'})
        #     elif isinstance(field, forms.Textarea):
        #         field.widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        #     else:
        #         field.widget = forms.TextInput(attrs={'class': 'form-control'})
        # self.fields['field_list'].widget.attrs.update({'class': 'form-control'})
        # Apply CSS class to the label
        # lable_test = self.fields['field_list'].label_tag
        self.fields['field_list'].label_tag = self.custom_label_tag(self.fields['field_list'].label, 'bold-label')

    def custom_label_tag(self, label_text, css_class):
        return f'<label class="{css_class}">{label_text}</label>'

    class Meta:
        model = Field
        exclude = []  # Include all model fields in the form
        widgets = {
            'field_list': forms.Select(attrs={'class': 'form-control'}),
            'source_list': forms.Select(attrs={'class': 'form-control'}),
            'field_alias': forms.TextInput(attrs={'class': 'form-control'}),
            'field_source_type': forms.Select(attrs={'class': 'form-control'}),
            'field_source': forms.Select(attrs={'class': 'form-control'}),
            'field_name': forms.TextInput(attrs={'class': 'form-control'}),
            'field_value': forms.TextInput(attrs={'class': 'form-control'}),
            'field_function': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'function_field_list': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'field_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# class FormQuery(forms.Form):
#     query_name = forms.CharField(lable='query_name', max_length=10)
