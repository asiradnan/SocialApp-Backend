# Instructor Rating API Reference

## Overview
Users can rate instructors on a scale of 1-5 stars. Each user can only have one rating per instructor, but they can update their rating at any time.

---

## Endpoints

### 1. Get Instructor Rating

**Endpoint:** `GET /api/users/instructors/{instructor_id}/rating/`

**Description:** Get the average rating, total number of ratings, and the current user's rating (if authenticated) for a specific instructor.

**Authentication:** Optional (user_rating only available if authenticated)

**Response (200 OK):**
```json
{
  "instructor_id": 5,
  "average_rating": 4.5,
  "total_ratings": 23,
  "user_rating": 5
}
```

**Response Fields:**
- `instructor_id` (int): The ID of the instructor
- `average_rating` (float): Average rating (0.0-5.0, rounded to 1 decimal place)
- `total_ratings` (int): Total number of ratings received
- `user_rating` (int|null): Current user's rating (1-5) or null if not rated yet

**Error Responses:**

**400 Bad Request** - User is not an instructor:
```json
{
  "error": "User is not an instructor"
}
```

**404 Not Found** - Instructor not found:
```json
{
  "error": "Instructor not found"
}
```

---

### 2. Submit or Update Rating

**Endpoint:** `POST /api/users/instructors/rating/`

**Description:** Submit a new rating or update an existing rating for an instructor.

**Authentication:** Required (JWT)

**Request Body:**
```json
{
  "instructor_id": 5,
  "rating": 4
}
```

**Request Fields:**
- `instructor_id` (int, required): The ID of the instructor to rate
- `rating` (int, required): Rating value (1-5)

**Response (201 Created)** - New rating:
```json
{
  "message": "Rating submitted successfully",
  "rating": 4
}
```

**Response (200 OK)** - Updated rating:
```json
{
  "message": "Rating updated successfully",
  "rating": 5
}
```

**Error Responses:**

**400 Bad Request** - Invalid rating value:
```json
{
  "rating": ["Rating must be between 1 and 5"]
}
```

**400 Bad Request** - User is not an instructor:
```json
{
  "instructor_id": ["This user is not an instructor"]
}
```

**400 Bad Request** - Trying to rate yourself:
```json
{
  "error": "You cannot rate yourself"
}
```

**404 Not Found** - Instructor not found:
```json
{
  "instructor_id": ["Instructor not found"]
}
```

**401 Unauthorized** - Not authenticated:
```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

## Usage Examples

### Get Instructor Rating (Unauthenticated)

```bash
curl -X GET http://localhost:8000/api/users/instructors/5/rating/
```

**Response:**
```json
{
  "instructor_id": 5,
  "average_rating": 4.3,
  "total_ratings": 18,
  "user_rating": null
}
```

---

### Get Instructor Rating (Authenticated)

```bash
curl -X GET http://localhost:8000/api/users/instructors/5/rating/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "instructor_id": 5,
  "average_rating": 4.3,
  "total_ratings": 18,
  "user_rating": 4
}
```

---

### Submit a New Rating

```bash
curl -X POST http://localhost:8000/api/users/instructors/rating/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instructor_id": 5,
    "rating": 5
  }'
```

**Response:**
```json
{
  "message": "Rating submitted successfully",
  "rating": 5
}
```

---

### Update an Existing Rating

```bash
curl -X POST http://localhost:8000/api/users/instructors/rating/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instructor_id": 5,
    "rating": 4
  }'
```

**Response:**
```json
{
  "message": "Rating updated successfully",
  "rating": 4
}
```

---

## Android Integration Example

### Get Instructor Rating

```kotlin
// Retrofit interface
@GET("api/users/instructors/{instructorId}/rating/")
suspend fun getInstructorRating(
    @Path("instructorId") instructorId: Int,
    @Header("Authorization") token: String? = null
): Response<InstructorRatingResponse>

// Data class
data class InstructorRatingResponse(
    val instructor_id: Int,
    val average_rating: Float,
    val total_ratings: Int,
    val user_rating: Int?
)

// Usage
lifecycleScope.launch {
    try {
        val token = "Bearer $jwtToken"
        val response = apiService.getInstructorRating(instructorId, token)
        
        if (response.isSuccessful) {
            val rating = response.body()
            // Display rating
            binding.averageRating.text = rating?.average_rating.toString()
            binding.totalRatings.text = "(${rating?.total_ratings} ratings)"
            
            // Update user's rating stars if available
            rating?.user_rating?.let { userRating ->
                binding.ratingBar.rating = userRating.toFloat()
            }
        }
    } catch (e: Exception) {
        Log.e("Rating", "Error fetching rating", e)
    }
}
```

### Submit Rating

```kotlin
// Retrofit interface
@POST("api/users/instructors/rating/")
suspend fun submitRating(
    @Header("Authorization") token: String,
    @Body request: SubmitRatingRequest
): Response<SubmitRatingResponse>

