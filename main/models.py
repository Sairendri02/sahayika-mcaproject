from django.db import models
from datetime import date

class District(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Village(models.Model):
    name = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Register(models.Model):
    ROLE_CHOICES = [
        ("President", "President"),
        ("Member", "Member"),
    ]

    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Left", "Left"),
    ]
    fullname = models.CharField(max_length=100)
    shgname = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True)
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True)
    role = models.CharField(max_length=20)
    phone = models.CharField(max_length=15)
    password = models.CharField(max_length=100)
    aadhaar_number = models.CharField(max_length=12, unique=True, null=True, blank=True)
    aadhaar_photo = models.ImageField(upload_to='aadhaar_photos/', null=True, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True,blank=True)
    joined_date = models.DateTimeField(auto_now_add=True)
    dob = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Active")
    left_date = models.DateField(null=True, blank=True)

    @property
    def age(self):
        if self.dob:
            today = date.today()
            return today.year - self.dob.year - (
                (today.month, today.day) < (self.dob.month, self.dob.day)
            )
        return None
    def __str__(self):
        return self.fullname
    
    class Meta:
         unique_together = ('phone','shgname')
    

class Loan(models.Model):
    LOAN_TYPES = (
        ('Group', 'Group'),
        ('Personal', 'Personal'),
    )

    shgname = models.CharField(max_length=100)
    loan_type = models.CharField(max_length=10, choices=LOAN_TYPES)

    member = models.ForeignKey(
        'Register',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    amount = models.FloatField(default=0)
    paid = models.FloatField(default=0)
    remaining = models.FloatField(default=0)

    duration = models.IntegerField(default=0)
    interest_rate = models.FloatField(default=0)
    subvention_rate = models.FloatField(default=0)
    created_at = models.DateField(auto_now_add=True, null=True, blank=True)
    total_payable = models.FloatField(default=0)

    def save(self, *args, **kwargs):
        self.total_payable = self.amount + (
            self.amount * (self.interest_rate - self.subvention_rate) * self.duration
        ) / 100

        self.remaining = self.total_payable - self.paid

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.loan_type} - {self.amount}"

class MeetingSchedule(models.Model):
    shgname = models.CharField(max_length=100)
    meeting_date = models.DateField()

    def __str__(self):
        return f"{self.shgname} - {self.meeting_date}"

class MonthlyRecord(models.Model):
    shgname = models.CharField(max_length=100)
    member = models.ForeignKey('Register', on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()  # 1-12
    expected_contribution = models.FloatField(default=100)
    saving_paid = models.FloatField(default=0)
    group_emi = models.FloatField(default=0)   
    personal_emi = models.FloatField(default=0) 
    personal_loan_taken = models.FloatField(default=0)
    loan_paid = models.FloatField(default=0)

    @property
    def remaining_contribution(self):
        return max(self.expected_contribution - self.saving_paid, 0)

    @property
    def contribution_status(self):
        return "Paid" if self.remaining_contribution <= 0 else "Pending"

    @property
    def remaining_loan(self):
        return max(self.personal_loan_taken - self.loan_paid, 0)

    @property
    def loan_status(self):
        return "Cleared" if self.remaining_loan <= 0 else "Pending"
    


class Project(models.Model):
    shgname = models.CharField(max_length=100)

    title = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='project_photos/')

    investment = models.FloatField()
    profit = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
