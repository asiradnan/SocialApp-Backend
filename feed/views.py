from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Count, Case, When, IntegerField
from django.db import transaction
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib.auth import get_user_model

from .models import Post, Comment, PostReaction, UserScore, LeaderboardEntry
from .serializers import (
    PostSerializer, PostCreateSerializer, PostUpdateSerializer,
    CommentSerializer, CommentCreateSerializer, PostReactionSerializer,
    UserScoreSerializer, LeaderboardSerializer, CurrentLeaderboardSerializer,
    UserStatsSerializer
)

User = get_user_model()


class PostPagination(PageNumberPagination):
    """Custom pagination for posts"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class LeaderboardPagination(PageNumberPagination):
    """Custom pagination for leaderboards"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class PostListCreateView(generics.ListCreateAPIView):
    """
    GET: List all posts with pagination
    POST: Create a new post
    """
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PostPagination
    
    def get_queryset(self):
        queryset = Post.objects.filter(is_active=True).select_related('author').prefetch_related(
            'reactions', 'comments__author', 'comments__replies'
        )
        
        # Filter by author if specified
        author_id = self.request.query_params.get('author_id')
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(content__icontains=search) | 
                Q(author__first_name__icontains=search) |
                Q(author__last_name__icontains=search)
            )
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostCreateSerializer
        return PostSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific post
    PUT/PATCH: Update a post (only by author)
    DELETE: Delete a post (only by author or admin)
    """
    queryset = Post.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PostUpdateSerializer
        return PostSerializer
    
    def get_object(self):
        obj = get_object_or_404(Post, pk=self.kwargs['pk'], is_active=True)
        return obj
    
    def perform_update(self, serializer):
        post = self.get_object()
        if post.author != self.request.user:
            raise permissions.PermissionDenied("You can only edit your own posts.")
        serializer.save()
    
    def perform_destroy(self, instance):
        if instance.author != self.request.user and self.request.user.user_type != 'admin':
            raise permissions.PermissionDenied("You can only delete your own posts.")
        # Soft delete
        instance.is_active = False
        instance.save()


class PostCommentsView(generics.ListCreateAPIView):
    """
    GET: List comments for a specific post
    POST: Create a new comment on a post
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        post_id = self.kwargs['post_id']
        # Only return top-level comments, replies are nested in serializer
        return Comment.objects.filter(
            post_id=post_id, 
            parent=None, 
            is_active=True
        ).select_related('author').prefetch_related('replies__author')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return CommentSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['post_id'] = self.kwargs['post_id']
        return context
    
    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs['post_id'], is_active=True)
        comment = serializer.save(author=self.request.user, post=post)
        
        # Update comment count
        with transaction.atomic():
            Post.objects.filter(pk=post.pk).update(
                comments_count=F('comments_count') + 1
            )
            
            # Update replies count if this is a reply
            if comment.parent:
                Comment.objects.filter(pk=comment.parent.pk).update(
                    replies_count=F('replies_count') + 1
                )


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific comment
    PUT/PATCH: Update a comment (only by author)
    DELETE: Delete a comment (only by author or post author)
    """
    queryset = Comment.objects.filter(is_active=True)
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_update(self, serializer):
        comment = self.get_object()
        if comment.author != self.request.user:
            raise permissions.PermissionDenied("You can only edit your own comments.")
        serializer.save()
    
    def perform_destroy(self, instance):
        if (instance.author != self.request.user and 
            instance.post.author != self.request.user and 
            self.request.user.user_type != 'admin'):
            raise permissions.PermissionDenied("You can only delete your own comments or comments on your posts.")
        
        # Update counts and soft delete
        with transaction.atomic():
            Post.objects.filter(pk=instance.post.pk).update(
                comments_count=F('comments_count') - 1
            )
            
            if instance.parent:
                Comment.objects.filter(pk=instance.parent.pk).update(
                    replies_count=F('replies_count') - 1
                )
            
            instance.is_active = False
            instance.save()


class PostReactionView(APIView):
    """
    POST: Add or update reaction to a post
    DELETE: Remove reaction from a post
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id, is_active=True)
        reaction_type = request.data.get('reaction_type')
        
        if not reaction_type or reaction_type not in dict(PostReaction.REACTION_CHOICES):
            return Response(
                {'error': 'Valid reaction_type is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            reaction, created = PostReaction.objects.update_or_create(
                post=post,
                user=request.user,
                defaults={'reaction_type': reaction_type}
            )
            
            if created:
                # Increment reaction count
                Post.objects.filter(pk=post.pk).update(
                    reactions_count=F('reactions_count') + 1
                )
        
        serializer = PostReactionSerializer(reaction, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def delete(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id, is_active=True)
        
        try:
            reaction = PostReaction.objects.get(post=post, user=request.user)
            with transaction.atomic():
                reaction.delete()
                Post.objects.filter(pk=post.pk).update(
                    reactions_count=F('reactions_count') - 1
                )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PostReaction.DoesNotExist:
            return Response(
                {'error': 'Reaction not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class UserPostsView(generics.ListAPIView):
    """Get all posts by a specific user"""
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PostPagination
    
    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return Post.objects.filter(
            author_id=user_id, 
            is_active=True
        ).select_related('author').prefetch_related('reactions', 'comments')


class FeedView(generics.ListAPIView):
    """
    Get personalized feed for the current user
    This could be enhanced with following/friends logic
    """
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PostPagination
    
    def get_queryset(self):
        # For now, return all posts. You can enhance this with:
        # - Posts from followed users
        # - Posts from friends
        # - Trending posts
        # - Posts based on user interests
        
        queryset = Post.objects.filter(is_active=True).select_related('author').prefetch_related(
            'reactions', 'comments__author'
        )
        
        # Optional: Filter by time range
        time_filter = self.request.query_params.get('time_filter')
        if time_filter == 'today':
            queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=1))
        elif time_filter == 'week':
            queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(weeks=1))
        elif time_filter == 'month':
            queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=30))
        
        return queryset


