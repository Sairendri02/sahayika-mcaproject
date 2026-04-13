from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),   
    path('ajax_load-villages/', views.load_villages, name='ajax_load_villages'),
    path("login/", views.login_view, name="login"),
    path("forgot_password/",views.forgot_password,name="forgot_password"),
    path("logout/",views.logout_view,name="logout"),
    path("dashboard/",views.dashboard,name="dashboard"),
    path('members/', views.member_list, name='member_list'),
    path("add_member/",views.add_member,name="add_member"),
    path("add_loan/",views.add_loan,name="add_loan"),
    path('edit-loan/<int:loan_id>/', views.add_loan, name='edit_loan'),
    path("meeting_entry/",views.meeting_entry,name="meeting_entry"),
    path("add_collection/",views.add_collection,name="add_collection"),
    path("monthly_collection/",views.monthly_collection,name="monthly_collection"),
    path('delete_member/<int:id>/', views.delete_member, name='delete_member'),
    path('projects/', views.project_list, name='project_list'),
    path('add-project/', views.add_project, name='add_project'),
    path("project/edit/<int:project_id>/", views.add_project, name="edit_project"),
    path("project/delete/<int:id>/", views.delete_project, name="delete_project"),
    path('loan-details/', views.loan_details, name='loan_details'),
    path('learn_more/', views.learn_more, name='learn_more'),
    path('about/', views.about, name='about'),
    path('rti/', views.rti, name='rti'),
    path('contact/', views.contact_view, name='contact'),
    path('clear-loan/<int:loan_id>/', views.clear_loan, name='clear_loan'),
   
   
]