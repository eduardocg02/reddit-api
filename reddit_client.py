#!/usr/bin/env python3
"""
Reddit API Client

A clean, modular Reddit API client for getting post statistics, user information,
and subreddit details. Designed to be used with FastAPI as a wrapper.

Usage:
    from reddit_client import RedditClient
    
    client = RedditClient(client_id, client_secret, user_agent)
    post_stats = client.get_post_statistics("https://www.reddit.com/r/python/comments/...")
    user_stats = client.get_user_statistics("username")
    subreddit_info = client.get_subreddit_info("python")
"""

import requests
import base64
import json
import re
from urllib.parse import urlencode, urlparse
from typing import Optional, Dict, Any

class RedditAPIError(Exception):
    """Custom exception for Reddit API errors"""
    pass

class RedditClient:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.access_token = None
        self.base_url = 'https://www.reddit.com'
        self.oauth_url = 'https://www.reddit.com/api/v1/access_token'
        
    def authenticate(self) -> bool:
        """Authenticate with Reddit API using client credentials flow"""
        # Prepare authentication data
        auth_data = {
            'grant_type': 'client_credentials'
        }
        
        # Create basic auth header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'User-Agent': self.user_agent,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(
                self.oauth_url,
                data=urlencode(auth_data),
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                return True
            else:
                raise RedditAPIError(f"Authentication failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise RedditAPIError(f"Network error during authentication: {e}")
        except json.JSONDecodeError as e:
            raise RedditAPIError(f"Invalid JSON response during authentication: {e}")
    
    def _make_authenticated_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Make an authenticated request to Reddit API"""
        if not self.access_token:
            # Try to authenticate first
            self.authenticate()
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'User-Agent': self.user_agent
        }
        
        url = f"https://oauth.reddit.com{endpoint}"
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 401:
                # Token might have expired, try re-authenticating
                self.authenticate()
                headers['Authorization'] = f'Bearer {self.access_token}'
                response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code not in [200, 201]:
                raise RedditAPIError(f"API request failed: {response.status_code} - {response.text}")
                
            return response
            
        except requests.exceptions.RequestException as e:
            raise RedditAPIError(f"Network error during API request: {e}")

    def _extract_post_id_from_url(self, post_url: str) -> str:
        """Extract post ID from Reddit URL"""
        # Handle various Reddit URL formats
        patterns = [
            r'/comments/([a-z0-9]+)/',  # Standard format
            r'/r/[^/]+/comments/([a-z0-9]+)',  # With subreddit
            r'reddit\.com/([a-z0-9]+)',  # Short format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, post_url)
            if match:
                return match.group(1)
        
        raise RedditAPIError(f"Could not extract post ID from URL: {post_url}")

    def get_post_statistics(self, post_url: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a Reddit post from its URL
        
        Args:
            post_url: Reddit post URL (e.g., "https://www.reddit.com/r/python/comments/abc123/title/")
            
        Returns:
            Dictionary containing post statistics including score, upvotes, downvotes, comments, etc.
        """
        try:
            post_id = self._extract_post_id_from_url(post_url)
            
            # First, try to get the post info from the URL structure
            # Extract subreddit from URL if possible
            subreddit_match = re.search(r'/r/([^/]+)/', post_url)
            if subreddit_match:
                subreddit = subreddit_match.group(1)
                endpoint = f"/r/{subreddit}/comments/{post_id}"
            else:
                # Fallback to search by post ID
                endpoint = f"/comments/{post_id}"
            
            response = self._make_authenticated_request(endpoint)
            data = response.json()
            
            # Reddit returns an array with post data and comments
            if isinstance(data, list) and len(data) > 0:
                post_data = data[0]['data']['children'][0]['data']
            else:
                raise RedditAPIError("Unexpected response format from Reddit API")
            
            return {
                'id': post_data.get('id'),
                'title': post_data.get('title'),
                'author': post_data.get('author'),
                'subreddit': post_data.get('subreddit'),
                'score': post_data.get('score'),
                'upvote_ratio': post_data.get('upvote_ratio'),
                'num_comments': post_data.get('num_comments'),
                'created_utc': post_data.get('created_utc'),
                'url': post_data.get('url'),
                'permalink': post_data.get('permalink'),
                'is_self': post_data.get('is_self'),
                'selftext': post_data.get('selftext'),
                'domain': post_data.get('domain'),
                'locked': post_data.get('locked'),
                'stickied': post_data.get('stickied'),
                'over_18': post_data.get('over_18'),
                'gilded': post_data.get('gilded'),
                'total_awards_received': post_data.get('total_awards_received'),
            }
            
        except Exception as e:
            if isinstance(e, RedditAPIError):
                raise
            raise RedditAPIError(f"Error getting post statistics: {str(e)}")

    def get_user_statistics(self, username: str) -> Dict[str, Any]:
        """
        Get detailed statistics and information for a Reddit user
        
        Args:
            username: Reddit username (without u/ prefix)
            
        Returns:
            Dictionary containing user statistics and information
        """
        try:
            # Clean username (remove u/ if present)
            username = username.replace('u/', '').replace('/u/', '')
            
            endpoint = f"/user/{username}/about"
            response = self._make_authenticated_request(endpoint)
            data = response.json()
            
            user_data = data.get('data', {})
            
            return {
                'name': user_data.get('name'),
                'id': user_data.get('id'),
                'created_utc': user_data.get('created_utc'),
                'link_karma': user_data.get('link_karma'),
                'comment_karma': user_data.get('comment_karma'),
                'total_karma': user_data.get('total_karma'),
                'awardee_karma': user_data.get('awardee_karma'),
                'awarder_karma': user_data.get('awarder_karma'),
                'is_gold': user_data.get('is_gold'),
                'is_mod': user_data.get('is_mod'),
                'has_verified_email': user_data.get('has_verified_email'),
                'icon_img': user_data.get('icon_img'),
                'snoovatar_img': user_data.get('snoovatar_img'),
                'subreddit': {
                    'subscribers': user_data.get('subreddit', {}).get('subscribers'),
                    'title': user_data.get('subreddit', {}).get('title'),
                    'public_description': user_data.get('subreddit', {}).get('public_description'),
                } if user_data.get('subreddit') else None,
                'accept_followers': user_data.get('accept_followers'),
                'account_creation_date': user_data.get('created_utc'),
            }
            
        except Exception as e:
            if isinstance(e, RedditAPIError):
                raise
            raise RedditAPIError(f"Error getting user statistics: {str(e)}")

    def get_subreddit_info(self, subreddit_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a subreddit
        
        Args:
            subreddit_name: Subreddit name (without r/ prefix)
            
        Returns:
            Dictionary containing subreddit information and statistics
        """
        try:
            # Clean subreddit name (remove r/ if present)
            subreddit_name = subreddit_name.replace('r/', '').replace('/r/', '')
            
            endpoint = f"/r/{subreddit_name}/about"
            response = self._make_authenticated_request(endpoint)
            data = response.json()
            
            subreddit_data = data.get('data', {})
            
            return {
                'name': subreddit_data.get('display_name'),
                'id': subreddit_data.get('id'),
                'title': subreddit_data.get('title'),
                'public_description': subreddit_data.get('public_description'),
                'description': subreddit_data.get('description'),
                'subscribers': subreddit_data.get('subscribers'),
                'accounts_active': subreddit_data.get('accounts_active'),
                'created_utc': subreddit_data.get('created_utc'),
                'over18': subreddit_data.get('over18'),
                'lang': subreddit_data.get('lang'),
                'url': subreddit_data.get('url'),
                'community_icon': subreddit_data.get('community_icon'),
                'banner_img': subreddit_data.get('banner_img'),
                'header_img': subreddit_data.get('header_img'),
                'icon_img': subreddit_data.get('icon_img'),
                'submission_type': subreddit_data.get('submission_type'),
                'allow_images': subreddit_data.get('allow_images'),
                'allow_videos': subreddit_data.get('allow_videos'),
                'wiki_enabled': subreddit_data.get('wiki_enabled'),
                'subreddit_type': subreddit_data.get('subreddit_type'),
                'user_is_subscriber': subreddit_data.get('user_is_subscriber'),
                'quarantine': subreddit_data.get('quarantine'),
            }
            
        except Exception as e:
            if isinstance(e, RedditAPIError):
                raise
            raise RedditAPIError(f"Error getting subreddit info: {str(e)}")
    
