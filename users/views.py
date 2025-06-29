from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from rest_framework_simplejwt.tokens import RefreshToken
import logging
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests

from .serializers import RegisterSerializer, LoginSerializer, UserProfileSerializer, GoogleAuthSerializer, GoogleSignupSerializer
from .models import CustomUser

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        users = CustomUser.objects.all()
        serializer = RegisterSerializer(users, many=True)
        return Response(serializer.data)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = authenticate(request, username=email, password=password)

            if user is not None:
                refresh = RefreshToken.for_user(user)
                update_last_login(None, user)

                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user_id': user.id,
                    'email': user.email,
                    'message': 'Login successful'
                }, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Logout failed'}, status=status.HTTP_400_BAD_REQUEST)

class UserView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)
    
    def put(self, request):
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PasswordView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        if not user.check_password(old_password):
            return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        
        if new_password != confirm_password:
            return Response({'error': 'Passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'Password updated successfully.',
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }, status=status.HTTP_200_OK)
    

class GoogleAuthView(APIView):
    """
    Handle Google authentication for existing users
    """
    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        if serializer.is_valid():
            id_token_str = serializer.validated_data['idToken']
            email = serializer.validated_data['email']
            
            try:
                # Verify the Google ID token
                idinfo = id_token.verify_oauth2_token(
                    id_token_str, 
                    requests.Request(), 
                    settings.GOOGLE_CLIENT_ID
                )
                
                # Verify the token is for our app
                if idinfo['aud'] != settings.GOOGLE_CLIENT_ID:
                    return Response({
                        'error': 'Invalid token audience'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if the email from token matches the provided email
                if idinfo['email'] != email:
                    return Response({
                        'error': 'Token email does not match provided email'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Verify email is verified by Google
                if not idinfo.get('email_verified', False):
                    return Response({
                        'error': 'Google email not verified'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if user exists
                try:
                    user = CustomUser.objects.get(email=email)
                    
                    # Generate tokens
                    refresh = RefreshToken.for_user(user)
                    update_last_login(None, user)
                    
                    return Response({
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'user_id': str(user.id),
                        'email': user.email,
                        'message': 'Google authentication successful'
                    }, status=status.HTTP_200_OK)
                    
                except CustomUser.DoesNotExist:
                    return Response({
                        'error': 'User not found. Please sign up first.',
                        'requires_signup': True
                    }, status=status.HTTP_404_NOT_FOUND)
                    
            except ValueError as e:
                logger.error(f"Google token verification failed: {str(e)}")
                return Response({
                    'error': 'Invalid Google token'
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Google authentication error: {str(e)}")
                return Response({
                    'error': 'Google authentication failed'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleSignupView(APIView):
    """
    Handle Google signup for new users
    """
    def post(self, request):
        serializer = GoogleSignupSerializer(data=request.data)
        if serializer.is_valid():
            id_token_str = serializer.validated_data['idToken']
            email = serializer.validated_data['email']
            
            try:
                # Verify the Google ID token
                idinfo = id_token.verify_oauth2_token(
                    id_token_str, 
                    requests.Request(), 
                    settings.GOOGLE_CLIENT_ID
                )
                
                # Verify the token is for our app
                if idinfo['aud'] != settings.GOOGLE_CLIENT_ID:
                    return Response({
                        'error': 'Invalid token audience'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if the email from token matches the provided email
                if idinfo['email'] != email:
                    return Response({
                        'error': 'Token email does not match provided email'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Verify email is verified by Google
                if not idinfo.get('email_verified', False):
                    return Response({
                        'error': 'Google email not verified'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if user already exists
                if CustomUser.objects.filter(email=email).exists():
                    return Response({
                        'error': 'User with this email already exists. Please sign in instead.',
                        'user_exists': True
                    }, status=status.HTTP_409_CONFLICT)
                
                # Create the user
                user = serializer.save()
                
                # Generate tokens
                refresh = RefreshToken.for_user(user)
                
                logger.info(f"New Google user created: {user.email}")
                
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user_id': str(user.id),
                    'email': user.email,
                    'message': 'Google signup successful'
                }, status=status.HTTP_201_CREATED)
                
            except ValueError as e:
                logger.error(f"Google token verification failed: {str(e)}")
                return Response({
                    'error': 'Invalid Google token'
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Google signup error: {str(e)}")
                return Response({
                    'error': 'Google signup failed'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)