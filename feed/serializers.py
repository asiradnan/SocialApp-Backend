from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Post, Comment, PostReaction, UserScore, LeaderboardEntry

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
    
    class Meta:
        model = Post
        fields = [
            'id', 'author', 'content', 'image', 'created_at', 'updated_at',
            'reactions_count', 'comments_count', 'comments', 'reactions',
            'user_reaction', 'can_edit', 'can_delete', 'time_since_created'
        ]
        read_only_fields = [
            'id', 'author', 'created_at', 'updated_at', 
            'reactions_count', 'comments_count'
        ]
    
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
        fields = ['content', 'image']
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class PostUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating posts"""
    
    class Meta:
        model = Post
        fields = ['content', 'image']
    
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
            'period_type', 'year', 'week_number', 'month_number', 'created_at'
        ]
        read_only_fields = ['created_at']


class CurrentLeaderboardSerializer(serializers.Serializer):
    """Serializer for current leaderboard data"""
    user = AuthorSerializer(read_only=True)
    rank = serializers.IntegerField()
    points = serializers.IntegerField()
    reactions_count = serializers.IntegerField()
    comments_count = serializers.IntegerField()
    
    def to_representation(self, instance):
        """Custom representation for leaderboard data"""
        if isinstance(instance, UserScore):
            period_type = self.context.get('period_type', 'total')
            
            if period_type == 'weekly':
                points = instance.weekly_points
                reactions = instance.weekly_reactions
                comments = instance.weekly_comments
            elif period_type == 'monthly':
                points = instance.monthly_points
                reactions = instance.monthly_reactions
                comments = instance.monthly_comments
            else:
                points = instance.total_points
                reactions = instance.total_reactions
                comments = instance.total_comments
            
            return {
                'user': AuthorSerializer(instance.user).data,
                'rank': self.context.get('rank', 1),
                'points': points,
                'reactions_count': reactions,
                'comments_count': comments,
            }
        return super().to_representation(instance)


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
    weekly_reactions = serializers.IntegerField()
    weekly_comments = serializers.IntegerField()
    monthly_reactions = serializers.IntegerField()
    monthly_comments = serializers.IntegerField()
