from django.shortcuts import render,redirect
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import JsonResponse
from django.db.models import Sum, Q
from .models import ContactMessage 
from .models import Register, District , Village, Loan, Meeting, Project
from datetime import datetime, date
import random
import re


def home(request):
    return render(request, 'index.html')


def register(request):
    districts = District.objects.all()
    error = ""
    success = ""
    fullname = ""
    shgname = "" 
    phone = ""
    role = ""
    district_id = ""
    village_id = ""

    
    if request.method == "POST" and "send_otp" in request.POST:
        phone = request.POST.get("phone")
        if not phone or not re.fullmatch(r'\d{10}', phone):
            error = _("Enter a valid 10-digit phone number to send OTP")
        else:
            otp = str(random.randint(100000, 999999))
            request.session["otp"] = otp
            # Here you can integrate SMS API to send otp to the phone
            print(f"OTP for {phone}: {otp}")  # For testing
            success = _(f"OTP sent to {phone}")
        return render(request, "register.html", {"districts": districts, "error": error, "success": success})

    
    if request.method == "POST" and "register" in request.POST:
        fullname = request.POST.get('fullname', '').strip()
        shgname = request.POST.get('shgname', '').strip()
        district_id = request.POST.get('district', '').strip()
        village_id = request.POST.get('village', '').strip()
        role = request.POST.get('role','').strip()
        phone = request.POST.get('phone','').strip()
        password = request.POST.get('password','').strip()
        otp_input = request.POST.get("otp",'').strip()
        aadhar_number = request.POST.get('aadhar_number','').strip()
        aadhar_photo = request.FILES.get('aadhar_photo','').strip()
        profile_photo = request.FILES.get('profile_photo','').strip()

        
        if not all([fullname, shgname, district_id, village_id, role, phone, password, otp_input]):
            error = _("All fields including OTP are required")

       
        elif not re.fullmatch(r'\d{10}', phone):
            error = _("Enter a valid 10-digit phone number")

        else:
            district = District.objects.get(id=district_id)
            village = Village.objects.get(id=village_id)

            
            group_members = Register.objects.filter(shgname=shgname , village=village )

# If president tries to create a group that already exists
            if role == "President" and group_members.exists():
                            error = _("This SHG group already exists.")

# If member tries to join a group that doesn't exist
            elif role == "Member" and not group_members.exists():
                           error = _("This SHG group does not exist. Contact the president.")


            elif group_members.count() >= 15:
                error=_("This SHG group already has 15 members. No more members allowed.")
            
            elif role.lower() == "president" and Register.objects.filter(shgname=shgname, role="president").exists():
                error = _("This group already has a president")

           
            
            
            elif otp_input != request.session.get("otp"):
                error = _("Invalid OTP")


            elif not all([aadhar_number, aadhar_photo, profile_photo]):
               error = "All fields are required."
            elif not re.fullmatch(r'\d{12}', aadhar_number):
                error = "Invalid Aadhaar number"
          

            else:
                Register.objects.create(
                    fullname=fullname,
                    shgname=shgname,
                    district=district,
                    village=village,
                    role=role,
                    phone=phone,
                    password=password,
                    aadhar_number=aadhar_number,
                    aadhar_photo=aadhar_photo,
                    profile_photo=profile_photo
                  )
                success = _("Registered successfully!")
                request.session.pop("otp", None)  # Clear OTP after success

    return render(request, "register.html", {"districts": districts, "error": error, "success": success,"fullname":fullname,"shgname":shgname,"phone":phone,"role":role,"district_id":district_id,"village_id":village_id})
    


def load_villages(request):
    district_id = request.GET.get('district')
    villages = Village.objects.filter(district_id=district_id).values('id', 'name')
    return JsonResponse(list(villages), safe=False)


def login_view(request):
    error = ""
    phone = ""
    shgname = ""
    role = ""

    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        shgname = request.POST.get("shgname", "").strip()
        role = request.POST.get("role", "").strip()
        password = request.POST.get("password", "").strip()

        # Check if group exists
        try:
           user = Register.objects.get(
           phone=phone,
           shgname=shgname,
           role__iexact=role
                 )
        except Register.DoesNotExist:
           error = _("User not found in this SHG group.")
        else:
           if user.password.strip() != password.strip():
            error = _("Incorrect password.")
           else:
                # Check role
                if user.role.lower() != role.lower():
                    if role == "President":
                        error = _("You are not registered as President.")
                    else:
                        error = _("You are not registered as Member.")
                # Check password
                elif user.password != password:
                    error = _("Incorrect password.")
                else:
                    # Login success
                    request.session["user_id"] = user.id
                    request.session["user_name"] = user.fullname
                    request.session["user_shg"] = user.shgname
                    request.session["user_role"] = user.role
                    request.session["user_phone"] = user.phone

                    return redirect("dashboard")  # single dashboard for both roles

    return render(request, "login.html", {
        "error": error,
        "phone": phone,
        "shgname": shgname,
        "role": role
    })
