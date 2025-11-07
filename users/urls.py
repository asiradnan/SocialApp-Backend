from django.urls import path
from .views import (
    RegisterView, LogoutView, LoginView, UserView, PasswordView, 
    GoogleAuthView, GoogleSignupView, ProfilePictureView, ProfilePictureDetailView,
    FCMTokenView, MutedInstructorsView, UnmuteInstructorView, CheckMutedStatusView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', UserView.as_view(), name='me'),
    path('password/', PasswordView.as_view(), name='password'),
    path('google-auth/', GoogleAuthView.as_view(), name='google-auth'),
    path('google-signup/', GoogleSignupView.as_view(), name='google-signup'),
    path('profile-picture/', ProfilePictureView.as_view(), name='profile-picture'),
    path('profile-picture/<int:pk>/', ProfilePictureDetailView.as_view(), name='profile-picture-detail'),
    
    # FCM and notification preferences
    path('fcm-token/', FCMTokenView.as_view(), name='fcm-token'),
    path('muted-instructors/', MutedInstructorsView.as_view(), name='muted-instructors'),
    path('muted-instructors/<int:instructor_id>/', UnmuteInstructorView.as_view(), name='unmute-instructor'),
    path('muted-instructors/<int:instructor_id>/status/', CheckMutedStatusView.as_view(), name='check-muted-status'),
]
