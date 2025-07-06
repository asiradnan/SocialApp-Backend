from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Post, Comment, PostReaction, UserScore, LeaderboardEntry, Poll, PollOption, PollVote

User = get_user_model()


class AuthorSerializer(serializers.ModelSerializer):
    """Serializer for displaying author information in posts and comments"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'user_type']
        read_only_fields = ['id', 'email', 'first_name', 'last_name', 'user_type']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class PollOptionSerializer(serializers.ModelSerializer):
    """Serializer for poll options"""
    vote_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = PollOption
        fields = ['id', 'text', 'votes_count', 'vote_percentage']
        read_only_fields = ['id', 'votes_count']
    
    def get_vote_percentage(self, obj):
        """Calculate vote percentage for this option"""
        if obj.poll.total_votes == 0:
            return 0
        return round((obj.votes_count / obj.poll.total_votes) * 100, 1)


class PollSerializer(serializers.ModelSerializer):
    """Serializer for polls"""
    author = AuthorSerializer(read_only=True)
    options = PollOptionSerializer(many=True, read_only=True)
    user_vote = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    time_since_created = serializers.SerializerMethodField()
    media_type = serializers.ReadOnlyField()
    is_image = serializers.ReadOnlyField()
    is_video = serializers.ReadOnlyField()
    media_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Poll
        fields = [
            'id', 'author', 'question', 'media', 'created_at', 'updated_at',
            'total_votes', 'options', 'user_vote', 'can_edit', 'can_delete',
            'time_since_created', 'media_type', 'is_image', 'is_video', 'media_url'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at', 'total_votes']
    
    def get_media_url(self, obj):
        """Get the full URL for the media file"""
        if obj.media:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.media.url)
            return obj.media.url
        return None
    
    def get_user_vote(self, obj):
        """Get current user's vote for this poll"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        try:
            vote = obj.votes.get(user=request.user)
            return {
                'option_id': vote.option.id,
                'option_text': vote.option.text
            }
        except PollVote.DoesNotExist:
            return None
    
    def get_can_edit(self, obj):
        """Check if current user can edit this poll"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user
    
    def get_can_delete(self, obj):
        """Check if current user can delete this poll"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user or request.user.user_type == 'admin'
    
    def get_time_since_created(self, obj):
        """Get human-readable time since poll creation"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at)


class PollCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating polls"""
    options = serializers.ListField(
        child=serializers.CharField(max_length=200),
        min_length=2,
        max_length=10,
        write_only=True
    )
    
    class Meta:
        model = Poll
        fields = ['question', 'media', 'options']
    
    def validate_media(self, value):
        """Validate that the uploaded file is either an image or video"""
        if value:
            import os
            file_extension = os.path.splitext(value.name)[1].lower()
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.webm']
            
            if file_extension not in allowed_extensions:
                raise serializers.ValidationError(
                    "Only image files (jpg, jpeg, png, gif) and video files (mp4, mov, avi, webm) are allowed."
                )
            
            max_size = 50 * 1024 * 1024  # 50MB
            if value.size > max_size:
                raise serializers.ValidationError("File size cannot exceed 50MB.")
        
        return value
    
    def validate_options(self, value):
        """Validate poll options"""
        if len(value) < 2:
            raise serializers.ValidationError("Poll must have at least 2 options.")
        if len(value) > 10:
            raise serializers.ValidationError("Poll cannot have more than 10 options.")
        
        # Remove duplicates and empty options
        cleaned_options = []
        for option in value:
            option = option.strip()
            if option and option not in cleaned_options:
                cleaned_options.append(option)
        
        if len(cleaned_options) < 2:
            raise serializers.ValidationError("Poll must have at least 2 unique, non-empty options.")
        
        return cleaned_options
    
    def create(self, validated_data):
        options_data = validated_data.pop('options')
        validated_data['author'] = self.context['request'].user
        
        poll = Poll.objects.create(**validated_data)
        
        # Create poll options
        for option_text in options_data:
            PollOption.objects.create(poll=poll, text=option_text)
        
        return poll


class PollUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating polls"""
    options = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Poll
        fields = ['question', 'media', 'options']
    
    def validate_media(self, value):
        """Validate that the uploaded file is either an image or video"""
        if value:
            import os
            file_extension = os.path.splitext(value.name)[1].lower()
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.webm']
            
            if file_extension not in allowed_extensions:
                raise serializers.ValidationError(
                    "Only image files (jpg, jpeg, png, gif) and video files (mp4, mov, avi, webm) are allowed."
                )
            
            max_size = 50 * 1024 * 1024  # 50MB
            if value.size > max_size:
                raise serializers.ValidationError("File size cannot exceed 50MB.")
        
        return value
    
    def to_internal_value(self, data):
        """Handle different input formats before validation"""
        # Make a mutable copy of the data
        if hasattr(data, 'copy'):
            internal_data = data.copy()
        else:
            internal_data = dict(data)
        
        # Handle options field specially
        options_raw = None
        
        # Try different ways to get options data
        if hasattr(data, 'getlist'):
            # Multipart form data - try different field names
            options_raw = (data.getlist('options[]') or 
                          data.getlist('options') or 
                          data.get('options'))
        elif 'options' in data:
            options_raw = data['options']
        
        if options_raw is not None:
            options_list = []
            
            # Handle different formats
            if hasattr(options_raw, 'all'):  # RelatedManager
                options_list = [str(option.text) for option in options_raw.all()]
            elif isinstance(options_raw, dict):
                # Handle dictionary format like {"0": "option1", "1": "option2"}
                # Sort by keys to maintain order
                sorted_keys = sorted(options_raw.keys(), key=lambda x: int(x) if str(x).isdigit() else float('inf'))
                options_list = [str(options_raw[key]).strip() for key in sorted_keys if str(options_raw[key]).strip()]
            elif isinstance(options_raw, str):
                # Handle JSON string or single option
                try:
                    import json
                    parsed = json.loads(options_raw)
                    if isinstance(parsed, list):
                        options_list = [str(option).strip() for option in parsed]
                    elif isinstance(parsed, dict):
                        # Handle JSON object format
                        sorted_keys = sorted(parsed.keys(), key=lambda x: int(x) if str(x).isdigit() else float('inf'))
                        options_list = [str(parsed[key]).strip() for key in sorted_keys if str(parsed[key]).strip()]
                    else:
                        options_list = [str(parsed).strip()] if str(parsed).strip() else []
                except (json.JSONDecodeError, ValueError):
                    options_list = [options_raw.strip()] if options_raw.strip() else []
            elif isinstance(options_raw, (list, tuple)):
                options_list = [str(option).strip() for option in options_raw if str(option).strip()]
            else:
                options_list = [str(options_raw).strip()] if str(options_raw).strip() else []
            
            # Remove duplicates while preserving order
            seen = set()
            cleaned_options = []
            for option in options_list:
                if option and option not in seen:
                    seen.add(option)
                    cleaned_options.append(option)
            
            internal_data['options'] = cleaned_options
        
        return super().to_internal_value(internal_data)
    
    def validate_options(self, value):
        """Validate poll options - this runs after to_internal_value"""
        if not value:  # Empty list or None
            return value
        
        if len(value) < 2:
            raise serializers.ValidationError("Poll must have at least 2 options.")
        if len(value) > 10:
            raise serializers.ValidationError("Poll cannot have more than 10 options.")
        
        return value
    
    def validate(self, data):
        """Ensure user can only update their own polls"""
        request = self.context.get('request')
        if request and request.user != self.instance.author:
            raise serializers.ValidationError("You can only edit your own polls.")
        
        return data



class FeedItemSerializer(serializers.Serializer):
    """Serializer for combined feed items (posts and polls)"""
    type = serializers.CharField()
    data = serializers.SerializerMethodField()
    
    def get_data(self, obj):
        """Serialize the actual object based on its type"""
        if obj['type'] == 'post':
            return PostSerializer(obj['object'], context=self.context).data
        elif obj['type'] == 'poll':
            return PollSerializer(obj['object'], context=self.context).data
        return None


class PostReactionSerializer(serializers.ModelSerializer):
    """Serializer for post reactions"""
    user = AuthorSerializer(read_only=True)
    emoji = serializers.ReadOnlyField()
    reaction_display = serializers.CharField(source='get_reaction_type_display', read_only=True)
    
    class Meta:
        model = PostReaction
        fields = ['id', 'user', 'reaction_type', 'reaction_display', 'emoji', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for comments with nested replies"""
    author = AuthorSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    is_reply = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'author', 'content', 'created_at', 'updated_at', 
            'replies_count', 'replies', 'is_reply', 'parent',
            'can_edit', 'can_delete'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at', 'replies_count']
    
    def get_replies(self, obj):
        """Get replies for top-level comments only"""
        if obj.parent is None:  # Only show replies for top-level comments
            replies = obj.replies.filter(is_active=True)
            return CommentSerializer(replies, many=True, context=self.context).data
        return []
    
    def get_is_reply(self, obj):
        """Check if this comment is a reply"""
        return obj.parent is not None
    
    def get_can_edit(self, obj):
        """Check if current user can edit this comment"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user
    
    def get_can_delete(self, obj):
        """Check if current user can delete this comment"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user or obj.post.author == request.user
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate(self, data):
        """Validate comment nesting level"""
        parent = data.get('parent')
        if parent and parent.parent:
            raise serializers.ValidationError("Comments can only be nested 2 levels deep")
        return data