def forgot_password(request):

    message = ""

    if request.method == "POST":

        phone = request.POST.get("phone")
        shgname = request.POST.get("shgname")
        new_password = request.POST.get("password")

        try:
            user = Register.objects.get(phone=phone, shgname=shgname)
            user.password = new_password
            user.save()
            message = _("Password updated successfully")
        except Register.DoesNotExist:
            message = _("User not found")

    return render(request,"forgot_password.html",{"message":message})


def add_collection(request):

    shg = request.session.get("user_shg")
    role = request.session.get("user_role")

    members = Register.objects.filter(shgname=shg)

    # Only president can submit
    if request.method == "POST":
        if role != "President":
            return redirect("add_collection")

        member_id = request.POST.get("member_id")
        savings = float( request.POST.get("savings",0))
        emi = float(request.POST.get("emi",0))
        member = Register.objects.get(id=member_id)

        Meeting.objects.create(
            shgname=shg,
            member_name=member.fullname,
            meeting_date=date.today(),
            savings_paid=savings,
            emi_paid=emi
            
             )
        try:
            member = Register.objects.get(fullname=member.fullname, shgname=shg)
            member.savings_total += savings
            member.save()
        except Register.DoesNotExist:
            pass  # Optional: handle error if member not foun
        

        return redirect("add_collection")

    collections = Meeting.objects.filter(shgname=shg)
    

    return render(request, "add_collection.html", {
        "members": members,
        "collections": collections,
        "role": role
       })

