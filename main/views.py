from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
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
from datetime import datetime, date ,timedelta
from django.utils import timezone
import random
import os
import re

from twilio.rest import Client


def home(request):  
    return render(request, 'index.html')
    


def send_otp_sms(phone, otp):

#Get Twilio credentials from environment
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone = os.getenv("TWILIO_PHONE")

    client = Client(account_sid, auth_token)
    try:
        # send otp sms
        client.messages.create(
            body=f"Your OTP is {otp}",
            from_=twilio_phone,
            to="+91"+phone
        )
        print("OTP SENT SUCCESS")
    except Exception as e:
        print("TWILIO ERROR:", e)

def register(request):
    districts = District.objects.all().order_by('name')
    villages = []  #  Add this for village dropdown
    
    # initialize msg
    error = ""
    success = ""

    fullname = ""
    shgname = ""
    phone = ""
    district_id = ""
    village_id = ""

    if request.method == "POST":

        #  Always fetch ALL fields at top of POST
        fullname = request.POST.get("fullname", "").strip()
        shgname = request.POST.get("shgname", "").strip()
        phone = request.POST.get("phone", "").strip()
        district_id = request.POST.get("district", "").strip()
        village_id = request.POST.get("village", "").strip()

        #  Load villages for selected district so dropdown stays filled
        if district_id:
            villages = Village.objects.filter(district_id=district_id)

        # send otp
        if "send_otp" in request.POST:
            if not re.fullmatch(r'\d{10}', phone):
                error = _("Enter valid phone number")
            else:
                otp = str(random.randint(1000, 9999))
                request.session["otp"] = otp
                request.session["otp_expiry"] = (
                    timezone.now() + timedelta(minutes=5)
                ).isoformat()
                send_otp_sms(phone, otp)
                success = _("OTP sent to your phone number")

        # register user
        elif "register" in request.POST:
            dob = request.POST.get('dob', '').strip()
            password = request.POST.get('password', '').strip()
            otp_input = request.POST.get("otp", '').strip()
            aadhaar_number = request.POST.get('aadhaar_number', '').strip()
            aadhaar_photo = request.FILES.get('aadhaar_photo')
            profile_photo = request.FILES.get('profile_photo')

            # Role always President
            role = "President"

            # Check OTP expiry
            otp_expiry = request.session.get("otp_expiry")
            otp_expired = False
            if otp_expiry:
                from django.utils.dateparse import parse_datetime
                expiry_time = parse_datetime(otp_expiry)
                if timezone.now() > expiry_time:
                    otp_expired = True

            if not all([fullname, shgname, district_id, village_id, phone, password, otp_input]):
                error = _("All fields including OTP are required")

            elif otp_expired:
                error = _("OTP expired. Please request a new one.")

            elif otp_input != request.session.get("otp"):
                error = _("Invalid OTP")

            elif not re.fullmatch(r'\d{10}', phone):
                error = _("Invalid phone number")

            elif User.objects.filter(username=phone).exists():
                error = _("This phone number is already registered")

            else:
                district = District.objects.get(id=district_id)
                village = Village.objects.get(id=village_id)

                if Register.objects.filter(shgname=shgname, village=village).exists():
                    error = _("An SHG with this name already exists in this village")

                elif Register.objects.filter(shgname=shgname, role="President").exists():
                    error = _("A President already exists for this SHG")

                elif not all([aadhaar_number, aadhaar_photo, profile_photo]):
                    error = _("All Aadhaar fields are required")

                elif not re.fullmatch(r'\d{12}', aadhaar_number):
                    error = _("Invalid Aadhaar number")

                else:
                    # Create Django user
                    user = User.objects.create_user(
                        username=phone,
                        password=password
                    )
                    # Save register model
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

                    success = _("Registered successfully! Please login.")
                    request.session.pop("otp", None)
                    request.session.pop("otp_expiry", None)

                    #  Clear fields after success
                    fullname = ""
                    shgname = ""
                    phone = ""
                    district_id = ""
                    village_id = ""
                    villages = []

    return render(request, "register.html", {
        "districts": districts,
        "villages": villages,  #  Pass villages to template
        "error": error,
        "success": success,
        "fullname": fullname,
        "shgname": shgname,
        "phone": phone,
        "district_id": district_id,
        "village_id": village_id,
    })