class PostSerializer(serializers.ModelSerializer):
    """Main serializer for posts"""
    author = AuthorSerializer(read_only=True)
    comments = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    time_since_created = serializers.SerializerMethodField()
    
    media_type = serializers.ReadOnlyField()
    is_image = serializers.ReadOnlyField()
    is_video = serializers.ReadOnlyField()
    media_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'author', 'content', 'image', 'created_at', 'updated_at',
            'reactions_count', 'comments_count', 'comments', 'reactions',
            'user_reaction', 'can_edit', 'can_delete', 'time_since_created',
            'media_type', 'is_image', 'is_video', 'media_url'  # Add these
        ]
        read_only_fields = [
            'id', 'author', 'created_at', 'updated_at', 
            'reactions_count', 'comments_count'
        ]
    
    def get_media_url(self, obj):
        """Get the full URL for the media file"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_comments(self, obj):
        """Get top-level comments only (replies are nested within)"""
        top_level_comments = obj.comments.filter(parent=None, is_active=True)
        return CommentSerializer(top_level_comments, many=True, context=self.context).data
    
    def get_reactions(self, obj):
        """Get reaction summary"""
        reactions = obj.reactions.all()
        reaction_summary = {}
        
        for reaction in reactions:
            reaction_type = reaction.reaction_type
            if reaction_type not in reaction_summary:
                reaction_summary[reaction_type] = {
                    'count': 0,
                    'emoji': reaction.emoji,
                    'users': []
                }
            reaction_summary[reaction_type]['count'] += 1
            reaction_summary[reaction_type]['users'].append({
                'id': reaction.user.id,
                'email': reaction.user.email,
                'full_name': f"{reaction.user.first_name} {reaction.user.last_name}".strip()
            })
        
        return reaction_summary
    
    def get_user_reaction(self, obj):
        """Get current user's reaction to this post"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        try:
            reaction = obj.reactions.get(user=request.user)
            return {
                'reaction_type': reaction.reaction_type,
                'emoji': reaction.emoji
            }
        except PostReaction.DoesNotExist:
            return None
    
    def get_can_edit(self, obj):
        """Check if current user can edit this post"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user
    
    def get_can_delete(self, obj):
        """Check if current user can delete this post"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.author == request.user or request.user.user_type == 'admin'
    
    def get_time_since_created(self, obj):
        """Get human-readable time since post creation"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at)
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class PostCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating posts"""
    
    class Meta:
        model = Post
        fields = ['content', 'image']  # Keep 'image' field name
    
    def validate_image(self, value):
        """Validate that the uploaded file is either an image or video"""
        if value:
            import os
            file_extension = os.path.splitext(value.name)[1].lower()
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.webm']
            
            if file_extension not in allowed_extensions:
                raise serializers.ValidationError(
                    "Only image files (jpg, jpeg, png, gif) and video files (mp4, mov, avi, webm) are allowed."
                )
            
            # Optional: Add file size validation
            max_size = 50 * 1024 * 1024  # 50MB
            if value.size > max_size:
                raise serializers.ValidationError("File size cannot exceed 50MB.")
        
        return value
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class PostUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating posts"""
    
    class Meta:
        model = Post
        fields = ['content', 'image']
    
    def validate_image(self, value):
        """Validate that the uploaded file is either an image or video"""
        if value:
            import os
            file_extension = os.path.splitext(value.name)[1].lower()
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.avi', '.webm']
            
            if file_extension not in allowed_extensions:
                raise serializers.ValidationError(
                    "Only image files (jpg, jpeg, png, gif) and video files (mp4, mov, avi, webm) are allowed."
                )
            
            # Optional: Add file size validation
            max_size = 50 * 1024 * 1024  # 50MB
            if value.size > max_size:
                raise serializers.ValidationError("File size cannot exceed 50MB.")
        
        return value
    
    def validate(self, data):
        """Ensure user can only update their own posts"""
        request = self.context.get('request')
        if request and request.user != self.instance.author:
            raise serializers.ValidationError("You can only edit your own posts.")
        return data


class CommentCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating comments"""
    
    class Meta:
        model = Comment
        fields = ['content', 'parent']
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['post_id'] = self.context['post_id']
        return super().create(validated_data)
    
    def validate(self, data):
        """Validate comment nesting and parent post"""
        parent = data.get('parent')
        post_id = self.context.get('post_id')
        
        if parent:
            # Check nesting level
            if parent.parent:
                raise serializers.ValidationError("Comments can only be nested 2 levels deep")
            # Check parent belongs to same post
            if parent.post_id != post_id:
                raise serializers.ValidationError("Parent comment must belong to the same post")
        
        return data


