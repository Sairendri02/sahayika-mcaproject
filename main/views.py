from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from .models import MeetingSchedule
from django.db.models import Sum 
from .models import  MonthlyRecord 
from .models import Register, District , Village, Loan , Project
from .forms import LoanForm
from datetime import datetime, date
import random
import re


def home(request):
    return render(request, 'index.html')


def register(request):
    districts = District.objects.all().order_by('name')

    error = ""
    success = ""

    fullname = request.POST.get("fullname", "")
    shgname = request.POST.get("shgname", "")
    phone = request.POST.get("phone", "")
    role = request.POST.get("role", "")
    district_id = request.POST.get("district", "")
    village_id = request.POST.get("village", "")

    if request.method == "POST":

        # 🔹 SEND OTP
        if "send_otp" in request.POST:
            phone = request.POST.get("phone", "").strip()

            if not re.fullmatch(r'\d{10}', phone):
                error = _("Enter valid phone number")
            else:
                otp = str(random.randint(1000, 9999))
                request.session["otp"] = otp
                print("OTP:", otp)
                success = _("OTP sent successfully")

        # 🔹 REGISTER
        elif "register" in request.POST:

            fullname = request.POST.get('fullname', '').strip()
            shgname = request.POST.get('shgname', '').strip()
            district_id = request.POST.get('district', '').strip()
            village_id = request.POST.get('village', '').strip()
            role = request.POST.get('role','').strip()
            phone = request.POST.get('phone','').strip()
            dob = request.POST.get('dob','').strip()
            password = request.POST.get('password','').strip()
            otp_input = request.POST.get("otp",'').strip()
            aadhaar_number = request.POST.get('aadhaar_number','').strip()
            aadhaar_photo = request.FILES.get('aadhaar_photo')
            profile_photo = request.FILES.get('profile_photo')

            # ✅ VALIDATION
            if not all([fullname, shgname, district_id, village_id, role, phone, password, otp_input]):
                error = _("All fields including OTP are required")

            elif otp_input != request.session.get("otp"):
                error = _("Invalid OTP")

            elif not re.fullmatch(r'\d{10}', phone):
                error = _("Invalid phone")

            elif User.objects.filter(username=phone).exists():
                error = _("User already exists")

            else:
                district = District.objects.get(id=district_id)
                village = Village.objects.get(id=village_id)

                group_members = Register.objects.filter(shgname=shgname, village=village)

                if role == "President" and group_members.exists():
                    error = _("Group already exists")

                elif role == "Member" and not group_members.exists():
                    error = _("Group does not exist")

                elif group_members.count() >= 15:
                    error = _("Max 15 members")

                elif role.lower() == "president" and Register.objects.filter(shgname=shgname, role="president").exists():
                    error = _("President already exists")

                elif not all([aadhaar_number, aadhaar_photo, profile_photo]):
                    error = _("All Aadhaar fields required")

                elif not re.fullmatch(r'\d{12}', aadhaar_number):
                    error = _("Invalid Aadhaar")

                else:
                    # ✅ CREATE USER
                    user = User.objects.create_user(
                        username=phone,
                        password=password
                    )

                    Register.objects.create(
                        fullname=fullname,
                        shgname=shgname,
                        district=district,
                        village=village,
                        role=role,
                        phone=phone,
                        dob=dob,
                        aadhaar_number=aadhaar_number,
                        aadhaar_photo=aadhaar_photo,
                        profile_photo=profile_photo,
                        user=user
                    )

                    success = _("Registered successfully!")
                    request.session.pop("otp", None)

    return render(request, "register.html", {
        "districts": districts,
        "error": error,
        "success": success,
        "fullname": fullname,
        "shgname": shgname,
        "phone": phone,
        "role": role,
        "district_id": district_id,
        "village_id": village_id,
    })
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

        user = authenticate(request, username=phone, password=password)

        if user is None:
            error = "Invalid phone or password"
        else:
            try:
                reg = Register.objects.get(
                    user=user,
                    shgname=shgname,
                    role__iexact=role
                )
            except Register.DoesNotExist:
                error = "Invalid SHG name or role"
            else:
                login(request, user)

                request.session["user_id"] = reg.id
                request.session["user_name"] = reg.fullname
                request.session["user_shg"] = reg.shgname
                request.session["user_role"] = reg.role
                request.session["user_phone"] = reg.phone

                return redirect("dashboard")

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
            reg = Register.objects.get(phone=phone, shgname=shgname)

            user = reg.user   

            user.set_password(new_password) 
            user.save()

            message = "Password updated successfully"

        except Register.DoesNotExist:
            message = "User not found"

    return render(request, "forgot_password.html", {"message": message})

