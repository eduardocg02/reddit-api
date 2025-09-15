# Reddit API FastAPI Wrapper

A FastAPI-based wrapper for the Reddit API that provides easy-to-use HTTP endpoints for getting user statistics, post information, and subreddit details.

## Features

- 🚀 **FastAPI** - Modern, fast web framework
- 📊 **Three Main Endpoints** - User stats, post stats, subreddit info
- 🔐 **Secure** - Credentials passed per request (no server-side storage)
- 📝 **Auto Documentation** - Interactive API docs at `/docs`
- ✅ **Error Handling** - Proper HTTP status codes and error messages

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the FastAPI server:
```bash
uvicorn app:app --reload
```

The server will start at `http://localhost:8000`

## API Endpoints

### 1. Get User Statistics
**POST** `/get-user`

Get detailed statistics for a Reddit user.

```json
{
  "username": "SnooCapers748",
  "credentials": {
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "user_agent": "YourApp/1.0"
  }
}
```

### 2. Get Post Statistics
**POST** `/get-post`

Get detailed information about a Reddit post.

```json
{
  "post_url": "https://www.reddit.com/r/agency/comments/1mq1mn3/title/",
  "credentials": {
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "user_agent": "YourApp/1.0"
  }
}
```

### 3. Get Subreddit Information
**POST** `/get-subreddit`

Get detailed information about a subreddit.

```json
{
  "subreddit_name": "agency",
  "credentials": {
    "client_id": "your_client_id",
    "client_secret": "your_client_secret", 
    "user_agent": "YourApp/1.0"
  }
}
```

## Testing

1. Start the server:
```bash
uvicorn app:app --reload
```

2. Run the test script:
```bash
python test_api.py
```

3. Or visit the interactive docs:
```
http://localhost:8000/docs
```

## Reddit App Setup

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Choose "script" as the app type
4. Fill in required fields
5. Use the generated `client_id` and `client_secret`

## File Structure

```
├── app.py              # FastAPI application
├── reddit_client.py    # Reddit API client class
├── test_api.py         # API endpoint tests
├── test_user_example.py # Direct client tests
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Example Response

### User Statistics Response:
```json
{
  "name": "SnooCapers748",
  "link_karma": 1234,
  "comment_karma": 5678,
  "total_karma": 6912,
  "is_gold": false,
  "created_utc": 1640995200.0
}
```

### Post Statistics Response:
```json
{
  "title": "What Systems / Tools have dramatically improved your business?",
  "author": "SnooCapers748",
  "score": 29,
  "num_comments": 58,
  "upvote_ratio": 0.95,
  "subreddit": "agency"
}
```

### Subreddit Information Response:
```json
{
  "name": "agency",
  "title": "r/agency",
  "subscribers": 63762,
  "accounts_active": 13,
  "subreddit_type": "public",
  "allow_images": true
}
```

## Development

- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