class ReactionSummarySerializer(serializers.Serializer):
    """Serializer for reaction summary statistics"""
    reaction_type = serializers.CharField()
    count = serializers.IntegerField()
    emoji = serializers.CharField()
    users = serializers.ListField(child=serializers.DictField())


class UserScoreSerializer(serializers.ModelSerializer):
    """Serializer for user scores"""
    user = AuthorSerializer(read_only=True)
    rank = serializers.SerializerMethodField()
    
    class Meta:
        model = UserScore
        fields = [
            'user', 'total_points', 'weekly_points', 'monthly_points',
            'total_reactions', 'total_comments', 'weekly_reactions', 
            'weekly_comments', 'monthly_reactions', 'monthly_comments',
            'rank', 'updated_at'
        ]
        read_only_fields = ['user', 'updated_at']
    
    def get_rank(self, obj):
        """Get current rank based on total points"""
        return UserScore.objects.filter(total_points__gt=obj.total_points).count() + 1


class LeaderboardSerializer(serializers.ModelSerializer):
    """Serializer for leaderboard entries"""
    user = AuthorSerializer(read_only=True)
    
    class Meta:
        model = LeaderboardEntry
        fields = [
            'user', 'rank', 'points', 'reactions_count', 'comments_count',
            'poll_votes_count',  # ADD THIS
            'period_type', 'year', 'week_number', 'month_number', 'created_at'
        ]
        read_only_fields = ['created_at']



class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics"""
    user = AuthorSerializer(read_only=True)
    total_points = serializers.IntegerField()
    weekly_points = serializers.IntegerField()
    monthly_points = serializers.IntegerField()
    total_rank = serializers.IntegerField()
    weekly_rank = serializers.IntegerField()
    monthly_rank = serializers.IntegerField()
    total_reactions = serializers.IntegerField()
    total_comments = serializers.IntegerField()
    total_poll_votes = serializers.IntegerField()  # ADD THIS
    weekly_reactions = serializers.IntegerField()
    weekly_comments = serializers.IntegerField()
    weekly_poll_votes = serializers.IntegerField()  # ADD THIS
    monthly_reactions = serializers.IntegerField()
    monthly_comments = serializers.IntegerField()
    monthly_poll_votes = serializers.IntegerField()  # ADD THIS

class CurrentLeaderboardSerializer(serializers.Serializer):
    """Serializer for current leaderboard data"""
    user = AuthorSerializer(read_only=True)
    rank = serializers.IntegerField()
    points = serializers.IntegerField()
    reactions_count = serializers.IntegerField()
    comments_count = serializers.IntegerField()
    poll_votes_count = serializers.IntegerField()  # ADD THIS
    
    def to_representation(self, instance):
        """Custom representation for leaderboard data"""
        if isinstance(instance, UserScore):
            period_type = self.context.get('period_type', 'total')
            
            if period_type == 'weekly':
                points = instance.weekly_points
                reactions = instance.weekly_reactions
                comments = instance.weekly_comments
                poll_votes = instance.weekly_poll_votes  # ADD THIS
            elif period_type == 'monthly':
                points = instance.monthly_points
                reactions = instance.monthly_reactions
                comments = instance.monthly_comments
                poll_votes = instance.monthly_poll_votes  # ADD THIS
            else:
                points = instance.total_points
                reactions = instance.total_reactions
                comments = instance.total_comments
                poll_votes = instance.total_poll_votes  # ADD THIS
            
            return {
                'user': AuthorSerializer(instance.user).data,
                'rank': self.context.get('rank', 1),
                'points': points,
                'reactions_count': reactions,
                'comments_count': comments,
                'poll_votes_count': poll_votes,  # ADD THIS
            }
        return super().to_representation(instance)