def load_villages(request):
    district_id = request.GET.get('district')
    villages = Village.objects.filter(district_id=district_id).values('id', 'name')
    return JsonResponse(list(villages), safe=False)


def login_view(request):
    error = ""
    success = ""
    phone = ""
    shgname = ""
    role = ""

    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        shgname = request.POST.get("shgname", "").strip()
        role = request.POST.get("role", "").strip()

        # send OTP to members
        if "send_otp" in request.POST:
            if not phone or not shgname:
                error = _("Phone and SHG name are required.")
            elif not Register.objects.filter(
                phone=phone,
                shgname=shgname,
                role="Member"
            ).exists():
                error = _("No member found with this phone and SHG name.")
            else:
                otp = str(random.randint(1000, 9999))
                request.session["login_otp"] = otp
                request.session["login_phone"] = phone
                request.session["login_otp_expiry"] = (
                    timezone.now() + timedelta(minutes=5)
                ).isoformat()
                send_otp_sms(phone, otp)  # Real SMS
                success = _("OTP sent to your phone number!")

        # login logic
        elif "login" in request.POST:

            if not role:
                error = _("Please select a role.")

            # president login(password)
            elif role == "President":
                password = request.POST.get("password", "").strip()

                if not password:
                    error = _("Please enter your password.")
                else:
                    user = authenticate(request, username=phone, password=password)

                    if user is None:
                        error = _("Invalid phone or password.")
                    else:
                        try:
                            reg = Register.objects.get(
                                user=user,
                                shgname=shgname,
                                role__iexact="President"
                            )
                        except Register.DoesNotExist:
                            error = _("No President account found for this SHG.")
                        else:
                            login(request, user)
                            request.session["user_id"] = reg.id
                            request.session["user_name"] = reg.fullname
                            request.session["user_shg"] = reg.shgname
                            request.session["user_role"] = reg.role
                            request.session["user_phone"] = reg.phone
                            return redirect("dashboard")

            # member login (otp)
            elif role == "Member":
                otp_input = request.POST.get("otp", "").strip()
                session_otp = request.session.get("login_otp")
                session_phone = request.session.get("login_phone")
                otp_expiry = request.session.get("login_otp_expiry")

              
                otp_expired = False
                if otp_expiry:
                    from django.utils.dateparse import parse_datetime
                    expiry_time = parse_datetime(otp_expiry)
                    if timezone.now() > expiry_time:
                        otp_expired = True

                if not otp_input:
                    error = _("Please enter the OTP.")

                elif session_otp is None:
                    error = _("Please request an OTP first.")

                elif otp_expired:
                    error = _("OTP expired. Please request a new one.")
                   
                    request.session.pop("login_otp", None)
                    request.session.pop("login_otp_expiry", None)

                elif phone != session_phone:
                    error = _("Phone number does not match OTP request.")

                elif otp_input != session_otp:
                    error = _("Invalid OTP. Please try again.")

                else:
                    try:
                        reg = Register.objects.get(
                            phone=phone,
                            shgname=shgname,
                            role__iexact="Member"
                        )
                    except Register.DoesNotExist:
                        error = _("No member found with this phone and SHG name.")
                    else:
                       
                        request.session.pop("login_otp", None)
                        request.session.pop("login_phone", None)
                        request.session.pop("login_otp_expiry", None)
                    if reg.user is None:
                        error = _("Account error.Please contact to your President")
                    else:
                        login(request, reg.user)
                        request.session["user_id"] = reg.id
                        request.session["user_name"] = reg.fullname
                        request.session["user_shg"] = reg.shgname
                        request.session["user_role"] = reg.role
                        request.session["user_phone"] = reg.phone
                        return redirect("dashboard")

            else:
                error = _("Invalid role selected.")

    return render(request, "login.html", {
        "error": error,
        "success": success,
        "phone": phone,
        "shgname": shgname,
        "role": role,
    })

