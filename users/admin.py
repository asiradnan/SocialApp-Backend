from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import CustomUser, ProfilePicture

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'user_type', 'is_active', 'date_joined', 'content_counts']
    list_filter = ['user_type', 'is_active', 'gender']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['date_joined', 'last_login', 'get_content_summary']
    
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
        ('Content Summary', {
            'fields': ('get_content_summary',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            posts_count=Count('posts'),
            comments_count=Count('comments'),
            reactions_count=Count('post_reactions'),
            poll_votes_count=Count('poll_votes')
        )
    
    def content_counts(self, obj):
        """Display content counts in list view"""
        return format_html(
            "Posts: {} | Comments: {} | Reactions: {} | Votes: {}",
            obj.posts_count,
            obj.comments_count,
            obj.reactions_count,
            obj.poll_votes_count
        )
    content_counts.short_description = 'Content Counts'
    
    def get_content_summary(self, obj):
        """Show detailed content summary"""
        if obj.pk:
            posts_count = obj.posts.count()
            comments_count = obj.comments.count()
            reactions_count = obj.post_reactions.count()
            poll_votes_count = obj.poll_votes.count()
            profile_pics_count = obj.profile_pictures.count()
            
            return format_html(
                """
                <div style='line-height: 1.6;'>
                    <strong>Content Overview:</strong><br>
                    • Posts: {}<br>
                    • Comments: {}<br>
                    • Reactions: {}<br>
                    • Poll Votes: {}<br>
                    • Profile Pictures: {}<br>
                    <br>
                    <em style='color: #666;'>
                        Note: Deleting this user will permanently remove all associated content.
                    </em>
                </div>
                """,
                posts_count,
                comments_count,
                reactions_count,
                poll_votes_count,
                profile_pics_count
            )
        return "Save the user first to see content summary."
    get_content_summary.short_description = 'User Content Summary'
    
    def delete_model(self, request, obj):
        """Custom delete method with proper cleanup"""
        try:
            obj.delete()
        except Exception as e:
            self.message_user(
                request,
                f"Error deleting user {obj.email}: {str(e)}",
                level='ERROR'
            )
            raise
    
    def delete_queryset(self, request, queryset):
        """Handle bulk deletion"""
        for obj in queryset:
            try:
                obj.delete()
            except Exception as e:
                self.message_user(
                    request,
                    f"Error deleting user {obj.email}: {str(e)}",
                    level='ERROR'
                )

@admin.register(ProfilePicture)
class ProfilePictureAdmin(admin.ModelAdmin):
    list_display = ['user', 'uploaded_at', 'is_current', 'file_size']
    list_filter = ['is_current', 'uploaded_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['uploaded_at', 'file_size']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