@never_cache
def dashboard(request):
    user_role = request.session.get("user_role")
    user_shg = request.session.get("user_shg")
    user_name = request.session.get("user_name")

    meeting = MeetingSchedule.objects.filter(
    shgname__iexact=(user_shg or "").strip()
    ).order_by("-id").first()

    if request.method == "POST":
      meeting_date = request.POST.get("meeting_date")

      if meeting_date:
        meeting_date = datetime.strptime(meeting_date, "%Y-%m-%d").date()

        if meeting:
            meeting.meeting_date = meeting_date
            meeting.save()
        else:
            meeting = MeetingSchedule.objects.create(
                shgname=user_shg,
                meeting_date=meeting_date
            )
    members = Register.objects.filter(
        shgname__iexact=(user_shg or "").strip()
    ).order_by("-id")

    total_members = members.count()

    
    now = datetime.now()
    current_month = int(request.GET.get("month") or now.month)
    current_year = int(request.GET.get("year") or now.year)

    
    records = MonthlyRecord.objects.filter(
        shgname__iexact=(user_shg or "").strip(),
        month=current_month,
        year=current_year
    )

    all_loans = Loan.objects.filter(
    shgname=user_shg,
    created_at__month=current_month,
    created_at__year=current_year   
    )

   
    personal_loans = Loan.objects.filter(
        shgname__iexact=(user_shg or "").strip(),
        loan_type="Personal",
        created_at__month=current_month,
        created_at__year=current_year
    )

    
    yearly_group_loans = Loan.objects.filter(
        shgname__iexact=(user_shg or "").strip(),
        loan_type="Group",
        created_at__month=current_month,
        created_at__year=current_year
    )

    total_loans_amount = yearly_group_loans.aggregate(
        Sum('amount')
    )['amount__sum'] or 0

    remaining_loans_amount = all_loans .aggregate(
        Sum('remaining')
    )['remaining__sum'] or 0

    total_loans_count = yearly_group_loans.count()

    paid_loans_count = all_loans.filter(
        remaining__gt=0
    ).count()

    active_loans = all_loans.filter(
        remaining__gt=0
    ).count()

    total_saving = records.aggregate(Sum('saving_paid'))['saving_paid__sum'] or 0
    total_group_emi = records.aggregate(Sum('group_emi'))['group_emi__sum'] or 0

    total_saving_all = MonthlyRecord.objects.filter(
        shgname__iexact=(user_shg or "").strip()
    ).aggregate(Sum('saving_paid'))['saving_paid__sum'] or 0

    
    total_personal_loan_year = personal_loans.aggregate(
        Sum('amount')
    )['amount__sum'] or 0

    member_data = []

    for m in members:
        member_meetings = MonthlyRecord.objects.filter(
            shgname__iexact=(user_shg or "").strip(),
            member=m,
            month=current_month,
            year=current_year
        )

        member_total_saving = member_meetings.aggregate(Sum('saving_paid'))['saving_paid__sum'] or 0
        member_total_emi = member_meetings.aggregate(Sum('group_emi'))['group_emi__sum'] or 0

        
        member_loans = Loan.objects.filter(
            shgname__iexact=(user_shg or "").strip(),
            member=m
        )

        loan_taken = member_loans.aggregate(Sum('amount'))['amount__sum'] or 0
        loan_remaining = member_loans.aggregate(Sum('remaining'))['remaining__sum'] or 0

        member_data.append({
            "fullname": m.fullname,
            "phone": m.phone,
            "aadhaar_number": m.aadhaar_number,
            "aadhaar_photo": m.aadhaar_photo.url if m.aadhaar_photo else None,
            "profile_photo": m.profile_photo.url if m.profile_photo else None,
            "total_saving": member_total_saving,
            "total_group_emi": member_total_emi,
            "loan_taken": loan_taken,
            "loan_remaining": loan_remaining,
            "pending_status": "Paid" if member_total_saving > 0 else "Pending",
            "loan_status": "Cleared" if loan_remaining == 0 else "Pending",
        })

    saving_paid_members = MonthlyRecord.objects.filter(
        shgname__iexact=(user_shg or "").strip(),
        month=current_month,
        year=current_year,
        saving_paid__gt=0
    ).values_list('member', flat=True).distinct()

    saving_paid_count = len(saving_paid_members)
    saving_pending_count = total_members - saving_paid_count

    saving_paid_percent = (saving_paid_count / total_members * 100) if total_members else 0
    saving_pending_percent = (saving_pending_count / total_members * 100) if total_members else 0

    group_emi_paid_members = MonthlyRecord.objects.filter(
        shgname__iexact=(user_shg or "").strip(),
        month=current_month,
        year=current_year,
        group_emi__gt=0
    ).values_list('member', flat=True).distinct()

    group_emi_paid_count = len(group_emi_paid_members)
    group_emi_pending_count = total_members - group_emi_paid_count

    group_emi_paid_percent = (group_emi_paid_count / total_members * 100) if total_members else 0
    group_emi_pending_percent = (group_emi_pending_count / total_members * 100) if total_members else 0

    total_collection = total_saving + total_group_emi
    saving_percent = (total_saving / total_collection * 100) if total_collection else 0
    emi_percent = (total_group_emi / total_collection * 100) if total_collection else 0

   

    context = {
        "user_role": user_role,
        "user_name": user_name,
        "user_shg": user_shg,
        "members": members,
        "member_data": member_data,
        "total_members": total_members,

        "total_saving": total_saving,
        "total_group_emi": total_group_emi,
        "total_saving_all": total_saving_all,

        "total_loans_amount": total_loans_amount,
        "remaining_loans_amount": remaining_loans_amount,
        "paid_loans_count": paid_loans_count,
        "active_loans": active_loans,

        "saving_paid_count": saving_paid_count,
        "saving_pending_count": saving_pending_count,
        "saving_paid_percent": saving_paid_percent,
        "saving_pending_percent": saving_pending_percent,

        "group_emi_paid_count": group_emi_paid_count,
        "group_emi_pending_count": group_emi_pending_count,
        "group_emi_paid_percent": group_emi_paid_percent,
        "group_emi_pending_percent": group_emi_pending_percent,

        "saving_percent": saving_percent,
        "emi_percent": emi_percent,
        "total_personal_loan_year": total_personal_loan_year,

        "meeting": meeting,
        "current_month": current_month,
        "current_year": current_year,
    }

    return render(request, "dashboard.html", context)