def forgot_password(request):
    error = ""
    success = ""
    phone = ""
    shgname = ""
    otp_sent = False

    if request.method == "POST":

        
        if "send_otp" in request.POST:
            phone = request.POST.get("phone", "").strip()
            shgname = request.POST.get("shgname", "").strip()

            if not phone or not shgname:
                error = _("Phone and SHG name are required.")
            else:
                try:
                    reg = Register.objects.get(
                        phone=phone,
                        shgname=shgname,
                        role="President"
                    )
                    otp = str(random.randint(1000, 9999))
                    request.session["fp_otp"] = otp
                    request.session["fp_phone"] = phone
                    request.session["fp_shgname"] = shgname
                    request.session["fp_otp_expiry"] = (
                        timezone.now() + timedelta(minutes=5)
                    ).isoformat()
                    send_otp_sms(phone, otp)  
                    otp_sent = True
                    success = _("OTP sent to your phone number!")

                except Register.DoesNotExist:
                    error = _("No President account found with this phone and SHG name.")

      
        elif "reset_password" in request.POST:
            phone = request.POST.get("phone", "").strip()
            shgname = request.POST.get("shgname", "").strip()
            otp_input = request.POST.get("otp", "").strip()
            new_password = request.POST.get("password", "").strip()
            confirm_password = request.POST.get("confirm_password", "").strip()

            session_otp = request.session.get("fp_otp")
            session_phone = request.session.get("fp_phone")
            session_shgname = request.session.get("fp_shgname")
            otp_expiry = request.session.get("fp_otp_expiry")

            
            otp_expired = False
            if otp_expiry:
                from django.utils.dateparse import parse_datetime
                expiry_time = parse_datetime(otp_expiry)
                if timezone.now() > expiry_time:
                    otp_expired = True

            if not otp_input:
                error = _("Please enter the OTP.")
                otp_sent = True

            elif otp_expired:
                error = _("OTP expired. Please request a new one.")

            elif otp_input != session_otp:
                error = _("Invalid OTP. Please try again.")
                otp_sent = True

            elif phone != session_phone or shgname != session_shgname:
                error = _("Session mismatch. Please start over.")

            elif not new_password:
                error = _("Password cannot be empty.")
                otp_sent = True

            elif new_password != confirm_password:
                error = _("Passwords do not match.")
                otp_sent = True

            else:
                try:
                    reg = Register.objects.get(
                        phone=phone,
                        shgname=shgname,
                        role="President"
                    )
                    reg.user.set_password(new_password)
                    reg.user.save()

                
                    request.session.pop("fp_otp", None)
                    request.session.pop("fp_phone", None)
                    request.session.pop("fp_shgname", None)
                    request.session.pop("fp_otp_expiry", None)

                    success = _("Password reset successfully! Please login.")
                    return render(request, "forgot_password.html", {
                        "success": success,
                        "otp_sent": False,
                        "phone": "",
                        "shgname": "",
                    })

                except Register.DoesNotExist:
                    error = _("Account not found.")
                    otp_sent = True

    return render(request, "forgot_password.html", {
        "error": error,
        "success": success,
        "phone": phone,
        "shgname": shgname,
        "otp_sent": otp_sent,
    })
