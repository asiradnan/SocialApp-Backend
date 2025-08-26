from django.contrib import admin
from .models import CustomUser, ProfilePicture

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'user_type', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active', 'gender']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['date_joined', 'last_login']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'gender', 'profile_picture')
        }),
        ('Account info', {
            'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )

@admin.register(ProfilePicture)
class ProfilePictureAdmin(admin.ModelAdmin):
    list_display = ['user', 'uploaded_at', 'is_current', 'file_size']
    list_filter = ['is_current', 'uploaded_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['uploaded_at', 'file_size']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
