from django.urls import path
from . import views

app_name = 'feed'

urlpatterns = [
    # Existing URLs
    path('posts/', views.PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('posts/<int:post_id>/comments/', views.PostCommentsView.as_view(), name='post-comments'),
    path('posts/<int:post_id>/reactions/', views.PostReactionView.as_view(), name='post-reactions'),
    path('posts/<int:post_id>/reactions/detail/', views.post_reactions_detail, name='post-reactions-detail'),
    path('comments/<int:pk>/', views.CommentDetailView.as_view(), name='comment-detail'),
    path('users/<int:user_id>/posts/', views.UserPostsView.as_view(), name='user-posts'),
    path('feed/', views.FeedView.as_view(), name='feed'),
    path('trending/', views.trending_posts, name='trending-posts'),
    path('search/', views.search_posts, name='search-posts'),
    
    # New Leaderboard URLs
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
    path('leaderboard/historical/', views.HistoricalLeaderboardView.as_view(), name='historical-leaderboard'),
    path('leaderboard/summary/', views.leaderboard_summary, name='leaderboard-summary'),
    path('leaderboard/save-weekly/', views.save_weekly_leaderboard, name='save-weekly-leaderboard'),
    path('leaderboard/save-monthly/', views.save_monthly_leaderboard, name='save-monthly-leaderboard'),
    path('users/<int:user_id>/stats/', views.UserStatsView.as_view(), name='user-stats'),
    path('users/my-stats/', views.UserStatsView.as_view(), name='my-stats'),
]