# DASHBOARD
@login_required(login_url='login')
@never_cache
def dashboard(request):
    # Get user session details
    user_role = request.session.get("user_role")
    user_shg = request.session.get("user_shg")
    user_name = request.session.get("user_name")

    # get latest metting
    meeting = MeetingSchedule.objects.filter(
    shgname__iexact=(user_shg or "").strip()
    ).order_by("-id").first()

    # save/update metting date
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
    # Get members of SHG
    members = Register.objects.filter(
        shgname__iexact=(user_shg or "").strip()
    ).order_by("-id")

    total_members = members.count()

    # Current month/year filteration
    now = datetime.now()
    current_month = int(request.GET.get("month") or now.month)
    current_year = int(request.GET.get("year") or now.year)

    # monthly record
    records = MonthlyRecord.objects.filter(
        shgname__iexact=(user_shg or "").strip(),
        month=current_month,
        year=current_year
    )
    
    # loan queries
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

    # Loan Calculation
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

    # Saving & EMI Totals
    total_saving = records.aggregate(Sum('saving_paid'))['saving_paid__sum'] or 0
    total_group_emi = records.aggregate(Sum('group_emi'))['group_emi__sum'] or 0

    total_saving_all = MonthlyRecord.objects.filter(
        shgname__iexact=(user_shg or "").strip()
    ).aggregate(Sum('saving_paid'))['saving_paid__sum'] or 0

    
    total_personal_loan_year = personal_loans.aggregate(
        Sum('amount')
    )['amount__sum'] or 0

    # Per member calculation
    member_data = []

    for m in members:
        # monthly data per member
        member_meetings = MonthlyRecord.objects.filter(
            shgname__iexact=(user_shg or "").strip(),
            member=m,
            month=current_month,
            year=current_year
        )

        member_total_saving = member_meetings.aggregate(Sum('saving_paid'))['saving_paid__sum'] or 0
        member_total_emi = member_meetings.aggregate(Sum('group_emi'))['group_emi__sum'] or 0

        
        # Loan data per member
        member_loans = Loan.objects.filter(
            shgname__iexact=(user_shg or "").strip(),
            member=m
        )

        loan_taken = member_loans.aggregate(Sum('amount'))['amount__sum'] or 0
        loan_remaining = member_loans.aggregate(Sum('remaining'))['remaining__sum'] or 0

        # Append member summery
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

    # Saving stats
    saving_paid_members = MonthlyRecord.objects.filter(
        shgname__iexact=(user_shg or "").strip(),
        month=current_month,
        year=current_year,
        saving_paid__gt=0
    ).values_list('member', flat=True).distinct()

    saving_paid_count = len(saving_paid_members)
    saving_pending_count = total_members - saving_paid_count

    # percentage calculation
    saving_paid_percent = (saving_paid_count / total_members * 100) if total_members else 0
    saving_pending_percent = (saving_pending_count / total_members * 100) if total_members else 0

    # EMI stats
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

    # Collection ratio
    total_collection = total_saving + total_group_emi
    saving_percent = (total_saving / total_collection * 100) if total_collection else 0
    emi_percent = (total_group_emi / total_collection * 100) if total_collection else 0

   
    # Final Context
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

@login_required(login_url='login')
def add_member(request):

    # Only President allow
    if request.session.get("user_role") != "President":
        return redirect("dashboard")

    president_id = request.session.get("user_id")

    # get president record
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

        # Basic validations
        if not phone:
            messages.error(request, "Phone number is required.")
            return redirect("add_member")

        if not shgname:
            messages.error(request, "Session expired. Please login again.")
            return redirect("login")

        if Register.objects.filter(phone=phone, shgname=shgname).exists():
            messages.error(request, "This phone number already exists in your SHG.")
            return redirect("add_member")

        if User.objects.filter(username=phone).exists():
            # Check if orphan user (no Register linked)
            existing_user = User.objects.get(username=phone)
            if Register.objects.filter(user=existing_user).exists():
                messages.error(request, "This phone number is already registered.")
                return redirect("add_member")

        if aadhaar_number and Register.objects.filter(aadhaar_number=aadhaar_number).exists():
            messages.error(request, "This Aadhaar number already exists.")
            return redirect("add_member")

        if Register.objects.filter(shgname=shgname).count() >= 15:
            messages.error(request, "Maximum 15 members allowed.")
            return redirect("add_member")

        try:
            #  Reuse orphan user or create new one
            user = None
            try:
                existing_user = User.objects.get(username=phone)
                if not Register.objects.filter(user=existing_user).exists():
                    user = existing_user
            except User.DoesNotExist:
                pass

            if user is None:
                #  Create user with unusable password
                # Members login with OTP so they don't need a password
                user = User.objects.create_user(username=phone)
                user.set_unusable_password()
                user.save()

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
            return redirect("add_member")

        except Exception as e:
            if user and not Register.objects.filter(user=user).exists():
                user.delete()
            print("ERROR adding member:", e)
            messages.error(request, f"Failed: {str(e)}")
            return redirect("add_member")
        