# Leaderboard Views

class LeaderboardView(generics.ListAPIView):
    """
    Get current leaderboard
    Query params:
    - period: 'weekly', 'monthly', or 'total' (default)
    - limit: number of results (default 50)
    """
    serializer_class = CurrentLeaderboardSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LeaderboardPagination
    
    def get_queryset(self):
        period = self.request.query_params.get('period', 'total')
        limit = int(self.request.query_params.get('limit', 50))
        
        # Get all user scores and reset periods if needed
        user_scores = UserScore.objects.select_related('user').all()
        
        # Reset periods for all users if needed
        for score in user_scores:
            score.reset_weekly_if_needed()
            score.reset_monthly_if_needed()
        
        # Order by the appropriate field
        if period == 'weekly':
            queryset = user_scores.order_by('-weekly_points', '-updated_at')
        elif period == 'monthly':
            queryset = user_scores.order_by('-monthly_points', '-updated_at')
        else:
            queryset = user_scores.order_by('-total_points', '-updated_at')
        
        return queryset[:limit]
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['period_type'] = self.request.query_params.get('period', 'total')
        return context
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        period_type = request.query_params.get('period', 'total')
        
        # Add rank to each item
        leaderboard_data = []
        for rank, user_score in enumerate(queryset, 1):
            context = self.get_serializer_context()
            context['rank'] = rank
            serializer = self.get_serializer(user_score, context=context)
            leaderboard_data.append(serializer.data)
        
        return Response({
            'period': period_type,
            'count': len(leaderboard_data),
            'results': leaderboard_data
        })