def dashboard(request):
    user_role = request.session.get("user_role")
    user_shg = request.session.get("user_shg")
    user_name = request.session.get("user_name")

    members = Register.objects.filter(shgname=user_shg)
    total_members = members.count()

    # Loans for SHG
    loans = Loan.objects.filter(shgname=user_shg)
    total_loans_amount = loans.aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0
    remaining_loans_amount = loans.aggregate(Sum('remaining_amount'))['remaining_amount__sum'] or 0
    total_loans_count = loans.count()
    paid_loans_count = loans.filter(remaining_amount=0).count()

    # Savings and EMI for SHG
    total_savings = Meeting.objects.filter(shgname=user_shg).aggregate(Sum('savings_paid'))['savings_paid__sum'] or 0
    total_emi = Meeting.objects.filter(shgname=user_shg).aggregate(Sum('emi_paid'))['emi_paid__sum'] or 0

    current_month = datetime.now().month
    current_year = datetime.now().year

    # Prepare member_data
    member_data = []
    for m in members:
        member_meetings = Meeting.objects.filter(shgname=user_shg, member_name=m.fullname)
        member_total_savings = member_meetings.aggregate(Sum('savings_paid'))['savings_paid__sum'] or 0
        member_total_emi = member_meetings.aggregate(Sum('emi_paid'))['emi_paid__sum'] or 0

        member_loans = loans.filter(member_name=m.fullname)
        loan_taken = member_loans.aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0
        loan_remaining = member_loans.aggregate(Sum('remaining_amount'))['remaining_amount__sum'] or 0

        member_data.append({
            "fullname": m.fullname,
            "phone": m.phone,
            "aadhar_number": m.aadhar_number,
            "aadhar_photo": m.aadhar_photo.url if m.aadhar_photo and m.aadhar_photo.name else None,
            "profile_photo": m.profile_photo.url if m.profile_photo and m.profile_photo.name else None,
            "total_savings": member_total_savings,
            "total_emi": member_total_emi,
            "loan_taken": loan_taken,
            "loan_remaining": loan_remaining,
            "pending_status": "Paid" if member_total_savings >= 100 else "Pending",
            "loan_status": "Cleared" if loan_remaining == 0 else "Pending",
        })

    # Count of paid/pending savings
    savings_paid_members = Meeting.objects.filter(
        shgname=user_shg,
        meeting_date__month=current_month,
        meeting_date__year=current_year,
        savings_paid__gt=0
    ).values_list('member_name', flat=True).distinct()
    savings_paid_count = len(savings_paid_members)
    savings_pending_count = total_members - savings_paid_count
    savings_paid_percent = (savings_paid_count / total_members * 100) if total_members else 0
    savings_pending_percent = (savings_pending_count / total_members * 100) if total_members else 0

    # Count of paid/pending EMI
    emi_paid_members = Meeting.objects.filter(
        shgname=user_shg,
        meeting_date__month=current_month,
        meeting_date__year=current_year,
        emi_paid__gt=0
    ).values_list('member_name', flat=True).distinct()
    emi_paid_count = len(emi_paid_members)
    emi_pending_count = total_members - emi_paid_count
    emi_paid_percent = (emi_paid_count / total_members * 100) if total_members else 0
    emi_pending_percent = (emi_pending_count / total_members * 100) if total_members else 0

    # Recent activities
    recent_meetings = Meeting.objects.filter(
       shgname=user_shg,
       meeting_date__month=current_month,
       meeting_date__year=current_year
          ).order_by('-meeting_date')[:5]
    recent_activities = [f"{m.member_name} paid ₹{m.savings_paid} savings, ₹{m.emi_paid} EMI" for m in recent_meetings]

    # Financial health
    total_money = total_savings + total_loans_amount
    savings_percent = (total_savings / total_money * 100) if total_money else 0
    loan_percent = (remaining_loans_amount / total_money * 100) if total_money else 0

    # Active loans
    active_loans = loans.filter(remaining_amount__gt=0).count()

    # Total monthly collection
    total_monthly_collection = Meeting.objects.filter(
        shgname=user_shg,
        meeting_date__month=current_month,
        meeting_date__year=current_year
    ).aggregate(Sum('savings_paid'))['savings_paid__sum'] or 0

    # Repayment rate
    repayment_rate = (paid_loans_count / total_loans_count * 100) if total_loans_count else 0

    meeting = Meeting.objects.filter(
             shgname=user_shg
             ).order_by('-id').first()
    context = {
        "user_role": user_role,
        "user_name": user_name,
        "user_shg": user_shg,
        "members": members,
        "member_data": member_data,
        "meeting":meeting,
        "loans": loans,
        "total_members": total_members,
        "total_savings": total_savings,
        "total_emi": total_emi,
        "total_loans_amount": total_loans_amount,
        "remaining_loans_amount": remaining_loans_amount,
        "paid_loans_count": paid_loans_count,
        "active_loans": active_loans,
        "savings_paid_count": savings_paid_count,
        "savings_pending_count": savings_pending_count,
        "savings_paid_percent": savings_paid_percent,
        "savings_pending_percent": savings_pending_percent,
        "emi_paid_count": emi_paid_count,
        "emi_pending_count": emi_pending_count,
        "emi_paid_percent": emi_paid_percent,
        "emi_pending_percent": emi_pending_percent,
        "recent_activities": recent_activities,
        "savings_percent": savings_percent,
        "loan_percent": loan_percent,
        "total_monthly_collection": total_monthly_collection,
        "repayment_rate": repayment_rate,
    }

    return render(request, "dashboard.html", context)
                

def add_member(request):
    # Only President can add members
    if request.session.get("user_role") != "President":
        return redirect("dashboard")  

    if request.method == "POST":
        fullname = request.POST.get("fullname", "").strip()
        phone = request.POST.get("phone", "").strip()
        aadhaar_number = request.POST.get("aadhaar_number", "").strip()

        # Simple Aadhaar validation
        if aadhaar_number and (not aadhaar_number.isdigit() or len(aadhaar_number) != 12):
            messages.error(request, "Aadhaar must be exactly 12 digits")
            return redirect("add_member")

        # Create Register instance
        register = Register(
            fullname=fullname,
            phone=phone,
            aadhaar_number=aadhaar_number or None,
            shgname=request.session.get("user_shg"),
        )

        # Save uploaded photos if provided
        if "aadhaar_photo" in request.FILES:
            register.aadhaar_photo = request.FILES["aadhaar_photo"]
        if "member_photo" in request.FILES:
            register.member_photo = request.FILES["member_photo"]
        if "president_photo" in request.FILES:
            register.president_photo = request.FILES["president_photo"]

        register.save()
        messages.success(request, "Member added successfully")
        return redirect("dashboard")

    # Render the page if GET
    return render(request, "add_member.html")


def delete_member(request, id):
    # Block non-president users
    if request.session.get("user_role") != "President":
        return redirect("dashboard")

    try:
        member = Register.objects.get(id=id)

        # Extra security: only delete within same SHG
        if member.shgname != request.session.get("user_shg"):
            return redirect("dashboard")

        member.delete()

    except Register.DoesNotExist:
        pass

    return redirect("dashboard")

