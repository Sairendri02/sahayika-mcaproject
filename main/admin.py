from django.contrib import admin
from .models import District, Village, Register
from .models import ContactMessage

admin.site.register(District)
admin.site.register(Village)
admin.site.register(Register)

@admin.register(ContactMessage)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'subject', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'phone', 'subject')



