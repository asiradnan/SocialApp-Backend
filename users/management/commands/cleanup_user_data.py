from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import CustomUser
from feed.models import Post, Comment, PostReaction, PollVote, UserScore, LeaderboardEntry
import os

class Command(BaseCommand):
    help = 'Clean up orphaned data and fix foreign key constraint issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Specific user ID to clean up (optional)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        dry_run = options.get('dry_run')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be deleted'))
        
        if user_id:
            try:
                user = CustomUser.objects.get(id=user_id)
                self.clean_user_data(user, dry_run)
            except CustomUser.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with ID {user_id} does not exist')
                )
        else:
            self.clean_all_orphaned_data(dry_run)
    
    def clean_user_data(self, user, dry_run=False):
        """Clean data for a specific user"""
        self.stdout.write(f'Cleaning data for user: {user.email}')
        
        # Count data
        posts_count = user.posts.count()
        comments_count = user.comments.count()
        reactions_count = user.post_reactions.count()
        votes_count = user.poll_votes.count()
        pics_count = user.profile_pictures.count()
        
        self.stdout.write(f'  Posts: {posts_count}')
        self.stdout.write(f'  Comments: {comments_count}')
        self.stdout.write(f'  Reactions: {reactions_count}')
        self.stdout.write(f'  Poll Votes: {votes_count}')
        self.stdout.write(f'  Profile Pictures: {pics_count}')
        
        if not dry_run:
            with transaction.atomic():
                # Delete media files
                for post in user.posts.all():
                    if post.image and os.path.isfile(post.image.path):
                        os.remove(post.image.path)
                        self.stdout.write(f'    Deleted file: {post.image.path}')
                
                for pic in user.profile_pictures.all():
                    if pic.image and os.path.isfile(pic.image.path):
                        os.remove(pic.image.path)
                        self.stdout.write(f'    Deleted file: {pic.image.path}')
                
                # Hard delete related objects
                user.posts.all().delete()
                user.comments.all().delete()
                user.post_reactions.all().delete()
                user.poll_votes.all().delete()
                user.profile_pictures.all().delete()
                
                # Delete user scores and leaderboard entries
                UserScore.objects.filter(user=user).delete()
                LeaderboardEntry.objects.filter(user=user).delete()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully cleaned data for user: {user.email}')
                )
    
    def clean_all_orphaned_data(self, dry_run=False):
        """Clean orphaned data across the system"""
        self.stdout.write('Scanning for orphaned data...')
        
        # Find orphaned comments (author doesn't exist)
        orphaned_comments = Comment.objects.filter(author__isnull=True)
        self.stdout.write(f'Found {orphaned_comments.count()} orphaned comments')
        
        # Find orphaned posts
        orphaned_posts = Post.objects.filter(author__isnull=True)
        self.stdout.write(f'Found {orphaned_posts.count()} orphaned posts')
        
        # Find orphaned reactions
        orphaned_reactions = PostReaction.objects.filter(user__isnull=True)
        self.stdout.write(f'Found {orphaned_reactions.count()} orphaned reactions')
        
        # Find orphaned votes
        orphaned_votes = PollVote.objects.filter(user__isnull=True)
        self.stdout.write(f'Found {orphaned_votes.count()} orphaned poll votes')
        
        if not dry_run and (orphaned_comments.exists() or orphaned_posts.exists() or 
                           orphaned_reactions.exists() or orphaned_votes.exists()):
            with transaction.atomic():
                # Delete orphaned data
                orphaned_comments.delete()
                orphaned_posts.delete()
                orphaned_reactions.delete()
                orphaned_votes.delete()
                
                self.stdout.write(
                    self.style.SUCCESS('Successfully cleaned orphaned data')
                )
        elif not orphaned_comments.exists() and not orphaned_posts.exists():
            self.stdout.write(
                self.style.SUCCESS('No orphaned data found - database is clean!')
            )