def add_member(request):

    if request.session.get("user_role") != "President":
        return redirect("dashboard")

    president_id = request.session.get("user_id")
    try:
        president = Register.objects.get(id=president_id)
    except Register.DoesNotExist:
        messages.error(request, "Session error. Please login again.")
        return redirect("login")

    if request.method == "GET":
        return render(request, "add_member.html")

    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        shgname = request.session.get("user_shg")
        aadhaar_number = request.POST.get("aadhaar_number", "").strip() or None

        # ✅ All validation checks first
        if not phone:
            messages.error(request, "Phone number is required.")
            return redirect("add_member")

        if not shgname:
            messages.error(request, "Session expired. Please login again.")
            return redirect("login")

        if Register.objects.filter(phone=phone, shgname=shgname).exists():
            messages.error(request, "This phone number already exists in your SHG.")
            return redirect("add_member")

        if aadhaar_number and Register.objects.filter(aadhaar_number=aadhaar_number).exists():
            messages.error(request, "This Aadhaar number already exists.")
            return redirect("add_member")

        if Register.objects.filter(shgname=shgname).count() >= 15:
            messages.error(request, "Maximum 15 members allowed.")
            return redirect("add_member")

        # ✅ Handle existing orphan User (from previous failed attempt)
        user = None
        try:
            existing_user = User.objects.get(username=phone)
            # If no Register linked to this user, reuse it
            if not Register.objects.filter(user=existing_user).exists():
                user = existing_user
            else:
                messages.error(request, "This phone number is already registered.")
                return redirect("add_member")
        except User.DoesNotExist:
            pass  # No existing user, will create fresh

        try:
            # Create user only if not reusing orphan
            if user is None:
                user = User.objects.create_user(
                    username=phone,
                    password=phone
                )

            register = Register(
                fullname=request.POST.get("fullname", "").strip(),
                phone=phone,
                aadhaar_number=aadhaar_number,
                dob=request.POST.get("dob") or None,
                role=request.POST.get("role", "Member"),
                shgname=shgname,
                user=user,
                district=president.district,
                village=president.village,
            )

            if "aadhaar_photo" in request.FILES:
                register.aadhaar_photo = request.FILES["aadhaar_photo"]

            if "profile_photo" in request.FILES:
                register.profile_photo = request.FILES["profile_photo"]

            register.save()

            messages.success(request, "Member added successfully!")
            return redirect("member_list")

        except Exception as e:
            # Only delete user if we just created it
            if user and not Register.objects.filter(user=user).exists():
                user.delete()
            print("ERROR adding member:", e)
            messages.error(request, f"Failed: {str(e)}")
            return redirect("add_member")
        
