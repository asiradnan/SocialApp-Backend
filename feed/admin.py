from django.contrib import admin
from .models import Post, Poll, Comment, PostReaction, PollVote

admin.site.register(Post)
admin.site.register(Poll)
admin.site.register(Comment)
admin.site.register(PostReaction)
admin.site.register(PollVote)
