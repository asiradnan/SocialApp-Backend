from django.shortcuts import get_object_or_404
from django.db.models import Q, F
from django.db import transaction
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from itertools import chain

from .models import Post, Comment, PostReaction, UserScore, LeaderboardEntry, Poll, PollOption, PollVote
from .serializers import (
    PostSerializer, PostCreateSerializer, PostUpdateSerializer,
    CommentSerializer, CommentCreateSerializer, PostReactionSerializer,
    UserScoreSerializer, LeaderboardSerializer, CurrentLeaderboardSerializer,
    UserStatsSerializer, PollSerializer, PollCreateSerializer, PollUpdateSerializer,
    PollOptionSerializer, FeedItemSerializer
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


# Poll Views

class PollListCreateView(generics.ListCreateAPIView):
    """
    GET: List all polls with pagination
    POST: Create a new poll
    """
    serializer_class = PollSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PostPagination
    
    def get_queryset(self):
        queryset = Poll.objects.filter(is_active=True).select_related('author').prefetch_related('options', 'votes')
        
        # Filter by author if specified
        author_id = self.request.query_params.get('author_id')
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(question__icontains=search) | 
                Q(author__first_name__icontains=search) |
                Q(author__last_name__icontains=search)
            )
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PollCreateSerializer
        return PollSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PollDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a specific poll
    PUT/PATCH: Update a poll (only by author)
    DELETE: Delete a poll (only by author or admin)
    """
    queryset = Poll.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PollUpdateSerializer
        return PollSerializer
    
    def get_object(self):
        obj = get_object_or_404(Poll, pk=self.kwargs['pk'], is_active=True)
        return obj
    
    def perform_update(self, serializer):
        poll = self.get_object()
        if poll.author != self.request.user:
            raise permissions.PermissionDenied("You can only edit your own polls.")
        
        with transaction.atomic():
            # Check if options are being updated
            options_data = serializer.validated_data.get('options')
            if options_data is not None:
                # Store original vote count for response
                original_votes = poll.total_votes
                
                # Remove all existing poll options and their votes
                PollVote.objects.filter(poll=poll).delete()
                poll.options.all().delete()
                
                # Reset poll vote count
                poll.total_votes = 0
                poll.save()
                
                # Create new options
                for option_text in options_data:
                    PollOption.objects.create(poll=poll, text=option_text)
                
                # Log the change if there were votes
                if original_votes > 0:
                    print(f"Poll {poll.id} options updated - {original_votes} votes were reset")
            
            # Update other fields
            for attr, value in serializer.validated_data.items():
                if attr != 'options':
                    setattr(poll, attr, value)
            poll.save()


    
    def perform_destroy(self, instance):
        if instance.author != self.request.user and self.request.user.user_type != 'admin':
            raise permissions.PermissionDenied("You can only delete your own polls.")
        # Soft delete
        instance.is_active = False
        instance.save()


class PollVoteView(APIView):
    """
    POST: Vote on a poll
    DELETE: Remove vote from a poll
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, poll_id):
        poll = get_object_or_404(Poll, pk=poll_id, is_active=True)
        option_id = request.data.get('option_id')
        
        if not option_id:
            return Response(
                {'error': 'option_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            option = poll.options.get(id=option_id)
        except PollOption.DoesNotExist:
            return Response(
                {'error': 'Invalid option_id'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Check if user already voted
            existing_vote = PollVote.objects.filter(poll=poll, user=request.user).first()
            
            if existing_vote:
                # Update existing vote
                old_option = existing_vote.option
                if old_option.id != option.id:
                    # Decrement old option count
                    PollOption.objects.filter(pk=old_option.pk).update(
                        votes_count=F('votes_count') - 1
                    )
                    # Increment new option count
                    PollOption.objects.filter(pk=option.pk).update(
                        votes_count=F('votes_count') + 1
                    )
                    # Update vote
                    existing_vote.option = option
                    existing_vote.save()
                    
                    return Response({
                        'message': 'Vote updated successfully',
                        'option_id': option.id,
                        'option_text': option.text
                    })
                else:
                    return Response(
                        {'message': 'You have already voted for this option'}, 
                        status=status.HTTP_200_OK
                    )
            else:
                # Create new vote
                PollVote.objects.create(poll=poll, option=option, user=request.user)
                # Increment option count
                PollOption.objects.filter(pk=option.pk).update(
                    votes_count=F('votes_count') + 1
                )
                # Increment total votes
                Poll.objects.filter(pk=poll.pk).update(
                    total_votes=F('total_votes') + 1
                )
                
                return Response({
                    'message': 'Vote cast successfully',
                    'option_id': option.id,
                    'option_text': option.text
                }, status=status.HTTP_201_CREATED)
    
    def delete(self, request, poll_id):
        poll = get_object_or_404(Poll, pk=poll_id, is_active=True)
        
        try:
            vote = PollVote.objects.get(poll=poll, user=request.user)
            with transaction.atomic():
                # Decrement option count
                PollOption.objects.filter(pk=vote.option.pk).update(
                    votes_count=F('votes_count') - 1
                )
                # Decrement total votes
                Poll.objects.filter(pk=poll.pk).update(
                    total_votes=F('total_votes') - 1
                )
                vote.delete()
            
            return Response({'message': 'Vote removed successfully'}, status=status.HTTP_204_NO_CONTENT)
        except PollVote.DoesNotExist:
            return Response(
                {'error': 'Vote not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class UserPollsView(generics.ListAPIView):
    """Get all polls by a specific user"""
    serializer_class = PollSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PostPagination
    
    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return Poll.objects.filter(
            author_id=user_id, 
            is_active=True
        ).select_related('author').prefetch_related('options', 'votes')


# Post Views (existing)

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
        
        serializer = PostReactionSerializer(reaction, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def delete(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id, is_active=True)
        
        try:
            reaction = PostReaction.objects.get(post=post, user=request.user)
            reaction.delete()
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


# Combined Feed View

class FeedView(generics.ListAPIView):
    """
    Get combined feed of posts and polls ordered by creation time
    """
    serializer_class = FeedItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PostPagination
    
    def get_queryset(self):
        # Get posts and polls
        posts = Post.objects.filter(is_active=True).select_related('author').prefetch_related(
            'reactions', 'comments__author'
        )
        polls = Poll.objects.filter(is_active=True).select_related('author').prefetch_related(
            'options', 'votes'
        )
        
        # Optional: Filter by time range
        time_filter = self.request.query_params.get('time_filter')
        if time_filter == 'today':
            time_threshold = timezone.now() - timedelta(days=1)
            posts = posts.filter(created_at__gte=time_threshold)
            polls = polls.filter(created_at__gte=time_threshold)
        elif time_filter == 'week':
            time_threshold = timezone.now() - timedelta(weeks=1)
            posts = posts.filter(created_at__gte=time_threshold)
            polls = polls.filter(created_at__gte=time_threshold)
        elif time_filter == 'month':
            time_threshold = timezone.now() - timedelta(days=30)
            posts = posts.filter(created_at__gte=time_threshold)
            polls = polls.filter(created_at__gte=time_threshold)
        
        # Create feed items
        post_items = [{'type': 'post', 'object': post, 'created_at': post.created_at} for post in posts]
        poll_items = [{'type': 'poll', 'object': poll, 'created_at': poll.created_at} for poll in polls]
        
        # Combine and sort by creation time (newest first)
        combined_feed = sorted(
            chain(post_items, poll_items),
            key=lambda x: x['created_at'],
            reverse=True
        )
        
        return combined_feed
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Apply pagination manually since we're working with a list
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# Leaderboard Views (existing)

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
            'total_poll_votes': user_score.total_poll_votes,  # ADD THIS
            'weekly_reactions': user_score.weekly_reactions,
            'weekly_comments': user_score.weekly_comments,
            'weekly_poll_votes': user_score.weekly_poll_votes,  # ADD THIS
            'monthly_reactions': user_score.monthly_reactions,
            'monthly_comments': user_score.monthly_comments,
            'monthly_poll_votes': user_score.monthly_poll_votes,  # ADD THIS
        }
        
        serializer = UserStatsSerializer(stats_data)
        return Response(serializer.data)

# Update leaderboard_summary function
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
    
    # Helper function to serialize user score
    def serialize_user_score(user_score, period='total'):
        if not user_score:
            return None
        
        if period == 'weekly':
            points = user_score.weekly_points
            reactions = user_score.weekly_reactions
            comments = user_score.weekly_comments
            poll_votes = user_score.weekly_poll_votes
        elif period == 'monthly':
            points = user_score.monthly_points
            reactions = user_score.monthly_reactions
            comments = user_score.monthly_comments
            poll_votes = user_score.monthly_poll_votes
        else:
            points = user_score.total_points
            reactions = user_score.total_reactions
            comments = user_score.total_comments
            poll_votes = user_score.total_poll_votes
        
        return {
            'user': {
                'id': user_score.user.id,
                'email': user_score.user.email,
                'full_name': f"{user_score.user.first_name} {user_score.user.last_name}".strip(),
                'user_type': user_score.user.user_type
            },
            'points': points,
            'reactions_count': reactions,
            'comments_count': comments,
            'poll_votes_count': poll_votes,  # ADD THIS
        }
    
    return Response({
        'total_users': total_users,
        'active_users_this_week': active_users_week,
        'active_users_this_month': active_users_month,
        'top_performers': {
            'all_time': serialize_user_score(top_total, 'total'),
            'this_week': serialize_user_score(top_weekly, 'weekly'),
            'this_month': serialize_user_score(top_monthly, 'monthly'),
        }
    })


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
def poll_votes_detail(request, poll_id):
    """Get detailed vote information for a poll"""
    poll = get_object_or_404(Poll, pk=poll_id, is_active=True)
    votes = PollVote.objects.filter(poll=poll).select_related('user', 'option')
    
    # Group votes by option
    vote_groups = {}
    for vote in votes:
        option_id = vote.option.id
        if option_id not in vote_groups:
            vote_groups[option_id] = {
                'option_text': vote.option.text,
                'votes_count': 0,
                'users': []
            }
        vote_groups[option_id]['votes_count'] += 1
        vote_groups[option_id]['users'].append({
            'id': vote.user.id,
            'email': vote.user.email,
            'full_name': f"{vote.user.first_name} {vote.user.last_name}".strip(),
            'user_type': vote.user.user_type
        })
    
    return Response({
        'poll_id': poll.id,
        'question': poll.question,
        'total_votes': poll.total_votes,
        'votes': vote_groups
    })



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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_polls(request):
    """Advanced search for polls"""
    query = request.GET.get('q', '')
    author = request.GET.get('author', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if not query and not author:
        return Response({'error': 'Search query or author is required'}, status=400)
    
    polls = Poll.objects.filter(is_active=True)
    
    if query:
        polls = polls.filter(
            Q(question__icontains=query) |
            Q(author__first_name__icontains=query) |
            Q(author__last_name__icontains=query)
        )
    
    if author:
        polls = polls.filter(
            Q(author__first_name__icontains=author) |
            Q(author__last_name__icontains=author) |
            Q(author__email__icontains=author)
        )
    
    if date_from:
        polls = polls.filter(created_at__gte=date_from)
    
    if date_to:
        polls = polls.filter(created_at__lte=date_to)
    
    polls = polls.select_related('author').prefetch_related('options', 'votes')[:50]
    
    serializer = PollSerializer(polls, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def feed_stats(request):
    """Get feed statistics"""
    total_posts = Post.objects.filter(is_active=True).count()
    total_polls = Poll.objects.filter(is_active=True).count()
    
    # Recent activity (last 24 hours)
    since = timezone.now() - timedelta(hours=24)
    recent_posts = Post.objects.filter(is_active=True, created_at__gte=since).count()
    recent_polls = Poll.objects.filter(is_active=True, created_at__gte=since).count()
    
    return Response({
        'total_posts': total_posts,
        'total_polls': total_polls,
        'total_feed_items': total_posts + total_polls,
        'recent_posts_24h': recent_posts,
        'recent_polls_24h': recent_polls,
        'recent_activity_24h': recent_posts + recent_polls,
    })