def delete_member(request, id):
   
    if request.session.get("user_role") != "President":
        return redirect("dashboard")

    try:
        member = Register.objects.get(id=id)

        if member.shgname != request.session.get("user_shg"):
            return redirect("dashboard")

        member.delete()

    except Register.DoesNotExist:
        pass

    return redirect("dashboard")


def member_list(request):
    user_shg = request.session.get("user_shg")
    user_role = request.session.get("user_role")

    if user_role != "President":
        return redirect("dashboard")

    search = request.GET.get("search", "").strip()
    member_id = request.GET.get("member_id")

    members = Register.objects.filter(shgname=user_shg)

    search_results = members

    if member_id:
        selected_member = members.filter(id=member_id).first()
    else:
        selected_member = members.filter(role="President").first()

    if not selected_member:
        selected_member = members.first()
    
    if request.method == "POST":
        member_id = request.POST.get("member_id")
        action = request.POST.get("action")

        member = Register.objects.get(id=member_id)

        if action == "edit":
            member.fullname = request.POST.get("fullname")
            member.phone = request.POST.get("phone")
            member.role = request.POST.get("role")
            dob = request.POST.get("dob")
            member.dob  = dob if dob else None

            if "profile_photo" in request.FILES:
                member.profile_photo = request.FILES["profile_photo"]

        elif action == "leave":
            member.status = "Left"
            member.left_date = date.today()

        member.save()
        return redirect(f"/members/?member_id={member.id}")

    return render(request, "member_list.html", {
        "members": members,
        "selected_member": selected_member,
        "search": search,
        "search_results": search_results
    })

