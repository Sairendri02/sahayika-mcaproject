from django.contrib import admin
from .models import District, Village, Register
from .models import ContactMessage

admin.site.register(District)
admin.site.register(Village)
admin.site.register(Register)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'subject', 'type', 'status', 'reply', 'created_at')
    list_filter = ('type', 'status')
    search_fields = ('name', 'phone', 'email', 'subject', 'message')
    readonly_fields = ('name', 'phone', 'email', 'subject', 'message', 'created_at')



