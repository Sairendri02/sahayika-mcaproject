from django import forms
from .models import Loan

class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # disable fields
        self.fields["duration"].disabled = True
        self.fields["si_rate"].disabled = True
        self.fields["subvention_rate"].disabled = True