// Data classes
data class SubmitRatingRequest(
    val instructor_id: Int,
    val rating: Int
)

data class SubmitRatingResponse(
    val message: String,
    val rating: Int
)

// Usage
binding.ratingBar.setOnRatingBarChangeListener { _, rating, fromUser ->
    if (fromUser) {
        lifecycleScope.launch {
            try {
                val token = "Bearer $jwtToken"
                val request = SubmitRatingRequest(instructorId, rating.toInt())
                val response = apiService.submitRating(token, request)
                
                if (response.isSuccessful) {
                    Toast.makeText(
                        this@Activity,
                        response.body()?.message,
                        Toast.LENGTH_SHORT
                    ).show()
                    
                    // Refresh rating display
                    loadInstructorRating()
                } else {
                    Toast.makeText(
                        this@Activity,
                        "Failed to submit rating",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            } catch (e: Exception) {
                Log.e("Rating", "Error submitting rating", e)
            }
        }
    }
}
```

---

## Database Schema

### Rating Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key (auto-increment) |
| `user` | ForeignKey | User who gave the rating |
| `instructor` | ForeignKey | Instructor being rated |
| `rating` | Integer | Rating value (1-5) |
| `created_at` | DateTime | When rating was first created |
| `updated_at` | DateTime | When rating was last updated |

**Constraints:**
- `unique_together`: (user, instructor) - One rating per user per instructor
- `validators`: Rating must be between 1 and 5

**Indexes:**
- `instructor` - For fast lookup of all ratings for an instructor
- `user` - For fast lookup of all ratings by a user

---

## Business Logic

### Rules:
1. ✅ Users can only rate instructors (user_type='instructor')
2. ✅ Users cannot rate themselves
3. ✅ Each user can only have one rating per instructor
4. ✅ Ratings can be updated (POST to same endpoint)
5. ✅ Rating values must be 1-5 (inclusive)
6. ✅ Average rating is calculated from all ratings
7. ✅ Unauthenticated users can view ratings but not their own rating

### Validation:
- Rating value: 1-5 (integer)
- Instructor must exist and have user_type='instructor'
- User cannot rate themselves
- Authentication required for submitting ratings

---

## Testing

### Test Scenarios:

1. **Get rating for instructor with no ratings:**
   - Expected: average_rating=0.0, total_ratings=0, user_rating=null

2. **Get rating as unauthenticated user:**
   - Expected: Shows average and count, user_rating=null

3. **Submit first rating:**
   - Expected: 201 Created, "Rating submitted successfully"

4. **Update existing rating:**
   - Expected: 200 OK, "Rating updated successfully"

5. **Try to rate yourself:**
   - Expected: 400 Bad Request, "You cannot rate yourself"

6. **Try to rate non-instructor:**
   - Expected: 400 Bad Request, "This user is not an instructor"

7. **Submit invalid rating (0 or 6):**
   - Expected: 400 Bad Request, validation error

---

## Admin Panel

Ratings can be managed in Django admin at `/admin/users/rating/`:

**List View:**
- User email
- Instructor email
- Rating (1-5)
- Created date
- Updated date

**Filters:**
- By rating value
- By created date
- By updated date

**Search:**
- User email, name
- Instructor email, name

---

## Performance Considerations

### Database Queries:
- `get_instructor_rating`: 2 queries (aggregate + optional user rating lookup)
- `submit_rating`: 1 query (update_or_create)

### Optimizations:
- Indexed on `instructor` field for fast aggregation
- Indexed on `user` field for fast user rating lookup
- `select_related` used in admin for efficient queries

### Caching Recommendations (Optional):
```python
# Cache average rating for 5 minutes
from django.core.cache import cache

cache_key = f'instructor_{instructor_id}_rating'
cached_data = cache.get(cache_key)

if not cached_data:
    # Calculate rating
    cache.set(cache_key, data, 300)  # 5 minutes
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success (GET, updated rating) |
| 201 | Created (new rating) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (no auth token) |
| 404 | Not Found (instructor doesn't exist) |

---

## Notes

- Ratings are soft-referenced to instructors - if instructor is deleted, ratings are also deleted (CASCADE)
- Rating updates preserve the original `created_at` timestamp
- Average rating is calculated on-the-fly (no denormalization)
- Round average to 1 decimal place for display

---

## Future Enhancements (Optional)

- [ ] Add rating comments/reviews
- [ ] Add ability to delete rating
- [ ] Add pagination for instructor ratings list
- [ ] Add filtering by rating value
- [ ] Add rating distribution (how many 1-star, 2-star, etc.)
- [ ] Add date range filtering for ratings
- [ ] Cache average ratings for better performance
- [ ] Add email notification to instructor when rated

---

*Last Updated: November 14, 2025*
