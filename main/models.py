from django.db import models

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
    fullname = models.CharField(max_length=100)
    shgname = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True)
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True)
    role = models.CharField(max_length=20)
    phone = models.CharField(max_length=15)
    password = models.CharField(max_length=100)
    aadhar_number = models.CharField(max_length=12, unique=True, null=True, blank=True)
    aadhar_photo = models.ImageField(upload_to='aadhar_photos/', null=True, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True,blank=True)
    def __str__(self):
        return self.fullname
    
    class Meta:
         unique_together = ('phone','shgname')
    

class Loan(models.Model):

    shgname = models.CharField(max_length=100,blank=True , null=True )
    member_name = models.CharField(max_length=100, null=True, blank=True)
    loan_amount = models.IntegerField()
    paid_amount = models.IntegerField(default=0)
    remaining_amount = models.IntegerField()
    loan_type = models.CharField(max_length=20,default="Personal")
    emi_date = models.DateField()
    loan_date = models.DateField(auto_now_add=True)
    total_installment = models.IntegerField(default=0)
    interest_rate = models.FloatField(default=0)  
    subsidy = models.FloatField(default=0)

    def __str__(self):
        return self.shgname


class Meeting(models.Model):

    shgname = models.CharField(max_length=100)
    member_name = models.CharField(max_length=100)

    meeting_date = models.DateField()

    attendance = models.BooleanField(default=False)

    savings_paid = models.IntegerField(default=0)

    emi_paid = models.IntegerField(default=0)

    notes = models.TextField(blank=True)

    def __str__(self):
        return self.member_name

class MonthlyRecord(models.Model):
    shgname = models.CharField(max_length=100)
    member = models.ForeignKey('Register', on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()  # 1-12
    expected_contribution = models.FloatField(default=100)
    saving_paid = models.FloatField(default=0)
    emi_paid = models.FloatField(default=0)
    personal_loan_taken = models.FloatField(default=0)
    loan_paid = models.FloatField(default=0)

    @property
    def remaining_contribution(self):
        return max(self.expected_contribution - self.paid_amount, 0)

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
    
class Contact(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

class ContactMessage(models.Model):
    TYPE_CHOICES = (
        ('Message', 'Message'),
        ('Complaint', 'Complaint'),
    )

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True,null=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Complaint')
    reply = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='Pending')  # Pending / Resolved
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} ({self.type})"