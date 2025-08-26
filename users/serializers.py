from rest_framework import serializers
from .models import CustomUser, ProfilePicture
from django.contrib.auth.password_validation import validate_password

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'password', 'password2', 'date_of_birth', 'gender', 'user_type']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords do not match.")
        
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password2')
        validated_data['email'] = validated_data['email'].lower()
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate_email(self, value):
        return value.lower()  # Normalize email to lowercase

class UserProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'date_of_birth', 'gender', 'user_type', 'profile_picture', 'profile_picture_url']

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture:
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

    def validate_email(self, value):
        if value:
            return value.lower()
        return value

    def update(self, instance, validated_data):
        # Update only the fields that are provided
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
    
class GoogleAuthSerializer(serializers.Serializer):
    idToken = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    name = serializers.CharField(required=True)
    
    def validate_email(self, value):
        return value.lower()

class GoogleSignupSerializer(serializers.Serializer):
    idToken = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    firstName = serializers.CharField(required=True, max_length=150)
    lastName = serializers.CharField(required=True, max_length=150)
    gender = serializers.CharField(required=False, max_length=10, allow_null=True, allow_blank=True)
    dateOfBirth = serializers.DateField(required=True)
    userType = serializers.CharField(required=False, default='standard')
    
    def validate_email(self, value):
        return value.lower()
    
    def validate_gender(self, value):
        # Handle cases where gender field is not provided or is empty
        if not value:
            return None
        
        valid_genders = ['male', 'female']
        if value.lower() not in valid_genders:
            return None
        return value.lower()
    
    def validate_userType(self, value):
        valid_types = ['instructor', 'standard']
        if value not in valid_types:
            return 'standard'
        return value
    
    def validate(self, data):
        # Check if user already exists
        email = data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return data
    
    def create(self, validated_data):
        # Remove idToken as it's not needed for user creation
        validated_data.pop('idToken', None)
        
        # Create user without password (Google authenticated)
        user = CustomUser(
            email=validated_data['email'],
            first_name=validated_data['firstName'],
            last_name=validated_data['lastName'],
            gender=validated_data.get('gender'),  # Will be None if not provided
            date_of_birth=validated_data['dateOfBirth'],
            user_type=validated_data.get('userType', 'standard'),
            is_active=True
        )
        # Set unusable password for Google users
        user.set_unusable_password()
        user.save()
        return user


class ProfilePictureSerializer(serializers.ModelSerializer):
    uploaded_at = serializers.DateTimeField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProfilePicture
        fields = ['id', 'image', 'image_url', 'uploaded_at', 'is_current', 'file_size']
        read_only_fields = ['id', 'uploaded_at', 'file_size']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def validate_image(self, value):
        """Validate the uploaded image"""
        if value:
            # Check file size (5MB limit)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Image file size cannot exceed 5MB.")
            
            # Check file type
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            import os
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in valid_extensions:
                raise serializers.ValidationError(
                    f"Invalid file type. Allowed types: {', '.join(valid_extensions)}"
                )
        
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        
        # If this is set as current, update the user's profile picture
        if validated_data.get('is_current', False):
            # Delete old profile picture if exists
            if user.profile_picture:
                user.delete_old_profile_picture()
        
        return super().create(validated_data)


class ProfilePictureUploadSerializer(serializers.Serializer):
    """Simplified serializer for profile picture upload"""
    image = serializers.ImageField(required=True)
    
    def validate_image(self, value):
        """Validate the uploaded image"""
        if value:
            # Check file size (5MB limit)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Image file size cannot exceed 5MB.")
            
            # Check file type
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            import os
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in valid_extensions:
                raise serializers.ValidationError(
                    f"Invalid file type. Allowed types: {', '.join(valid_extensions)}"
                )
        
        return value