@login_required(login_url='login')
def delete_member(request, id):

    if request.session.get("user_role") != "President":
        return redirect("dashboard")

    try:
        member = Register.objects.get(id=id)

        if member.shgname != request.session.get("user_shg"):
            return redirect("dashboard")

        #  Prevent deleting President
        if member.role == "President":
            messages.error(request, "Cannot delete the President.")
            return redirect("member_list")

        #  Delete linked user too
        if member.user:
            member.user.delete()
        else:
            member.delete()

        messages.success(request, "Member deleted successfully!")

    except Register.DoesNotExist:
        messages.error(request, "Member not found.")

    return redirect("member_list")  #  Goes back to member list



@login_required(login_url='login')
def member_list(request):

    # get session data
    user_shg = request.session.get("user_shg")
    user_role = request.session.get("user_role")

    # Only president allowed
    if user_role != "President":
        return redirect("dashboard")

    search = request.GET.get("search", "").strip()
    member_id = request.GET.get("member_id")

    # get all members
    members = Register.objects.filter(shgname=user_shg)
    search_results = members

    # select member for view/edit
    if member_id:
        selected_member = members.filter(id=member_id).first()
    else:
        selected_member = members.filter(role="President").first()

    if not selected_member:
        selected_member = members.first()

    if request.method == "POST":
        member_id = request.POST.get("member_id")
        action = request.POST.get("action")

        try:
            member = Register.objects.get(id=member_id)
        except Register.DoesNotExist:
            messages.error(request, "Member not found.")
            return redirect("member_list")

        if action == "edit":
            old_phone = member.phone
            new_phone = request.POST.get("phone", "").strip()

            #  Check duplicate phone
            if Register.objects.filter(phone=new_phone).exclude(id=member.id).exists():
                messages.error(request, "This phone number already exists.")
                return redirect(f"/members/?member_id={member.id}")

            # update member details
            member.fullname = request.POST.get("fullname")
            member.phone = new_phone
            member.role = request.POST.get("role")
            dob = request.POST.get("dob")
            member.dob = dob if dob else None

            if "profile_photo" in request.FILES:
                member.profile_photo = request.FILES["profile_photo"]

            #  Update Django User username if phone changed
            if old_phone != new_phone:
                if member.user:
                    member.user.username = new_phone
                    member.user.save()

            messages.success(request, "Member updated successfully!")

        elif action == "leave":
            # mark member as left
            member.status = "Left"
            member.left_date = date.today()
            messages.success(request, f"{member.fullname} marked as left.")

        member.save()
        return redirect(f"/members/?member_id={member.id}")

    return render(request, "member_list.html", {
        "members": members,
        "selected_member": selected_member,
        "search": search,
        "search_results": search_results
    })

@login_required(login_url='login')
def add_loan(request, loan_id=None):
    if request.session.get("user_role") != "President":
        return redirect("dashboard")

    shgname = request.session.get("user_shg")

    # Get member
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

        # convert inputs
        amount = float(request.POST.get("amount") or 0)
        paid = float(request.POST.get("paid") or 0)
        duration = float(request.POST.get("duration") or 0)
        interest_rate = float(request.POST.get("interest_rate") or 0)
        subvention_rate = float(request.POST.get("subvention_rate") or 0)

        
        # member require only for personal loan
        selected_member = None
        if loan_type == "Personal":
            member_id = request.POST.get("member_id")

            if not member_id:
                messages.error(request, "Select a member")
                return redirect("add_loan")

            selected_member = get_object_or_404(Register, id=member_id)

       
       # Validation amount
        if amount <= 0:
            messages.error(request, "Loan amount must be greater than 0")
            return redirect("add_loan")

       # Calculation Total payable 
        total_payable = amount + (
            amount * (interest_rate - subvention_rate) * duration
        ) / 100

        remaining = total_payable - paid

        # update existing loan
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

        # Create new loan
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

        return redirect("add_loan")

    return render(request, "add_loan.html", {
        "members": members,
        "loan": loan,
        "selected_member": selected_member
    })

