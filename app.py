#!/usr/bin/env python3
"""
FastAPI Reddit API Wrapper

A FastAPI application that provides HTTP endpoints for Reddit API functionality.
Wraps the RedditClient to provide easy-to-use REST endpoints.

Endpoints:
- POST /get-user: Get user statistics by username
- POST /get-post: Get post statistics by URL
- POST /get-subreddit: Get subreddit information by name

Usage:
    uvicorn app:app --reload
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
import secrets
from dotenv import load_dotenv
from reddit_client import RedditClient, RedditAPIError

# Load environment variables from .env file
load_dotenv()

# FastAPI app instance
app = FastAPI(
    title="Reddit API Wrapper",
    description="A FastAPI wrapper for Reddit API functionality with API key authentication",
    version="1.0.0",
    docs_url=None,  # Disable default docs
    redoc_url=None  # Disable default redoc
)

# Security
security = HTTPBasic()  # For docs authentication
bearer_security = HTTPBearer()  # For API key authentication

# API Key configuration
API_KEY = os.getenv("API_KEY", "your-secret-api-key-here")  # Set via environment variable

# Basic Auth credentials for docs
DOCS_USERNAME = os.getenv("DOCS_USERNAME", "admin")
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "password")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request bodies
class RedditCredentials(BaseModel):
    client_id: str = Field(..., description="Reddit app client ID")
    client_secret: str = Field(..., description="Reddit app client secret")
    user_agent: str = Field(default="RedditAPIWrapper/1.0", description="User agent string")

class UserRequest(BaseModel):
    username: str = Field(..., description="Reddit username (without u/ prefix)")
    credentials: RedditCredentials

class PostRequest(BaseModel):
    post_url: str = Field(..., description="Reddit post URL")
    credentials: RedditCredentials

class SubredditRequest(BaseModel):
    subreddit_name: str = Field(..., description="Subreddit name (without r/ prefix)")
    credentials: RedditCredentials

class SubredditPostsRequest(BaseModel):
    subreddit_name: str = Field(..., description="Subreddit name (without r/ prefix)")
    sort: str = Field(default="new", description="Sort method (new, hot, top, rising, controversial, best)")
    limit: int = Field(default=25, ge=1, le=100, description="Number of posts to retrieve (1-100)")
    time_period: Optional[str] = Field(default=None, description="Time period for top/controversial (hour, day, week, month, year, all)")
    after: Optional[str] = Field(default=None, description="Get posts after this post ID (for pagination)")
    before: Optional[str] = Field(default=None, description="Get posts before this post ID (for pagination)")
    include_attractiveness_score: bool = Field(default=False, description="Whether to calculate attractiveness scores for posts")
    credentials: RedditCredentials

class PostCommentsRequest(BaseModel):
    post_url: str = Field(..., description="Reddit post URL")
    limit: Optional[int] = Field(default=None, description="Maximum number of comments to retrieve")
    sort: str = Field(default="best", description="Comment sort order (best, top, new, controversial, old, qa)")
    depth: Optional[int] = Field(default=None, description="Maximum depth of comment replies")
    credentials: RedditCredentials

class FormattedPostAnalysisRequest(BaseModel):
    post_url: str = Field(..., description="Reddit post URL")
    include_attractiveness: bool = Field(default=True, description="Whether to include attractiveness analysis")
    credentials: RedditCredentials

class FullSubredditPostsRequest(BaseModel):
    subreddit_name: str = Field(..., description="Subreddit name (without r/ prefix)")
    sort: str = Field(default="hot", description="Sort method (hot, new, top, rising, controversial, best)")
    time_period: Optional[str] = Field(default=None, description="Time period for top/controversial (hour, day, week, month, year, all)")
    limit: int = Field(default=25, description="Maximum number of posts to fetch")
    after: Optional[str] = Field(default=None, description="Get posts after this post ID (for pagination)")
    before: Optional[str] = Field(default=None, description="Get posts before this post ID (for pagination)")
    include_comments: bool = Field(default=True, description="Whether to fetch comments for each post")
    sort_by_attractiveness: bool = Field(default=True, description="Whether to sort results by attractiveness score")
    credentials: RedditCredentials

# Response models
class UserResponse(BaseModel):
    name: Optional[str]
    id: Optional[str]
    created_utc: Optional[float]
    link_karma: Optional[int]
    comment_karma: Optional[int]
    total_karma: Optional[int]
    awardee_karma: Optional[int]
    awarder_karma: Optional[int]
    is_gold: Optional[bool]
    is_mod: Optional[bool]
    has_verified_email: Optional[bool]
    icon_img: Optional[str]
    snoovatar_img: Optional[str]
    subreddit: Optional[Dict[str, Any]]
    accept_followers: Optional[bool]
    account_creation_date: Optional[float]

class PostResponse(BaseModel):
    id: Optional[str]
    title: Optional[str]
    author: Optional[str]
    subreddit: Optional[str]
    score: Optional[int]
    upvote_ratio: Optional[float]
    upvotes: Optional[int]
    downvotes: Optional[int]
    total_votes: Optional[int]
    num_comments: Optional[int]
    created_utc: Optional[float]
    url: Optional[str]
    permalink: Optional[str]
    is_self: Optional[bool]
    selftext: Optional[str]
    domain: Optional[str]
    locked: Optional[bool]
    stickied: Optional[bool]
    over_18: Optional[bool]
    gilded: Optional[int]
    total_awards_received: Optional[int]
    engagement_rate: Optional[float]

class SubredditResponse(BaseModel):
    name: Optional[str]
    id: Optional[str]
    title: Optional[str]
    public_description: Optional[str]
    description: Optional[str]
    subscribers: Optional[int]
    accounts_active: Optional[int]
    created_utc: Optional[float]
    over18: Optional[bool]
    lang: Optional[str]
    url: Optional[str]
    community_icon: Optional[str]
    banner_img: Optional[str]
    header_img: Optional[str]
    icon_img: Optional[str]
    submission_type: Optional[str]
    allow_images: Optional[bool]
    allow_videos: Optional[bool]
    wiki_enabled: Optional[bool]
    subreddit_type: Optional[str]
    user_is_subscriber: Optional[bool]
    quarantine: Optional[bool]

class PostInfo(BaseModel):
    id: Optional[str]
    title: Optional[str]
    author: Optional[str]
    subreddit: Optional[str]
    score: Optional[int]
    upvote_ratio: Optional[float]
    upvotes: Optional[int]
    downvotes: Optional[int]
    total_votes: Optional[int]
    num_comments: Optional[int]
    created_utc: Optional[float]
    url: Optional[str]
    permalink: Optional[str]
    is_self: Optional[bool]
    selftext: Optional[str]
    selftext_html: Optional[str]
    domain: Optional[str]
    locked: Optional[bool]
    stickied: Optional[bool]
    over_18: Optional[bool]
    gilded: Optional[int]
    total_awards_received: Optional[int]
    thumbnail: Optional[str]
    preview: Optional[Dict[str, Any]]
    media: Optional[Dict[str, Any]]
    is_video: Optional[bool]
    post_hint: Optional[str]
    engagement_rate: Optional[float]
    full_url: Optional[str]
    attractiveness_analysis: Optional[Dict[str, Any]] = None
    attractiveness_tier: Optional[Dict[str, Any]] = None

class PaginationInfo(BaseModel):
    after: Optional[str]
    before: Optional[str]
    count: int
    limit: int

class SubredditPostsResponse(BaseModel):
    subreddit: str
    sort_method: str
    time_period: Optional[str]
    posts: list[PostInfo]
    pagination: PaginationInfo
    total_posts_returned: int

class CommentInfo(BaseModel):
    id: Optional[str]
    author: Optional[str]
    body: Optional[str]
    body_html: Optional[str]
    score: Optional[int]
    upvote_ratio: Optional[float]
    upvotes: Optional[int]
    downvotes: Optional[int]
    total_votes: Optional[int]
    created_utc: Optional[float]
    edited: Optional[bool]
    gilded: Optional[int]
    total_awards_received: Optional[int]
    permalink: Optional[str]
    parent_id: Optional[str]
    link_id: Optional[str]
    subreddit: Optional[str]
    is_submitter: Optional[bool]
    stickied: Optional[bool]
    locked: Optional[bool]
    controversiality: Optional[int]
    depth: int
    replies_count: int
    replies: list['CommentInfo']
    full_url: Optional[str]

class PostBasicInfo(BaseModel):
    id: Optional[str]
    title: Optional[str]
    author: Optional[str]
    subreddit: Optional[str]
    score: Optional[int]
    num_comments: Optional[int]
    created_utc: Optional[float]
    url: Optional[str]
    permalink: Optional[str]
    full_url: Optional[str]

class CommentsParameters(BaseModel):
    limit: Optional[int]
    depth: Optional[int]
    sort: str

class PostCommentsResponse(BaseModel):
    post: PostBasicInfo
    comments: list[CommentInfo]
    total_comments_retrieved: int
    sort_order: str
    parameters: CommentsParameters

class FormattedPostAnalysisResponse(BaseModel):
    success: bool
    post_data: Optional[PostInfo] = None
    comments_data: Optional[list[CommentInfo]] = None
    attractiveness_analysis: Optional[Dict[str, Any]] = None
    formatted_post: Optional[str] = None
    basic_metrics: Optional[Dict[str, Any]] = None
    analysis_timestamp: Optional[float] = None
    error: Optional[str] = None

class FullPostAnalysis(BaseModel):
    post_data: PostInfo
    comments_data: Optional[list[CommentInfo]] = None
    attractiveness_analysis: Optional[Dict[str, Any]] = None
    formatted_post: str
    basic_metrics: Dict[str, Any]

class FullSubredditPostsResponse(BaseModel):
    success: bool
    subreddit: str
    sort_method: str
    time_period: Optional[str] = None
    total_posts_fetched: int
    posts_analyzed: list[FullPostAnalysis]
    summary_metrics: Dict[str, Any]
    analysis_timestamp: float
    error: Optional[str] = None

# Authentication dependency for API endpoints
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(bearer_security)):
    """
    Verify API key using Bearer Token Authentication
    
    The API key should be passed as a Bearer token in the Authorization header:
    Authorization: Bearer {api_key}
    """
    provided_key = credentials.credentials
    is_correct_key = secrets.compare_digest(provided_key, API_KEY)
    
    if not is_correct_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True

# Authentication dependency for docs endpoints
def verify_docs_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Verify username and password for documentation access
    
    Standard HTTP Basic Authentication with username and password:
    Authorization: Basic {base64(username:password)}
    """
    is_correct_username = secrets.compare_digest(credentials.username, DOCS_USERNAME)
    is_correct_password = secrets.compare_digest(credentials.password, DOCS_PASSWORD)
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid documentation credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