def add_loan(request, loan_id=None):
    if request.session.get("user_role") != "President":
        return redirect("dashboard")

    shgname = request.session.get("user_shg")

    members = Register.objects.filter(
        shgname__iexact=(shgname or "").strip()
    )

    loan = None
    selected_member = None

    # EDIT MODE
    if loan_id:
        loan = get_object_or_404(Loan, id=loan_id)
        selected_member = loan.member

    if request.method == "POST":

        loan_type = request.POST.get("loan_type")

        amount = float(request.POST.get("amount") or 0)
        paid = float(request.POST.get("paid") or 0)
        duration = float(request.POST.get("duration") or 0)
        interest_rate = float(request.POST.get("interest_rate") or 0)
        subvention_rate = float(request.POST.get("subvention_rate") or 0)

        
        selected_member = None
        if loan_type == "Personal":
            member_id = request.POST.get("member_id")

            if not member_id:
                messages.error(request, "Select a member")
                return redirect("add_loan")

            selected_member = get_object_or_404(Register, id=member_id)

       
        if amount <= 0:
            messages.error(request, "Loan amount must be greater than 0")
            return redirect("add_loan")

       
        total_payable = amount + (
            amount * (interest_rate - subvention_rate) * duration
        ) / 100

        remaining = total_payable - paid

        
        if loan:
            loan.member = selected_member
            loan.amount = amount
            loan.paid = paid
            loan.remaining = remaining
            loan.loan_type = loan_type
            loan.duration = duration
            loan.interest_rate = interest_rate
            loan.subvention_rate = subvention_rate
            loan.total_payable = total_payable

            loan.save()
            messages.success(request, "Loan updated successfully")

        
        else:
            Loan.objects.create(
                shgname=shgname,
                member=selected_member,
                amount=amount,
                paid=paid,
                remaining=remaining,
                loan_type=loan_type,
                duration=duration,
                interest_rate=interest_rate,
                subvention_rate=subvention_rate,
                total_payable=total_payable
            )

            messages.success(request, f"{loan_type} loan added successfully")

        return redirect("loan_details")

    return render(request, "add_loan.html", {
        "members": members,
        "loan": loan,
        "selected_member": selected_member
    })

def logout_view(request):
    request.session.flush()   
    return redirect("login")

def monthly_collection(request):
    shg = (request.session.get("user_shg") or "").strip()
    role = request.session.get("user_role")

    members = Register.objects.filter(shgname__iexact=shg)

   
    month = request.GET.get("month")
    year = request.GET.get("year")

    today = date.today()

   
    if not month and not year:
        selected_month = today.month
        selected_year = today.year
    else:
        try:
            selected_month = int(month) if month else None
        except:
            selected_month = None

        try:
            selected_year = int(year) if year else None
        except:
            selected_year = None

    
    if request.method == "POST" and role == "President":
        member_id = request.POST.get("member_id")

        saving = float(request.POST.get("saving") or 0)
        group_emi = float(request.POST.get("group_emi") or 0)
        personal_emi = float(request.POST.get("personal_emi") or 0)

        if member_id:
            member = Register.objects.get(id=member_id)

            MonthlyRecord.objects.update_or_create(
                shgname=shg,
                member=member,
                month=selected_month,
                year=selected_year,
                defaults={
                    "saving_paid": saving,
                    "group_emi": group_emi,
                    "personal_emi": personal_emi,
                }
            )

        return redirect(f"/monthly_collection/?month={selected_month}&year={selected_year}")

   
    collections = MonthlyRecord.objects.filter(shgname=shg)

    
    if selected_month and selected_year:
        collections = collections.filter(month=selected_month, year=selected_year)

    elif selected_year:
        collections = collections.filter(year=selected_year)

    elif selected_month:
        collections = collections.filter(month=selected_month)

  
    total_savings_collection = collections.aggregate(Sum('saving_paid'))['saving_paid__sum'] or 0
    total_group_emi = collections.aggregate(Sum('group_emi'))['group_emi__sum'] or 0
    total_personal_emi = collections.aggregate(Sum('personal_emi'))['personal_emi__sum'] or 0

  
    saving_paid_members = collections.filter(
        saving_paid__gt=0
    ).values('member_id').distinct().count()

    group_emi_paid_members = collections.filter(
        group_emi__gt=0
    ).values('member_id').distinct().count()

    
    member_data = []

    for m in members:
        member_records = collections.filter(member_id=m.id)

        total_saving = member_records.aggregate(Sum('saving_paid'))['saving_paid__sum'] or 0
        total_group = member_records.aggregate(Sum('group_emi'))['group_emi__sum'] or 0
        total_personal = member_records.aggregate(Sum('personal_emi'))['personal_emi__sum'] or 0

        member_data.append({
            "fullname": m.fullname,
            "phone": m.phone,
            "total_saving": total_saving,
            "total_group_emi": total_group,
            "total_personal_emi": total_personal,
            "group_emi_status": "Paid" if total_group > 0 else "Pending",
            "personal_emi_status": "Paid" if total_personal > 0 else "Pending",
        })

    context = {
        "members": members,
        "role": role,
        "collections": collections,

        "total_savings_collection": total_savings_collection,
        "total_group_emi": total_group_emi,
        "total_personal_emi": total_personal_emi,

        "saving_paid_members": saving_paid_members,
        "group_emi_paid_members": group_emi_paid_members,

        "member_data": member_data,

        
        "selected_month": selected_month if selected_month else "",
        "selected_year": selected_year if selected_year else "",
    }

    return render(request, "monthly_collection.html", context)