class UserStatsView(APIView):
    """Get detailed stats for a specific user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, user_id=None):
        # If no user_id provided, use current user
        if user_id is None:
            user = request.user
        else:
            user = get_object_or_404(User, pk=user_id)
        
        # Get or create user score
        user_score = UserScore.get_or_create_for_user(user)
        user_score.reset_weekly_if_needed()
        user_score.reset_monthly_if_needed()
        
        # Calculate ranks
        total_rank = UserScore.objects.filter(total_points__gt=user_score.total_points).count() + 1
        weekly_rank = UserScore.objects.filter(weekly_points__gt=user_score.weekly_points).count() + 1
        monthly_rank = UserScore.objects.filter(monthly_points__gt=user_score.monthly_points).count() + 1
        
        stats_data = {
            'user': user,
            'total_points': user_score.total_points,
            'weekly_points': user_score.weekly_points,
            'monthly_points': user_score.monthly_points,
            'total_rank': total_rank,
            'weekly_rank': weekly_rank,
            'monthly_rank': monthly_rank,
            'total_reactions': user_score.total_reactions,
            'total_comments': user_score.total_comments,
            'weekly_reactions': user_score.weekly_reactions,
            'weekly_comments': user_score.weekly_comments,
            'monthly_reactions': user_score.monthly_reactions,
            'monthly_comments': user_score.monthly_comments,
        }
        
        serializer = UserStatsSerializer(stats_data)
        return Response(serializer.data)


class HistoricalLeaderboardView(generics.ListAPIView):
    """Get historical leaderboard data"""
    serializer_class = LeaderboardSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LeaderboardPagination
    
    def get_queryset(self):
        period_type = self.request.query_params.get('period', 'weekly')
        year = self.request.query_params.get('year')
        week = self.request.query_params.get('week')
        month = self.request.query_params.get('month')
        queryset = LeaderboardEntry.objects.filter(period_type=period_type).select_related('user')
        
        if year:
            queryset = queryset.filter(year=int(year))
        
        if period_type == 'weekly' and week:
            queryset = queryset.filter(week_number=int(week))
        elif period_type == 'monthly' and month:
            queryset = queryset.filter(month_number=int(month))
        
        return queryset.order_by('rank')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def post_reactions_detail(request, post_id):
    """Get detailed reaction information for a post"""
    post = get_object_or_404(Post, pk=post_id, is_active=True)
    reactions = PostReaction.objects.filter(post=post).select_related('user')
    
    # Group reactions by type
    reaction_groups = {}
    for reaction in reactions:
        reaction_type = reaction.reaction_type
        if reaction_type not in reaction_groups:
            reaction_groups[reaction_type] = {
                'emoji': reaction.emoji,
                'count': 0,
                'users': []
            }
        reaction_groups[reaction_type]['count'] += 1
        reaction_groups[reaction_type]['users'].append({
            'id': reaction.user.id,
            'email': reaction.user.email,
            'full_name': f"{reaction.user.first_name} {reaction.user.last_name}".strip(),
            'user_type': reaction.user.user_type
        })
    
    return Response({
        'post_id': post.id,
        'total_reactions': post.reactions_count,
        'reactions': reaction_groups
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def trending_posts(request):
    """Get trending posts based on recent activity"""
    # Posts with high engagement in the last 24 hours
    since = timezone.now() - timedelta(hours=24)
    
    trending = Post.objects.filter(
        is_active=True,
        created_at__gte=since
    ).annotate(
        engagement_score=F('reactions_count') + F('comments_count')
    ).filter(
        engagement_score__gt=0
    ).order_by('-engagement_score', '-created_at')[:20]
    
    serializer = PostSerializer(trending, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_posts(request):
    """Advanced search for posts"""
    query = request.GET.get('q', '')
    author = request.GET.get('author', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if not query and not author:
        return Response({'error': 'Search query or author is required'}, status=400)
    
    posts = Post.objects.filter(is_active=True)
    
    if query:
        posts = posts.filter(
            Q(content__icontains=query) |
            Q(author__first_name__icontains=query) |
            Q(author__last_name__icontains=query)
        )
    
    if author:
        posts = posts.filter(
            Q(author__first_name__icontains=author) |
            Q(author__last_name__icontains=author) |
            Q(author__email__icontains=author)
        )
    
    if date_from:
        posts = posts.filter(created_at__gte=date_from)
    
    if date_to:
        posts = posts.filter(created_at__lte=date_to)
    
    posts = posts.select_related('author').prefetch_related('reactions')[:50]
    
    serializer = PostSerializer(posts, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def save_weekly_leaderboard(request):
    """Manually save current weekly leaderboard (admin only)"""
    if request.user.user_type != 'admin':
        return Response({'error': 'Admin access required'}, status=403)
    
    current_date = timezone.now().date()
    year = current_date.year
    week_number = current_date.isocalendar()[1]
    
    # Get current weekly leaderboard
    user_scores = UserScore.objects.select_related('user').order_by('-weekly_points')[:100]
    
    saved_entries = []
    for rank, user_score in enumerate(user_scores, 1):
        if user_score.weekly_points > 0:  # Only save users with points
            entry, created = LeaderboardEntry.objects.update_or_create(
                user=user_score.user,
                period_type='weekly',
                year=year,
                week_number=week_number,
                defaults={
                    'points': user_score.weekly_points,
                    'rank': rank,
                    'reactions_count': user_score.weekly_reactions,
                    'comments_count': user_score.weekly_comments,
                }
            )
            saved_entries.append(entry)
    
    return Response({
        'message': f'Saved {len(saved_entries)} weekly leaderboard entries',
        'year': year,
        'week': week_number
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def save_monthly_leaderboard(request):
    """Manually save current monthly leaderboard (admin only)"""
    if request.user.user_type != 'admin':
        return Response({'error': 'Admin access required'}, status=403)
    
    current_date = timezone.now().date()
    year = current_date.year
    month_number = current_date.month
    
    # Get current monthly leaderboard
    user_scores = UserScore.objects.select_related('user').order_by('-monthly_points')[:100]
    
    saved_entries = []
    for rank, user_score in enumerate(user_scores, 1):
        if user_score.monthly_points > 0:  # Only save users with points
            entry, created = LeaderboardEntry.objects.update_or_create(
                user=user_score.user,
                period_type='monthly',
                year=year,
                month_number=month_number,
                defaults={
                    'points': user_score.monthly_points,
                    'rank': rank,
                    'reactions_count': user_score.monthly_reactions,
                    'comments_count': user_score.monthly_comments,
                }
            )
            saved_entries.append(entry)
    
    return Response({
        'message': f'Saved {len(saved_entries)} monthly leaderboard entries',
        'year': year,
        'month': month_number
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def leaderboard_summary(request):
    """Get leaderboard summary statistics"""
    total_users = UserScore.objects.count()
    active_users_week = UserScore.objects.filter(weekly_points__gt=0).count()
    active_users_month = UserScore.objects.filter(monthly_points__gt=0).count()
    
    # Top performers
    top_total = UserScore.objects.select_related('user').order_by('-total_points').first()
    top_weekly = UserScore.objects.select_related('user').order_by('-weekly_points').first()
    top_monthly = UserScore.objects.select_related('user').order_by('-monthly_points').first()
    
    return Response({
        'total_users': total_users,
        'active_users_this_week': active_users_week,
        'active_users_this_month': active_users_month,
        'top_performers': {
            'all_time': UserScoreSerializer(top_total).data if top_total else None,
            'this_week': UserScoreSerializer(top_weekly).data if top_weekly else None,
            'this_month': UserScoreSerializer(top_monthly).data if top_monthly else None,
        }
    })