@login_required(login_url='login')
def monthly_collection(request):
    # session data
    shg = (request.session.get("user_shg") or "").strip()
    role = request.session.get("user_role")

    members = Register.objects.filter(shgname__iexact=shg)

    # Get filters
    month = request.GET.get("month")
    year = request.GET.get("year")

    today = date.today()

    # Default current month/year
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

    # save/update collection(President only)
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

        return redirect(f"/monthly_collection/?month={selected_month or ''}&year={selected_year or ''}")

    # Filter records
    collections = MonthlyRecord.objects.filter(shgname=shg)

    
    if selected_month and selected_year:
        collections = collections.filter(month=selected_month, year=selected_year)

    elif selected_year:
        collections = collections.filter(year=selected_year)

    elif selected_month:
        collections = collections.filter(month=selected_month)

    # Aggregations
    total_savings_collection = collections.aggregate(Sum('saving_paid'))['saving_paid__sum'] or 0
    total_group_emi = collections.aggregate(Sum('group_emi'))['group_emi__sum'] or 0
    total_personal_emi = collections.aggregate(Sum('personal_emi'))['personal_emi__sum'] or 0

  
    saving_paid_members = collections.filter(
        saving_paid__gt=0
    ).values('member_id').distinct().count()

    group_emi_paid_members = collections.filter(
        group_emi__gt=0
    ).values('member_id').distinct().count()

    # member-wise data
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

@login_required(login_url='login')
def loan_details(request):

    # get SHG loans
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

    # monthly filter
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

@login_required(login_url='login')
def clear_loan(request, loan_id):
    # Only president allowed
    if request.session.get("user_role") != "President":
        return redirect("loan_details")  

    loan = Loan.objects.get(id=loan_id)
    # Clear loan
    loan.remaining = 0
    loan.paid = loan.loan
    loan.save()

    return redirect("loan_details")

@login_required(login_url='login')
def delete_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    if request.method == "POST":
        loan.delete()
    return redirect("loan_details")

@login_required(login_url='login')
def edit_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)

    if request.method == "POST":
        # Update loan fields
        loan.loan_type = request.POST.get("loan_type")
        loan.amount = float(request.POST.get("amount") or 0)
        loan.paid = float(request.POST.get("paid") or 0)
        loan.remaining = float(request.POST.get("remaining") or 0)
        loan.duration = float(request.POST.get("duration") or 0)
        loan.interest_rate =float(request.POST.get("interest_rate") or 0)
        loan.subvention_rate =float(request.POST.get("subvention_rate") or 0)
        loan.total_payable = float(request.POST.get("total_payable") or 0)
        loan.save()

        return redirect("loan_details")

    return render(request, "add_loan.html", {"loan": loan, "edit": True})

@login_required(login_url='login')
def add_project(request, project_id=None):

    # Only President allowed
    if request.session.get("user_role") != "President":
        return redirect("project_list")

    shgname = request.session.get("user_shg")

    project = None
    # Edit mode
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
        # Create new project
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


@login_required(login_url='login')
def delete_project(request, id):
    if request.session.get("user_role") != "President":
        return redirect("project_list")

    project = get_object_or_404(Project, id=id)
    project.delete()

    return redirect("project_list")

@login_required(login_url='login')
def project_list(request):
    # get project ogf current shg
    projects = Project.objects.filter(
        shgname=request.session.get("user_shg")
    )

    return render(request, "project_list.html", {
        "projects": projects,
        "user_role": request.session.get("user_role")
    })

def logout_view(request):
    # logout user and clear session
    auth_logout(request)
    request.session.flush()
    return redirect("home")

def learn_more(request):
    return render(request, 'learn_more.html')

def about(request):
    return render(request, 'about.html')

def rti(request):
    return render(request, 'rti.html')