# Helper function to create Reddit client
def create_reddit_client(credentials: RedditCredentials) -> RedditClient:
    """Create and return a Reddit client instance"""
    return RedditClient(
        client_id=credentials.client_id,
        client_secret=credentials.client_secret,
        user_agent=credentials.user_agent
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Reddit API Wrapper",
        "version": "1.0.0",
        "authentication": {
            "type": "Bearer Token",
            "header": "Authorization: Bearer {api_key}",
            "note": "Standard Bearer token authentication for API endpoints"
        },
        "endpoints": {
            "get_user": "/get-user",
            "get_post": "/get-post", 
            "get_subreddit": "/get-subreddit",
            "get_subreddit_posts": "/get-subreddit-posts",
            "get_post_comments": "/get-post-comments",
            "get_formatted_post_analysis": "/get-formatted-post-analysis",
            "get_full_subreddit_posts": "/get-full-subreddit-posts"
        },
        "docs": "/docs"
    }

# Custom authenticated docs endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(authenticated: bool = Depends(verify_docs_credentials)):
    """
    Custom Swagger UI docs that require username/password authentication
    
    Requires Basic Authentication with username and password:
    Authorization: Basic {base64(username:password)}
    """
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html(authenticated: bool = Depends(verify_docs_credentials)):
    """
    Custom ReDoc documentation that requires username/password authentication
    
    Requires Basic Authentication with username and password:
    Authorization: Basic {base64(username:password)}
    """
    from fastapi.openapi.docs import get_redoc_html
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "reddit-api-wrapper"}

