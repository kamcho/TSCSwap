from django import forms
from .models import MySubject, Subject, Swaps, Counties, Constituencies, Wards, Schools, Level, Curriculum, SwapPreference, FastSwap


class MySubjectForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get the user's level from their profile if available
        user_level = None
        if hasattr(user, 'profile') and hasattr(user.profile, 'level'):
            user_level = user.profile.level
        
        # Filter subjects by user's level if available, otherwise show all
        if user_level:
            self.fields['subject'].queryset = Subject.objects.filter(level=user_level).order_by('name')
            
            # Get user's current subjects and set initial values
            current_subjects = Subject.objects.filter(
                mysubject__user=user
            ).values_list('id', flat=True)
            self.initial['subject'] = list(current_subjects)
        else:
            self.fields['subject'].queryset = Subject.objects.all().order_by('name')
    
    subject = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(),  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Subjects",
    )

    class Meta:
        model = MySubject
        fields = ["subject"]


class FastSwapForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['school'].queryset = Schools.objects.all().order_by('name')
        self.fields['most_preferred'].queryset = Counties.objects.all().order_by('name')
        self.fields['acceptable_county'].queryset = Counties.objects.all().order_by('name')
        # Only show Secondary/High School subjects
        self.fields['subjects'].queryset = Subject.objects.filter(
            level__name="Secondary/High School"
        ).order_by('name')
        self.fields['current_county'].queryset = Counties.objects.all().order_by('name')
        
        # Make fields required
        self.fields['names'].required = True
        self.fields['phone'].required = True
        self.fields['school'].required = False  # Now optional since we have current location
        self.fields['level'].required = True
        self.fields['subjects'].required = False  # Only for secondary
        self.fields['current_county'].required = True
        
        # Set up cascading dropdowns for current location
        self.fields['current_constituency'].queryset = Constituencies.objects.none()
        self.fields['current_ward'].queryset = Wards.objects.none()
        
        if 'current_county' in self.data:
            try:
                county_id = int(self.data.get('current_county'))
                self.fields['current_constituency'].queryset = Constituencies.objects.filter(county_id=county_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.current_county:
            self.fields['current_constituency'].queryset = Constituencies.objects.filter(county=self.instance.current_county).order_by('name')
                
        if 'current_constituency' in self.data:
            try:
                constituency_id = int(self.data.get('current_constituency'))
                self.fields['current_ward'].queryset = Wards.objects.filter(constituency_id=constituency_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.current_constituency:
            self.fields['current_ward'].queryset = Wards.objects.filter(constituency=self.instance.current_constituency).order_by('name')

    class Meta:
        model = FastSwap
        fields = ['names', 'phone', 'school', 'current_county', 'current_constituency', 'current_ward', 'most_preferred', 'acceptable_county', 'level', 'subjects']
        widgets = {
            'acceptable_county': forms.CheckboxSelectMultiple(),
            'subjects': forms.CheckboxSelectMultiple(),
            'names': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'school': forms.Select(attrs={'class': 'form-select'}),
            'current_county': forms.Select(attrs={'class': 'form-select'}),
            'current_constituency': forms.Select(attrs={'class': 'form-select'}),
            'current_ward': forms.Select(attrs={'class': 'form-select'}),
            'most_preferred': forms.Select(attrs={'class': 'form-select'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
        }


class SwapForm(forms.ModelForm):
    gender = forms.ChoiceField(
        choices=Swaps.Gender,
        label="Preferred school gender",
        widget=forms.Select(attrs={"class": "swap-input"}),
    )
    boarding = forms.ChoiceField(
        choices=Swaps.Boarding,
        label="Preferred boarding type",
        widget=forms.Select(attrs={"class": "swap-input"}),
    )
    county = forms.ModelChoiceField(
        queryset=Counties.objects.all().order_by('name'),
        required=True,
        label="Target county *",
        help_text="Required field",
        widget=forms.Select(attrs={"class": "swap-input"}),
    )
    constituency = forms.ModelChoiceField(
        queryset=Constituencies.objects.none(),
        required=False,
        label="Target constituency (optional)",
        help_text="Optional - Select a county first to see available constituencies",
        widget=forms.Select(attrs={"class": "swap-input"}),
    )
    
    ward = forms.ModelChoiceField(
        queryset=Wards.objects.none(),
        required=False,
        label="Target ward (optional)",
        help_text="Optional - Select a constituency first to see available wards",
        widget=forms.Select(attrs={"class": "swap-input"}),
    )

    class Meta:
        model = Swaps
        fields = ["gender", "boarding", "county", "constituency", "ward"]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['constituency'].queryset = Constituencies.objects.none()
        self.fields['ward'].queryset = Wards.objects.none()
        
        if 'county' in self.data:
            try:
                county_id = int(self.data.get('county'))
                self.fields['constituency'].queryset = Constituencies.objects.filter(county_id=county_id).order_by('name')
            except (ValueError, TypeError):
                pass
                
        if 'constituency' in self.data:
            try:
                constituency_id = int(self.data.get('constituency'))
                self.fields['ward'].queryset = Wards.objects.filter(constituency_id=constituency_id).order_by('name')
            except (ValueError, TypeError):
                pass


class SchoolForm(forms.ModelForm):
    county = forms.ModelChoiceField(
        queryset=Counties.objects.all().order_by('name'),
        required=True,
        label="County"
    )
    
    constituency = forms.ModelChoiceField(
        queryset=Constituencies.objects.none(),
        required=False,
        label="Constituency"
    )
    
    ward = forms.ModelChoiceField(
        queryset=Wards.objects.all(),
        required=True,
        label="Ward"
    )
    
    class Meta:
        model = Schools
        fields = ['name', 'gender', 'level', 'boarding', 'curriculum', 'postal_code', 'ward']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500'}),
            'gender': forms.Select(attrs={'class': 'form-select mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500'}),
            'level': forms.Select(attrs={'class': 'form-select mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500'}),
            'boarding': forms.Select(attrs={'class': 'form-select mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500'}),
            'curriculum': forms.Select(attrs={'class': 'form-select mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500'}),
            'ward': forms.Select(attrs={'class': 'form-select mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500'}),
            'county': forms.HiddenInput(),
            'constituency': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Order the choices in the dropdowns
        self.fields['level'].queryset = Level.objects.all().order_by('name')
        self.fields['curriculum'].queryset = Curriculum.objects.all().order_by('name')
        
        # Set initial values if we're editing an existing school
        if self.instance and self.instance.pk and self.instance.ward:
            self.fields['county'].initial = self.instance.ward.constituency.county
            self.fields['constituency'].queryset = Constituencies.objects.filter(county=self.instance.ward.constituency.county)
            self.fields['constituency'].initial = self.instance.ward.constituency
            self.fields['ward'].queryset = Wards.objects.filter(constituency=self.instance.ward.constituency)
        else:
            # Initialize with empty querysets for new forms
            self.fields['constituency'].queryset = Constituencies.objects.none()
            self.fields['ward'].queryset = Wards.objects.none()
            
            # If we have county in the POST data, update the constituency queryset
            if 'county' in self.data:
                try:
                    county_id = int(self.data.get('county'))
                    self.fields['constituency'].queryset = Constituencies.objects.filter(county_id=county_id).order_by('name')
                    
                    # If we also have a constituency in POST data, update the ward queryset
                    if 'constituency' in self.data:
                        try:
                            constituency_id = int(self.data.get('constituency'))
                            self.fields['ward'].queryset = Wards.objects.filter(constituency_id=constituency_id).order_by('name')
                        except (ValueError, TypeError):
                            pass
                except (ValueError, TypeError):
                    pass
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Ensure the selected ward exists
        ward = cleaned_data.get('ward')
        if not ward:
            raise forms.ValidationError({
                'ward': 'Please select a valid ward.'
            })
            
        return cleaned_data
        
        help_texts = {
            'postal_code': 'Enter the postal code of the school',
        }
        
        # If we're editing an existing instance, set the querysets based on the instance's data
        if self.instance and self.instance.ward_id:
            self.fields['ward'].queryset = Wards.objects.filter(
                constituency=self.instance.ward.constituency
            ).order_by('name')


class SwapPreferenceForm(forms.ModelForm):
    county = forms.ModelChoiceField(
        queryset=Counties.objects.all().order_by('name'),
        required=False,
        label="Preferred County",
        help_text="Select your preferred county for swapping",
        widget=forms.Select(attrs={"class": "form-select mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500"}),
    )
    
    constituency = forms.ModelChoiceField(
        queryset=Constituencies.objects.none(),
        required=False,
        label="Preferred Constituency (Optional)",
        help_text="Optionally select a specific constituency",
        widget=forms.Select(attrs={"class": "form-select mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500"}),
    )
    
    ward = forms.ModelChoiceField(
        queryset=Wards.objects.none(),
        required=False,
        label="Preferred Ward (Optional)",
        help_text="Optionally select a specific ward",
        widget=forms.Select(attrs={"class": "form-select mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500"}),
    )
    
    open_to_all = forms.BooleanField(
        required=False,
        label="Open to All Counties",
        help_text="Check this if you're willing to swap to any county in Kenya",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox h-5 w-5 text-teal-600 rounded border-gray-300 focus:ring-teal-500"}),
    )
    
    is_hardship = forms.ChoiceField(
        choices=SwapPreference.Hardship,
        required=True,
        label="Hardship Area Preference",
        help_text="Are you willing to swap to a hardship area?",
        widget=forms.Select(attrs={"class": "form-select mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-teal-500 focus:ring-teal-500"}),
    )

    class Meta:
        model = SwapPreference
        fields = ['county', 'constituency', 'ward', 'open_to_all', 'is_hardship']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up the querysets for constituency and ward fields
        if 'county' in self.data:
            try:
                county_id = int(self.data.get('county'))
                self.fields['constituency'].queryset = Constituencies.objects.filter(
                    county_id=county_id
                ).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.desired_county:
            self.fields['constituency'].queryset = self.instance.desired_county.constituencies_set.order_by('name')
        
        if 'constituency' in self.data:
            try:
                constituency_id = int(self.data.get('constituency'))
                self.fields['ward'].queryset = Wards.objects.filter(
                    constituency_id=constituency_id
                ).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.desired_constituency:
            self.fields['ward'].queryset = self.instance.desired_constituency.wards_set.order_by('name')
        
        # Set initial values if editing an existing instance
        if self.instance.pk:
            if self.instance.desired_county:
                self.fields['county'].initial = self.instance.desired_county
            if self.instance.desired_constituency:
                self.fields['constituency'].initial = self.instance.desired_constituency
            if self.instance.desired_ward:
                self.fields['ward'].initial = self.instance.desired_ward
    
    def save(self, commit=True):
        # Get the unsaved instance
        instance = super().save(commit=False)
        
        # Map the form fields to the model fields
        instance.desired_county = self.cleaned_data.get('county')
        instance.desired_constituency = self.cleaned_data.get('constituency')
        instance.desired_ward = self.cleaned_data.get('ward')
        
        if commit:
            instance.save()
        return instance

