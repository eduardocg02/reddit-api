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
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
import secrets
from reddit_client import RedditClient, RedditAPIError

# FastAPI app instance
app = FastAPI(
    title="Reddit API Wrapper",
    description="A FastAPI wrapper for Reddit API functionality with API key authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Security
security = HTTPBasic()

# API Key configuration
API_KEY = os.getenv("API_KEY", "your-secret-api-key-here")  # Set via environment variable

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

# Authentication dependency
def verify_api_key(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Verify API key using HTTP Basic Authentication
    
    The API key should be passed as the username in the Authorization header:
    Authorization: Basic {base64(api_key:)}
    
    Note: The password field is ignored, you can leave it empty or use any value
    """
    provided_key = credentials.username
    is_correct_key = secrets.compare_digest(provided_key, API_KEY)
    
    if not is_correct_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
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
            "type": "HTTP Basic",
            "header": "Authorization: Basic {base64(api_key:)}",
            "note": "API key goes in username field, password can be empty"
        },
        "endpoints": {
            "get_user": "/get-user",
            "get_post": "/get-post", 
            "get_subreddit": "/get-subreddit"
        },
        "docs": "/docs"
    }

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
    Authorization: Basic {base64(api_key:)}
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
    Authorization: Basic {base64(api_key:)}
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
    Authorization: Basic {base64(api_key:)}
    """
    try:
        client = create_reddit_client(request.credentials)
        subreddit_info = client.get_subreddit_info(request.subreddit_name)
        return SubredditResponse(**subreddit_info)
    
    except RedditAPIError as e:
        raise HTTPException(status_code=400, detail=f"Reddit API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Endpoint not found", "detail": "The requested endpoint does not exist"}

@app.exception_handler(422)
async def validation_error_handler(request, exc):
    return {"error": "Validation Error", "detail": "Invalid request format or missing required fields"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