def add_loan(request):
    if request.session.get("user_role") != "President":
        return redirect("dashboard")  # Only President

    shgname = request.session.get("user_shg")
    members = Register.objects.filter(shgname__iexact=shgname.strip())

    if request.method == "POST":
        loan_type = request.POST.get("loan_type")
        amount = float(request.POST.get("amount") or 0)
        paid = float(request.POST.get("paid") or 0)
        remaining = float(request.POST.get("remaining", amount - paid))
        emi_date = request.POST.get("emi_date")
        total_installment = int(request.POST.get("total_installment") or 0)
        interest_rate = float(request.POST.get("interest_rate") or 0)
        subsidy = float(request.POST.get("subsidy") or 0)

        if loan_type == "Personal":
           member_id = request.POST.get("member_id")
           if not member_id:
              messages.error(request, "Select a member")
              return redirect("add_loan")

           member = Register.objects.get(id=member_id)
           member_name = member.fullname

        else:
          member_name = None # only if model allows null

        try:
            amount = float(amount)
            total_installment = int(total_installment)
            interest_rate = float(interest_rate)
            subsidy = float(subsidy)
        except ValueError:
            messages.error(request, "Invalid input values")
            return redirect("add_loan")

        if amount <= 0:
            messages.error(request, "Loan amount must be greater than 0")
            return redirect("add_loan")

        if not emi_date:
            messages.error(request, "EMI date is required")
            return redirect("add_loan")
        try:
              emi_date = datetime.strptime(emi_date, "%Y-%m-%d").date()
        except:
           messages.error(request, "Invalid date format")
           return redirect("add_loan")
        
        Loan.objects.create(
            shgname=shgname,
            member_name=member_name,
            loan_amount=amount,
            paid_amount=paid,
            remaining_amount=remaining,
            loan_type=loan_type,
            emi_date=emi_date,
            total_installment=total_installment,
            interest_rate=interest_rate,
            subsidy=subsidy
        )
        messages.success(request, "Group loan added successfully")
        return redirect("loan_details")

    return render(request, "add_loan.html", { "members":members})

def meeting_entry(request):

    shgname=request.session.get("user_shg")

    members=Register.objects.filter(shgname=shgname)

    if request.method=="POST":

        member=request.POST.get("member")
        meeting_date_str=request.POST.get("date")
        attendance=request.POST.get("attendance")
        notes=request.POST.get("notes")

        try:
            meeting_date = datetime.strptime(meeting_date_str, "%Y-%m-%d").date()
        except:
            meeting_date = datetime.today().date()

        Meeting.objects.create(
            shgname=shgname,
            member_name=member,
            meeting_date=meeting_date,
            attendance=True if attendance == "Present" else False,
            notes=notes



        
        )

        return redirect("dashboard")

    return render(request,"meeting_entry.html",{"members":members})

def logout_view(request):
    request.session.flush()   # clears all session data
    return redirect("login")

