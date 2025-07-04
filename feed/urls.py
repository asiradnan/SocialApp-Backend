from django.urls import path
from . import views

app_name = 'feed'

urlpatterns = [
    # Post URLs
    path('posts/', views.PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('posts/<int:post_id>/comments/', views.PostCommentsView.as_view(), name='post-comments'),
    path('posts/<int:post_id>/reactions/', views.PostReactionView.as_view(), name='post-reactions'),
    path('posts/<int:post_id>/reactions/detail/', views.post_reactions_detail, name='post-reactions-detail'),
    path('comments/<int:pk>/', views.CommentDetailView.as_view(), name='comment-detail'),
    path('users/<int:user_id>/posts/', views.UserPostsView.as_view(), name='user-posts'),
    
    # Poll URLs
    path('polls/', views.PollListCreateView.as_view(), name='poll-list-create'),
    path('polls/<int:pk>/', views.PollDetailView.as_view(), name='poll-detail'),
    path('polls/<int:poll_id>/vote/', views.PollVoteView.as_view(), name='poll-vote'),
    path('polls/<int:poll_id>/votes/detail/', views.poll_votes_detail, name='poll-votes-detail'),
    path('users/<int:user_id>/polls/', views.UserPollsView.as_view(), name='user-polls'),
    
    # Combined Feed URLs
    path('feed/', views.FeedView.as_view(), name='feed'),
    path('feed/stats/', views.feed_stats, name='feed-stats'),
    
    # Search and Trending URLs
    path('search/posts/', views.search_posts, name='search-posts'),
    path('search/polls/', views.search_polls, name='search-polls'),
    
    # Leaderboard URLs
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
    path('leaderboard/historical/', views.HistoricalLeaderboardView.as_view(), name='historical-leaderboard'),
    path('leaderboard/summary/', views.leaderboard_summary, name='leaderboard-summary'),
    
    # User Stats URLs
    path('users/<int:user_id>/stats/', views.UserStatsView.as_view(), name='user-stats'),
    path('users/my-stats/', views.UserStatsView.as_view(), name='my-stats'),
]