def loan_details(request):
    shg = (request.session.get("user_shg") or "").strip()

    loan_type = request.GET.get("type")
    member = request.GET.get("member")
    month = request.GET.get("month")
    year = request.GET.get("year")

    now = datetime.now()

    
    if not month and not year:
        month = now.month
        year = now.year
    else:
        try:
            month = int(month) if month else None
        except:
            month = None

        try:
            year = int(year) if year else None
        except:
            year = None

    loans = Loan.objects.filter(
        shgname__iexact=shg
    )


    if loan_type == "Group":
        loans = loans.filter(loan_type__iexact="Group")

    elif loan_type == "Personal":
        loans = loans.filter(loan_type__iexact="Personal")

        if member and member.strip():
            try:
                loans = loans.filter(member_id=int(member))
            except:
                pass

    
    if month and year:
        loans = loans.filter(created_at__month=month, created_at__year=year)

    elif year:
        loans = loans.filter(created_at__year=year)

    elif month:
        loans = loans.filter(created_at__month=month)

    
    month_choices = [
        (1, "January"), (2, "February"), (3, "March"),
        (4, "April"), (5, "May"), (6, "June"),
        (7, "July"), (8, "August"), (9, "September"),
        (10, "October"), (11, "November"), (12, "December"),
    ]

    return render(request, "loan_details.html", {
        "loans": loans,
        "members": Register.objects.filter(
            shgname__iexact=shg
        ),

        "selected_month": month if month else "",
        "selected_year": year if year else "",
        "selected_type": loan_type,
        "selected_member": member,
        "month_choices": month_choices,

        "user_role": request.session.get("user_role"),
    })

def clear_loan(request, loan_id):
    if request.session.get("user_role") != "President":
        return redirect("loan_details")  

    loan = Loan.objects.get(id=loan_id)

    loan.remaining_amount = 0
    loan.paid_amount = loan.loan_amount
    loan.save()

    return redirect("loan_details")

def delete_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    if request.method == "POST":
        loan.delete()
    return redirect("loan_details")

def edit_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)

    if request.method == "POST":
        loan.loan_type = request.POST.get("loan_type")
        loan.amount = request.POST.get("amount")
        loan.paid = request.POST.get("paid")
        loan.remaining = request.POST.get("remaining")
        loan.duration = request.POST.get("duration")
        loan.interest_rate = request.POST.get("interest_rate")
        loan.subvention_rate = request.POST.get("subvention_rate")
        loan.total_payable = request.POST.get("total_payable")
        loan.save()

        return redirect("loan_details")

    return render(request, "add_loan.html", {"loan": loan, "edit": True})

def add_project(request, project_id=None):
    if request.session.get("user_role") != "President":
        return redirect("project_list")

    shgname = request.session.get("user_shg")

    project = None
    if project_id:
        project = get_object_or_404(Project, id=project_id, shgname=shgname)

    if request.method == "POST":
        title = request.POST.get("title")
        investment = request.POST.get("investment")
        profit = request.POST.get("profit")
        photo = request.FILES.get("photo")

        if request.POST.get("project_id"):   # UPDATE
            project = get_object_or_404(Project, id=request.POST.get("project_id"), shgname=shgname)

            project.title = title
            project.investment = investment
            project.profit = profit

            if photo:
                project.photo = photo

            project.save()

        else: 
            Project.objects.create(
                title=title,
                investment=investment,
                profit=profit,
                photo=photo,
                shgname=shgname
            )

        return redirect("project_list")

    return render(request, "add_project.html", {
        "project": project
    })



def delete_project(request, id):
    if request.session.get("user_role") != "President":
        return redirect("project_list")

    project = get_object_or_404(Project, id=id)
    project.delete()

    return redirect("project_list")
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

