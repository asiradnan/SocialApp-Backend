from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from rest_framework_simplejwt.tokens import RefreshToken
import logging
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests

from .serializers import (
    RegisterSerializer, LoginSerializer, UserProfileSerializer, 
    GoogleAuthSerializer, GoogleSignupSerializer, ProfilePictureSerializer,
    ProfilePictureUploadSerializer, FCMTokenSerializer, MutedInstructorSerializer,
    MuteInstructorSerializer, SubmitRatingSerializer, RatingSerializer
)
from .models import CustomUser, ProfilePicture, MutedInstructor, Rating

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
        serializer = UserProfileSerializer(user, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request):
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True, context={'request': request})
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


class ProfilePictureView(APIView):
    """
    Handle profile picture operations
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        """Get user's profile pictures"""
        profile_pictures = ProfilePicture.objects.filter(user=request.user)
        serializer = ProfilePictureSerializer(profile_pictures, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Upload a new profile picture"""
        serializer = ProfilePictureUploadSerializer(data=request.data)
        if serializer.is_valid():
            image = serializer.validated_data['image']
            
            # Delete old profile picture if exists
            if request.user.profile_picture:
                request.user.delete_old_profile_picture()
            
            # Create new profile picture
            profile_picture = ProfilePicture.objects.create(
                user=request.user,
                image=image,
                is_current=True
            )
            
            # Update user's profile picture field
            request.user.profile_picture = image
            request.user.save(update_fields=['profile_picture'])
            
            serializer = ProfilePictureSerializer(profile_picture, context={'request': request})
            return Response({
                'message': 'Profile picture uploaded successfully',
                'profile_picture': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """Delete current profile picture"""
        try:
            if request.user.profile_picture:
                # Delete the file
                request.user.delete_old_profile_picture()
                
                # Update user model
                request.user.profile_picture = None
                request.user.save(update_fields=['profile_picture'])
                
                # Mark all profile pictures as not current
                ProfilePicture.objects.filter(user=request.user, is_current=True).update(is_current=False)
                
                return Response({
                    'message': 'Profile picture deleted successfully'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'No profile picture to delete'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Profile picture deletion error: {str(e)}")
            return Response({
                'error': 'Failed to delete profile picture'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfilePictureDetailView(APIView):
    """
    Handle specific profile picture operations
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """Get specific profile picture"""
        try:
            profile_picture = ProfilePicture.objects.get(pk=pk, user=request.user)
            serializer = ProfilePictureSerializer(profile_picture, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ProfilePicture.DoesNotExist:
            return Response({
                'error': 'Profile picture not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        """Set specific profile picture as current"""
        try:
            profile_picture = ProfilePicture.objects.get(pk=pk, user=request.user)
            
            # Set all other profile pictures as not current
            ProfilePicture.objects.filter(user=request.user, is_current=True).update(is_current=False)
            
            # Set this one as current
            profile_picture.is_current = True
            profile_picture.save()
            
            # Update user's profile picture field
            request.user.profile_picture = profile_picture.image
            request.user.save(update_fields=['profile_picture'])
            
            serializer = ProfilePictureSerializer(profile_picture, context={'request': request})
            return Response({
                'message': 'Profile picture set as current',
                'profile_picture': serializer.data
            }, status=status.HTTP_200_OK)
            
        except ProfilePicture.DoesNotExist:
            return Response({
                'error': 'Profile picture not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        """Delete specific profile picture"""
        try:
            profile_picture = ProfilePicture.objects.get(pk=pk, user=request.user)
            
            # If this is the current profile picture, update user model
            if profile_picture.is_current:
                request.user.profile_picture = None
                request.user.save(update_fields=['profile_picture'])
            
            # Delete the profile picture (this will also delete the file)
            profile_picture.delete()
            
            return Response({
                'message': 'Profile picture deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except ProfilePicture.DoesNotExist:
            return Response({
                'error': 'Profile picture not found'
            }, status=status.HTTP_404_NOT_FOUND)


class FCMTokenView(APIView):
    """
    Handle FCM token updates
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Update user's FCM token"""
        serializer = FCMTokenSerializer(data=request.data)
        if serializer.is_valid():
            fcm_token = serializer.validated_data['fcm_token']
            
            # Update user's FCM token
            request.user.fcm_token = fcm_token
            request.user.save(update_fields=['fcm_token'])
            
            logger.info(f"Updated FCM token for user {request.user.email}")
            
            return Response({
                'message': 'FCM token updated successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """Remove user's FCM token (for logout)"""
        if request.user.fcm_token:
            request.user.fcm_token = None
            request.user.save(update_fields=['fcm_token'])
            
            logger.info(f"Removed FCM token for user {request.user.email}")
            
            return Response({
                'message': 'FCM token removed successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'message': 'No FCM token to remove'
            }, status=status.HTTP_200_OK)


class MutedInstructorsView(APIView):
    """
    Get list of muted instructors and mute new instructors
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get list of muted instructors"""
        muted = MutedInstructor.objects.filter(user=request.user).select_related('instructor')
        serializer = MutedInstructorSerializer(muted, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Mute an instructor"""
        serializer = MuteInstructorSerializer(data=request.data)
        if serializer.is_valid():
            instructor_id = serializer.validated_data['instructor_id']
            
            # Check if user is trying to mute themselves
            if instructor_id == request.user.id:
                return Response({
                    'error': 'You cannot mute yourself'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create or get muted instructor relationship
            muted, created = MutedInstructor.objects.get_or_create(
                user=request.user,
                instructor_id=instructor_id
            )
            
            if created:
                logger.info(f"User {request.user.email} muted instructor {instructor_id}")
                return Response({
                    'message': 'Instructor muted successfully'
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'message': 'Instructor already muted'
                }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UnmuteInstructorView(APIView):
    """
    Unmute a specific instructor
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, instructor_id):
        """Unmute an instructor"""
        try:
            muted = MutedInstructor.objects.get(
                user=request.user,
                instructor_id=instructor_id
            )
            muted.delete()
            
            logger.info(f"User {request.user.email} unmuted instructor {instructor_id}")
            
            return Response({
                'message': 'Instructor unmuted successfully'
            }, status=status.HTTP_200_OK)
            
        except MutedInstructor.DoesNotExist:
            return Response({
                'error': 'Instructor is not muted'
            }, status=status.HTTP_404_NOT_FOUND)


class CheckMutedStatusView(APIView):
    """
    Check if a specific instructor is muted
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, instructor_id):
        """Check if instructor is muted"""
        is_muted = MutedInstructor.objects.filter(
            user=request.user,
            instructor_id=instructor_id
        ).exists()
        
        return Response({
            'is_muted': is_muted,
            'instructor_id': instructor_id
        }, status=status.HTTP_200_OK)


class InstructorRatingView(APIView):
    """
    Get instructor's average rating and total ratings count
    """
    def get(self, request, instructor_id):
        """Get average rating and count for an instructor"""
        try:
            # Verify instructor exists and is an instructor
            instructor = CustomUser.objects.get(id=instructor_id)
            if instructor.user_type != 'instructor':
                return Response({
                    'error': 'User is not an instructor'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get ratings for this instructor
            from django.db.models import Avg
            ratings = Rating.objects.filter(instructor_id=instructor_id)
            avg_rating = ratings.aggregate(Avg('rating'))['rating__avg'] or 0.0
            total_ratings = ratings.count()
            
            # Get user's rating if authenticated
            user_rating = None
            if request.user.is_authenticated:
                user_rating_obj = ratings.filter(user=request.user).first()
                if user_rating_obj:
                    user_rating = user_rating_obj.rating
            
            return Response({
                'instructor_id': instructor_id,
                'average_rating': round(avg_rating, 1),
                'total_ratings': total_ratings,
                'user_rating': user_rating
            }, status=status.HTTP_200_OK)
            
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'Instructor not found'
            }, status=status.HTTP_404_NOT_FOUND)


class SubmitRatingView(APIView):
    """
    Submit or update a rating for an instructor
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Submit or update rating"""
        serializer = SubmitRatingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            instructor_id = serializer.validated_data['instructor_id']
            rating_value = serializer.validated_data['rating']
            
            # Update or create rating
            rating, created = Rating.objects.update_or_create(
                user=request.user,
                instructor_id=instructor_id,
                defaults={'rating': rating_value}
            )
            
            action = 'submitted' if created else 'updated'
            logger.info(f"User {request.user.email} {action} rating {rating_value} for instructor {instructor_id}")
            
            return Response({
                'message': f'Rating {action} successfully',
                'rating': rating_value
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