def monthly_collection(request):
    shg = request.session.get("user_shg")
    role = request.session.get("user_role")
    members = Register.objects.filter(shgname=shg)
    # Month-Year filter
    selected_month = request.GET.get("month")
    selected_year = request.GET.get("year")

    today = date.today()

    if selected_month:
      selected_month = int(selected_month)
    else:
      selected_month = today.month

    if selected_year:
      selected_year = int(selected_year)
    else:
      selected_year = today.year
    
    # PRESIDENT INPUT
    if request.method == "POST" and role == "President":
        member_id = request.POST.get("member_id")
        savings = float(request.POST.get("savings", 0))
        emi = float(request.POST.get("emi", 0))
        if member_id:
            member = Register.objects.get(id=member_id)
            member_name = member.fullname
        else:
            member_name = "Group Collection"

        Meeting.objects.create(
            shgname=shg,
            member_name=member_name,
            meeting_date=date.today(),
            savings_paid=savings,
            emi_paid=emi
        )

        # Update individual member total savings if personal
        if member_id:
            member.savings_total += savings
            member.save()

        return redirect(f" /monthly_collection/? month={selected_month} &year={selected_year}")

    # DATA FOR TABLE
    collections = Meeting.objects.filter(shgname=shg, 
                                         meeting_date__month=selected_month,
                                         meeting_date__year=selected_year )
    

    month_records = collections

    total_savings_collection = month_records.aggregate(
     Sum('savings_paid')
     )['savings_paid__sum'] or 0

    total_emi_collection = month_records.aggregate(
     Sum('emi_paid')
    )['emi_paid__sum'] or 0
    paid_members_count = month_records.filter(
    Q(savings_paid__gt=0) | Q(emi_paid__gt=0)
     ).values('member_name').distinct().count()
    # Loans
    personal_loans = Loan.objects.filter(shgname=shg, loan_type="Personal")
    group_loans = Loan.objects.filter(shgname=shg, loan_type="Group")

    personal_loans_taken = personal_loans.aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0
    personal_loans_cleared = personal_loans.filter(remaining_amount=0).count()

    # Table data
    member_data = []
    for m in members:
        member_records = collections.filter(member_name=m.fullname)

    total_savings = member_records.aggregate(
        Sum('savings_paid')
    )['savings_paid__sum'] or 0

    total_emi = member_records.aggregate(
        Sum('emi_paid')
    )['emi_paid__sum'] or 0

    loans = personal_loans.filter(member_name=m.fullname)

    loan_taken = loans.aggregate(
        Sum('loan_amount')
    )['loan_amount__sum'] or 0

    loan_remaining = loans.aggregate(
        Sum('remaining_amount')
    )['remaining_amount__sum'] or 0

    emi_status = "Paid" if total_emi > 0 else "Pending"

    member_data.append({
        "fullname": m.fullname,
        "phone": m.phone,
        "total_savings": total_savings,
        "total_emi": total_emi,
        "emi_status": emi_status,
        "loan_taken": loan_taken,
        "loan_remaining": loan_remaining,
        "last_loan_date": loans.order_by('-loan_date').first().loan_date if loans.exists() else None
    })

    context = {
        "members": members,
        "role": role,
        "total_savings_collection": total_savings_collection,
        "total_emi_collection": total_emi_collection,
        "paid_members_count": paid_members_count,
        "personal_loans_taken": personal_loans_taken,
        "personal_loans_cleared": personal_loans_cleared,
        "member_data": member_data,
        "group_loans": group_loans,
        "selected_month": selected_month,
        "selected_year": selected_year,
    }
    return render(request, "monthly_collection.html", context)

# views.py
def loan_details(request):
    shg = request.session.get("user_shg")
    loan_type = request.GET.get("type")
    member = request.GET.get("member")
    month = request.GET.get("month")
    year = request.GET.get("year")

    now = datetime.now()

    month = int(month) if month else now.month
    year = int(year) if year else now.year

    loans = Loan.objects.filter(
        shgname=shg,
        emi_date__month=month,
        emi_date__year=year
    )
   

    if loan_type == "Group":
        loans = loans.filter(loan_type="Group")

    elif loan_type == "Personal":
        loans = loans.filter(loan_type="Personal")

        if member:
            loans = loans.filter(member_name=member)

    return render(request, "loan_details.html", {
        "loans": loans,
        "members": Register.objects.filter(shgname=shg),
        "selected_month": month,
        "selected_year": year,
    })

def add_project(request):
    if request.session.get("user_role") != "President":
        return redirect("project_list")

    if request.method == "POST":
        title = request.POST.get("title")
        investment = request.POST.get("investment")
        profit = request.POST.get("profit")
        photo = request.FILES.get("photo")

        Project.objects.create(
            title=title,
            investment=investment,
            profit=profit,
            photo=photo,
            shgname=request.session.get("user_shg")
        )

        return redirect("project_list")

    return render(request, "add_project.html")

def project_list(request):
    projects = Project.objects.filter(
        shgname=request.session.get("user_shg")
    )

    return render(request, "project_list.html", {
        "projects": projects,
        "user_role": request.session.get("user_role")
    })

def learn_more(request):
    return render(request, 'learn_more.html')

def home(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def rti(request):
    return render(request, 'rti.html')

def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        print(name, phone, subject, message)

        messages.success(request, "Message sent successfully")

    return render(request, "contact.html")


def contact_view(request):
    phone = request.session.get("user_phone")

    if request.method == "POST":
        ContactMessage.objects.create(
            name=request.POST.get('name'),
            phone=request.POST.get('phone'),
            email=request.POST.get('email'),
            subject=request.POST.get('subject'),
            message=request.POST.get('message'),
            type=request.POST.get('type', 'Complaint')
        )
        messages.success(request, "Message sent successfully")
        return redirect('contact')

    submissions = ContactMessage.objects.filter(phone=phone).order_by('-created_at')

    return render(request, "contact.html", {
        "submissions": submissions
    })
  

    