from django.contrib import admin
from .models import CustomUser, ProfilePicture, MutedInstructor

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'user_type', 'is_active', 'date_joined', 'has_fcm_token']
    list_filter = ['user_type', 'is_active', 'gender']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['date_joined', 'last_login']
    
    def has_fcm_token(self, obj):
        return bool(obj.fcm_token)
    has_fcm_token.boolean = True
    has_fcm_token.short_description = 'Has FCM Token'
    
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
        ('Notifications', {
            'fields': ('fcm_token',)
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


@admin.register(MutedInstructor)
class MutedInstructorAdmin(admin.ModelAdmin):
    list_display = ['user', 'instructor', 'muted_at']
    list_filter = ['muted_at']
    search_fields = ['user__email', 'instructor__email', 'user__first_name', 'instructor__first_name']
    readonly_fields = ['muted_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'instructor')

