from django.urls import path
from .views import RegisterView, LogoutView, LoginView, UserView, PasswordView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', UserView.as_view(), name='me'),
    path('password', PasswordView.as_view(), name='password'),
]
