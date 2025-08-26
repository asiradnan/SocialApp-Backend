# Comment Deletion Fix - Cascading Reply Count Update

## 🐛 **Problem Identified**

When deleting a comment that had replies, the `replies_count` was not being properly updated because:

1. **Soft Deletion**: The system uses soft deletion (`is_active = False`) instead of hard deletion
2. **No Cascading**: When a parent comment was deleted, its replies were not being soft-deleted
3. **Incorrect Count**: The system only decremented counts by 1, ignoring the number of replies
4. **Signal Mismatch**: Signals were set up for hard deletion but views used soft deletion

## ✅ **Solution Implemented**

### Updated Comment Deletion Logic

**File**: `/feed/views.py` - `CommentDetailView.perform_destroy()`

```python
def perform_destroy(self, instance):
    # Permission checks...
    
    with transaction.atomic():
        # Count how many comments will be deleted (comment + all its active replies)
        replies_to_delete = instance.replies.filter(is_active=True)
        total_comments_to_delete = 1 + replies_to_delete.count()
        
        # Soft delete the comment and all its replies
        instance.is_active = False
        instance.save()
        
        # Soft delete all replies
        replies_to_delete.update(is_active=False)
        
        # Update post comment count
        Post.objects.filter(pk=instance.post.pk).update(
            comments_count=F('comments_count') - total_comments_to_delete
        )
        
        # Update parent comment reply count (if this comment is a reply)
        if instance.parent:
            Comment.objects.filter(pk=instance.parent.pk).update(
                replies_count=F('replies_count') - 1
            )
        
        # If this comment has replies, reset its replies_count to 0
        if replies_to_delete.exists():
            Comment.objects.filter(pk=instance.pk).update(replies_count=0)
```

### Improved Signal Handling

**File**: `/feed/signals.py` - `update_comment_count_on_delete()`

Added better error handling and cascade detection for the hard deletion signal.

## 🔄 **How It Works Now**

### Scenario 1: Delete a Comment with Replies
```
Comment A (parent)
├── Reply A.1
├── Reply A.2
└── Reply A.3
```

**Before**: 
- Comment A: `is_active = False`, `replies_count = 3` ❌
- Replies: Still active ❌
- Post: `comments_count` decreased by 1 ❌

**After**: 
- Comment A: `is_active = False`, `replies_count = 0` ✅
- Reply A.1, A.2, A.3: `is_active = False` ✅
- Post: `comments_count` decreased by 4 ✅

### Scenario 2: Delete a Reply
```
Comment A (parent)
├── Reply A.1  ← Delete this
├── Reply A.2
└── Reply A.3
```

**Before**: 
- Reply A.1: `is_active = False` ✅
- Comment A: `replies_count` decreased by 1 ✅
- Post: `comments_count` decreased by 1 ✅

**After**: 
- Same behavior ✅ (no change needed for simple replies)

## 🎯 **Benefits**

1. **Accurate Counts**: Reply counts now reflect actual visible replies
2. **Cascading Deletion**: Deleting a parent comment properly handles all replies
3. **Data Consistency**: Post comment counts are accurate
4. **UI Consistency**: Frontend will show correct counts
5. **Database Integrity**: Atomic operations ensure consistency

## 🧪 **Testing**

### Test Scenario 1: Parent Comment with Replies
```bash
# 1. Create a comment with replies
curl -X POST http://localhost:8000/api/feed/posts/1/comments/ \
  -H "Authorization: Bearer TOKEN" \
  -d '{"content": "Parent comment"}'

curl -X POST http://localhost:8000/api/feed/posts/1/comments/ \
  -H "Authorization: Bearer TOKEN" \
  -d '{"content": "Reply 1", "parent": 1}'

curl -X POST http://localhost:8000/api/feed/posts/1/comments/ \
  -H "Authorization: Bearer TOKEN" \
  -d '{"content": "Reply 2", "parent": 1}'

# 2. Check counts before deletion
curl -X GET http://localhost:8000/api/feed/posts/1/ \
  -H "Authorization: Bearer TOKEN"
# Should show: comments_count = 3, parent comment replies_count = 2

# 3. Delete parent comment
curl -X DELETE http://localhost:8000/api/feed/comments/1/ \
  -H "Authorization: Bearer TOKEN"

# 4. Check counts after deletion
curl -X GET http://localhost:8000/api/feed/posts/1/ \
  -H "Authorization: Bearer TOKEN"
# Should show: comments_count = 0, no visible comments
```

### Test Scenario 2: Single Reply Deletion
```bash
# Delete only a reply, parent should remain with updated count
curl -X DELETE http://localhost:8000/api/feed/comments/2/ \
  -H "Authorization: Bearer TOKEN"

# Parent comment replies_count should decrease by 1
# Post comments_count should decrease by 1
```

## 🔧 **Technical Details**

- **Atomic Operations**: All count updates happen in a single transaction
- **Database-Level Updates**: Using `F('field_name')` for atomic count operations
- **Soft Deletion**: Maintains data integrity while hiding deleted content
- **Cascade Logic**: Properly handles nested comment structures
- **Error Handling**: Improved signal error handling for edge cases

## 📋 **Files Modified**

1. **`/feed/views.py`**: Updated `CommentDetailView.perform_destroy()`
2. **`/feed/signals.py`**: Improved `update_comment_count_on_delete()` signal

The fix ensures that comment deletion properly cascades to replies and maintains accurate counts throughout the system.
