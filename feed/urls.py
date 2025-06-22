from django.urls import path
from . import views

app_name = 'feed'

urlpatterns = [
    # Posts
    path('posts/', views.PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('posts/<int:post_id>/comments/', views.PostCommentsView.as_view(), name='post-comments'),
    path('posts/<int:post_id>/reactions/', views.PostReactionView.as_view(), name='post-reactions'),
    path('posts/<int:post_id>/reactions/detail/', views.post_reactions_detail, name='post-reactions-detail'),
    
    # Comments
    path('comments/<int:pk>/', views.CommentDetailView.as_view(), name='comment-detail'),
    
    # User posts
    path('users/<int:user_id>/posts/', views.UserPostsView.as_view(), name='user-posts'),
    
    # Feed and discovery
    path('feed/', views.FeedView.as_view(), name='feed'),
    path('trending/', views.trending_posts, name='trending-posts'),
    path('search/', views.search_posts, name='search-posts'),
]
