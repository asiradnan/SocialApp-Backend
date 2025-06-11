# Alternative serializer - completely removes username from registration
from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    email = serializers.EmailField()

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'password2', 'date_of_birth', 'gender', 'user_type']  # Removed username

    def validate_email(self, value):
        # Normalize email to lowercase
        email = value.lower()
        
        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        
        return email

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        
        # Auto-generate username from email
        email_prefix = validated_data['email'].split('@')[0]
        username = email_prefix
        
        # Handle duplicate usernames by adding numbers
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{email_prefix}{counter}"
            counter += 1
        
        # Create user with auto-generated username
        user = CustomUser.objects.create_user(
            username=username,  # Auto-generated
            email=validated_data['email'],
            password=validated_data['password'],
            date_of_birth=validated_data.get('date_of_birth'),
            gender=validated_data.get('gender', ''),
            user_type=validated_data.get('user_type', '')
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate_email(self, value):
        return value.lower()  # Normalize email to lowercase
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            # Use email for authentication
            user = authenticate(username=email, password=password)
            
            if not user:
                # Check if user exists with this email
                if not CustomUser.objects.filter(email=email).exists():
                    raise serializers.ValidationError("No account found with this email address.")
                else:
                    raise serializers.ValidationError("Invalid password.")
            
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
                
            data['user'] = user
        else:
            raise serializers.ValidationError("Must include email and password.")
            
        return data