# User statistics endpoint
@app.post("/get-user", response_model=UserResponse)
async def get_user_statistics(request: UserRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Get detailed statistics for a Reddit user
    
    - **username**: Reddit username (without u/ prefix)
    - **credentials**: Reddit app credentials
    
    Requires API key authentication via Authorization header:
    Authorization: Bearer {api_key}
    """
    try:
        client = create_reddit_client(request.credentials)
        user_stats = client.get_user_statistics(request.username)
        return UserResponse(**user_stats)
    
    except RedditAPIError as e:
        raise HTTPException(status_code=400, detail=f"Reddit API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Post statistics endpoint
@app.post("/get-post", response_model=PostResponse)
async def get_post_statistics(request: PostRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Get detailed statistics for a Reddit post
    
    - **post_url**: Full Reddit post URL
    - **credentials**: Reddit app credentials
    
    Requires API key authentication via Authorization header:
    Authorization: Bearer {api_key}
    """
    try:
        client = create_reddit_client(request.credentials)
        post_stats = client.get_post_statistics(request.post_url)
        return PostResponse(**post_stats)
    
    except RedditAPIError as e:
        raise HTTPException(status_code=400, detail=f"Reddit API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Subreddit information endpoint
@app.post("/get-subreddit", response_model=SubredditResponse)
async def get_subreddit_info(request: SubredditRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Get detailed information about a subreddit
    
    - **subreddit_name**: Subreddit name (without r/ prefix)
    - **credentials**: Reddit app credentials
    
    Requires API key authentication via Authorization header:
    Authorization: Bearer {api_key}
    """
    try:
        client = create_reddit_client(request.credentials)
        subreddit_info = client.get_subreddit_info(request.subreddit_name)
        return SubredditResponse(**subreddit_info)
    
    except RedditAPIError as e:
        raise HTTPException(status_code=400, detail=f"Reddit API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Subreddit new posts endpoint
@app.post("/get-subreddit-posts", response_model=SubredditPostsResponse)
async def get_subreddit_new_posts(request: SubredditPostsRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Get posts from a subreddit with various sorting options
    
    - **subreddit_name**: Subreddit name (without r/ prefix)
    - **sort**: Sort method (new, hot, top, rising, controversial, best) - default: new
    - **limit**: Number of posts to retrieve (1-100, default 25)
    - **time_period**: Time period for top/controversial sorts (hour, day, week, month, year, all)
    - **after**: Get posts after this post ID (for pagination)
    - **before**: Get posts before this post ID (for pagination)
    - **include_attractiveness_score**: Whether to calculate attractiveness scores for posts (default false)
    - **credentials**: Reddit app credentials
    
    Requires API key authentication via Authorization header:
    Authorization: Bearer {api_key}
    """
    try:
        client = create_reddit_client(request.credentials)
        posts_data = client.get_subreddit_posts(
            subreddit_name=request.subreddit_name,
            sort=request.sort,
            limit=request.limit,
            time_period=request.time_period,
            after=request.after,
            before=request.before,
            include_attractiveness_score=request.include_attractiveness_score
        )
        return SubredditPostsResponse(**posts_data)
    
    except RedditAPIError as e:
        raise HTTPException(status_code=400, detail=f"Reddit API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Post comments endpoint
@app.post("/get-post-comments", response_model=PostCommentsResponse)
async def get_post_comments(request: PostCommentsRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Get all comments for a specific Reddit post
    
    - **post_url**: Full Reddit post URL
    - **limit**: Maximum number of comments to retrieve (optional)
    - **sort**: Comment sort order (best, top, new, controversial, old, qa)
    - **depth**: Maximum depth of comment replies (optional)
    - **credentials**: Reddit app credentials
    
    Requires API key authentication via Authorization header:
    Authorization: Bearer {api_key}
    """
    try:
        client = create_reddit_client(request.credentials)
        comments_data = client.get_post_comments(
            post_url=request.post_url,
            limit=request.limit,
            sort=request.sort,
            depth=request.depth
        )
        return PostCommentsResponse(**comments_data)
    
    except RedditAPIError as e:
        raise HTTPException(status_code=400, detail=f"Reddit API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "detail": "The requested endpoint does not exist"}
    )

# Full subreddit posts analysis endpoint
@app.post("/get-full-subreddit-posts", response_model=FullSubredditPostsResponse)
async def get_full_subreddit_posts(request: FullSubredditPostsRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Get comprehensive analysis of subreddit posts with attractiveness scoring and formatted output
    
    - **subreddit_name**: Subreddit name (without r/ prefix)
    - **sort**: Sort method (hot, new, top, rising, controversial, best)
    - **time_period**: Time period for top/controversial (hour, day, week, month, year, all)
    - **limit**: Maximum number of posts to fetch (default: 25)
    - **after**: Get posts after this post ID (for pagination)
    - **before**: Get posts before this post ID (for pagination)
    - **include_comments**: Whether to fetch comments for each post (default: true)
    - **sort_by_attractiveness**: Whether to sort results by attractiveness score (default: true)
    - **credentials**: Reddit app credentials
    
    Returns:
    - All posts with full analysis
    - Attractiveness scores and rankings
    - Formatted markdown for each post
    - Summary metrics for the subreddit
    
    Requires API key authentication via Authorization header:
    Authorization: Bearer {api_key}
    """
    try:
        # Create Reddit client
        client = RedditClient(
            client_id=request.credentials.client_id,
            client_secret=request.credentials.client_secret,
            user_agent=request.credentials.user_agent
        )
        
        # Get full subreddit analysis
        analysis_data = client.get_full_subreddit_posts(
            subreddit_name=request.subreddit_name,
            sort=request.sort,
            time_period=request.time_period,
            limit=request.limit,
            after=request.after,
            before=request.before,
            include_comments=request.include_comments,
            sort_by_attractiveness=request.sort_by_attractiveness
        )
        
        return FullSubredditPostsResponse(**analysis_data)
    
    except RedditAPIError as e:
        raise HTTPException(status_code=400, detail=f"Reddit API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Formatted post analysis endpoint
@app.post("/get-formatted-post-analysis", response_model=FormattedPostAnalysisResponse)
async def get_formatted_post_analysis(request: FormattedPostAnalysisRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Get a complete formatted analysis of a Reddit post including comments and attractiveness scoring
    
    - **post_url**: Full Reddit post URL
    - **include_attractiveness**: Whether to include attractiveness analysis (default: true)
    - **credentials**: Reddit app credentials
    
    Returns:
    - Full post details
    - All comments with nested replies
    - Attractiveness score and analysis (if enabled)
    - Human-readable markdown formatted output
    - Basic engagement metrics
    
    Requires API key authentication via Authorization header:
    Authorization: Bearer {api_key}
    """
    try:
        # Create Reddit client
        client = RedditClient(
            client_id=request.credentials.client_id,
            client_secret=request.credentials.client_secret,
            user_agent=request.credentials.user_agent
        )
        
        # Get formatted post analysis
        analysis_data = client.get_formatted_post_analysis(
            post_url=request.post_url,
            include_attractiveness=request.include_attractiveness
        )
        
        return FormattedPostAnalysisResponse(**analysis_data)
    
    except RedditAPIError as e:
        raise HTTPException(status_code=400, detail=f"Reddit API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.exception_handler(422)
async def validation_error_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Error", "detail": "Invalid request format or missing required fields"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
