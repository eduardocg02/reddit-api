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
import time
from urllib.parse import urlencode, urlparse
from typing import Optional, Dict, Any
try:
    from helper import calculate_post_attractiveness_score, get_attractiveness_tier, format_post
except ImportError:
    # Fallback if helper module is not available
    def calculate_post_attractiveness_score(post_data, comments_data=None, include_time_factor=True):
        return {'attractiveness_score': 0, 'score_breakdown': {}, 'engagement_metrics': {}, 'scoring_weights': {}}
    def get_attractiveness_tier(score):
        return {'tier': 'Unknown', 'tier_level': 0, 'description': 'Attractiveness scoring unavailable'}

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
            
            # Calculate upvotes and downvotes from score and upvote_ratio
            score = post_data.get('score', 0)
            upvote_ratio = post_data.get('upvote_ratio', 0.5)
            
            # Calculate total votes and separate upvotes/downvotes
            # Formula: score = upvotes - downvotes, upvote_ratio = upvotes / (upvotes + downvotes)
            if upvote_ratio > 0 and upvote_ratio < 1:
                total_votes = round(score / (2 * upvote_ratio - 1)) if (2 * upvote_ratio - 1) != 0 else 0
                upvotes = round(total_votes * upvote_ratio)
                downvotes = total_votes - upvotes
            else:
                # Handle edge cases
                upvotes = max(0, score) if upvote_ratio >= 0.5 else 0
                downvotes = max(0, -score) if upvote_ratio < 0.5 else 0
                total_votes = upvotes + downvotes
            
            return {
                'id': post_data.get('id'),
                'title': post_data.get('title'),
                'author': post_data.get('author'),
                'subreddit': post_data.get('subreddit'),
                'score': score,
                'upvote_ratio': upvote_ratio,
                'upvotes': upvotes,
                'downvotes': downvotes,
                'total_votes': total_votes,
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
                # Engagement metrics
                'engagement_rate': round((post_data.get('num_comments', 0) / max(total_votes, 1)) * 100, 2) if total_votes > 0 else 0,
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

    def get_subreddit_posts(self, subreddit_name: str, sort: str = "new", limit: int = 25, time_period: Optional[str] = None, after: Optional[str] = None, before: Optional[str] = None, include_attractiveness_score: bool = False) -> Dict[str, Any]:
        """
        Get posts from a subreddit with various sorting options
        
        Args:
            subreddit_name: Subreddit name (without r/ prefix)
            sort: Sort method ("new", "hot", "top", "rising", "controversial", "best")
            limit: Number of posts to retrieve (1-100, default 25)
            time_period: Time period for "top" and "controversial" sorts ("hour", "day", "week", "month", "year", "all")
            after: Get posts after this post ID (for pagination)
            before: Get posts before this post ID (for pagination)
            include_attractiveness_score: Whether to calculate attractiveness scores for posts
            
        Returns:
            Dictionary containing list of posts and pagination info
        """
        try:
            # Clean subreddit name (remove r/ if present)
            subreddit_name = subreddit_name.replace('r/', '').replace('/r/', '')
            
            # Validate limit
            limit = max(1, min(100, limit))
            
            # Validate sort method
            valid_sorts = ["new", "hot", "top", "rising", "controversial", "best"]
            if sort not in valid_sorts:
                raise RedditAPIError(f"Invalid sort method '{sort}'. Valid options: {', '.join(valid_sorts)}")
            
            # Build endpoint based on sort method
            endpoint = f"/r/{subreddit_name}/{sort}"
            
            # Build parameters
            params = {'limit': limit}
            if after:
                params['after'] = after
            if before:
                params['before'] = before
            
            # Add time period for top and controversial sorts
            if sort in ["top", "controversial"] and time_period:
                valid_periods = ["hour", "day", "week", "month", "year", "all"]
                if time_period not in valid_periods:
                    raise RedditAPIError(f"Invalid time period '{time_period}'. Valid options: {', '.join(valid_periods)}")
                params['t'] = time_period
            
            response = self._make_authenticated_request(endpoint, params)
            data = response.json()
            
            # Extract posts data
            posts_data = data.get('data', {})
            children = posts_data.get('children', [])
            
            posts = []
            for child in children:
                post_data = child.get('data', {})
                
                # Calculate upvotes and downvotes from score and upvote_ratio
                score = post_data.get('score', 0)
                upvote_ratio = post_data.get('upvote_ratio', 0.5)
                
                # Calculate total votes and separate upvotes/downvotes
                if upvote_ratio > 0 and upvote_ratio < 1:
                    total_votes = round(score / (2 * upvote_ratio - 1)) if (2 * upvote_ratio - 1) != 0 else 0
                    upvotes = round(total_votes * upvote_ratio)
                    downvotes = total_votes - upvotes
                else:
                    # Handle edge cases
                    upvotes = max(0, score) if upvote_ratio >= 0.5 else 0
                    downvotes = max(0, -score) if upvote_ratio < 0.5 else 0
                    total_votes = upvotes + downvotes
                
                post_info = {
                    'id': post_data.get('id'),
                    'title': post_data.get('title'),
                    'author': post_data.get('author'),
                    'subreddit': post_data.get('subreddit'),
                    'score': score,
                    'upvote_ratio': upvote_ratio,
                    'upvotes': upvotes,
                    'downvotes': downvotes,
                    'total_votes': total_votes,
                    'num_comments': post_data.get('num_comments'),
                    'created_utc': post_data.get('created_utc'),
                    'url': post_data.get('url'),
                    'permalink': post_data.get('permalink'),
                    'is_self': post_data.get('is_self'),
                    'selftext': post_data.get('selftext'),
                    'selftext_html': post_data.get('selftext_html'),
                    'domain': post_data.get('domain'),
                    'locked': post_data.get('locked'),
                    'stickied': post_data.get('stickied'),
                    'over_18': post_data.get('over_18'),
                    'gilded': post_data.get('gilded'),
                    'total_awards_received': post_data.get('total_awards_received'),
                    'thumbnail': post_data.get('thumbnail'),
                    'preview': post_data.get('preview'),
                    'media': post_data.get('media'),
                    'is_video': post_data.get('is_video'),
                    'post_hint': post_data.get('post_hint'),
                    # Engagement metrics
                    'engagement_rate': round((post_data.get('num_comments', 0) / max(total_votes, 1)) * 100, 2) if total_votes > 0 else 0,
                    # Full Reddit URL
                    'full_url': f"https://www.reddit.com{post_data.get('permalink', '')}" if post_data.get('permalink') else None,
                }
                
                # Add attractiveness score if requested
                if include_attractiveness_score:
                    try:
                        attractiveness_data = calculate_post_attractiveness_score(post_info)
                        tier_data = get_attractiveness_tier(attractiveness_data['attractiveness_score'])
                        post_info['attractiveness_analysis'] = attractiveness_data
                        post_info['attractiveness_tier'] = tier_data
                    except Exception as e:
                        # Add error info for debugging
                        post_info['attractiveness_analysis'] = {'error': str(e)}
                        post_info['attractiveness_tier'] = {'error': str(e)}
                posts.append(post_info)
            
            return {
                'subreddit': subreddit_name,
                'sort_method': sort,
                'time_period': time_period,
                'posts': posts,
                'pagination': {
                    'after': posts_data.get('after'),
                    'before': posts_data.get('before'),
                    'count': len(posts),
                    'limit': limit
                },
                'total_posts_returned': len(posts)
            }
            
        except Exception as e:
            if isinstance(e, RedditAPIError):
                raise
            raise RedditAPIError(f"Error getting subreddit posts: {str(e)}")

    def get_subreddit_new_posts(self, subreddit_name: str, limit: int = 25, after: Optional[str] = None, before: Optional[str] = None, include_attractiveness_score: bool = False) -> Dict[str, Any]:
        """
        Get new posts from a subreddit (backwards compatibility method)
        
        This method is kept for backwards compatibility. Use get_subreddit_posts() for more options.
        """
        return self.get_subreddit_posts(
            subreddit_name=subreddit_name,
            sort="new",
            limit=limit,
            after=after,
            before=before,
            include_attractiveness_score=include_attractiveness_score
        )

    def get_post_comments(self, post_url: str, limit: Optional[int] = None, sort: str = "best", depth: Optional[int] = None) -> Dict[str, Any]:
        """
        Get all comments for a specific Reddit post
        
        Args:
            post_url: Reddit post URL (e.g., "https://www.reddit.com/r/python/comments/abc123/title/")
            limit: Maximum number of comments to retrieve (default: no limit)
            sort: Comment sort order ("best", "top", "new", "controversial", "old", "qa")
            depth: Maximum depth of comment replies to retrieve (default: all levels)
            
        Returns:
            Dictionary containing post info and all comments with replies
        """
        try:
            post_id = self._extract_post_id_from_url(post_url)
            
            # Extract subreddit from URL if possible
            subreddit_match = re.search(r'/r/([^/]+)/', post_url)
            if subreddit_match:
                subreddit = subreddit_match.group(1)
                endpoint = f"/r/{subreddit}/comments/{post_id}"
            else:
                # Fallback to search by post ID
                endpoint = f"/comments/{post_id}"
            
            # Build parameters
            params = {'sort': sort}
            # When limit is None, we want ALL comments, so set a very high limit
            if limit is None:
                params['limit'] = 1000  # Reddit's practical maximum
            elif limit is not None:
                params['limit'] = limit
            if depth is not None:
                params['depth'] = depth
            
            response = self._make_authenticated_request(endpoint, params)
            data = response.json()
            
            # Reddit returns an array: [post_data, comments_data]
            if not isinstance(data, list) or len(data) < 2:
                raise RedditAPIError("Unexpected response format from Reddit API")
            
            post_data = data[0]['data']['children'][0]['data']
            comments_data = data[1]['data']['children']
            
            def process_comment(comment_data: Dict[str, Any], level: int = 0) -> Dict[str, Any]:
                """Recursively process comment and its replies"""
                if comment_data.get('kind') != 't1':  # t1 is comment type
                    return None
                
                comment = comment_data.get('data', {})
                
                # Skip deleted/removed comments
                if comment.get('author') in ['[deleted]', '[removed]']:
                    return None
                
                # Calculate upvotes and downvotes from score and upvote_ratio
                score = comment.get('score', 0)
                upvote_ratio = comment.get('upvote_ratio')
                
                if upvote_ratio and upvote_ratio > 0 and upvote_ratio < 1:
                    total_votes = round(score / (2 * upvote_ratio - 1)) if (2 * upvote_ratio - 1) != 0 else 0
                    upvotes = round(total_votes * upvote_ratio)
                    downvotes = total_votes - upvotes
                else:
                    # For comments, upvote_ratio might not be available
                    upvotes = max(0, score) if score >= 0 else 0
                    downvotes = max(0, -score) if score < 0 else 0
                    total_votes = upvotes + downvotes
                
                # Process replies
                replies = []
                replies_data = comment.get('replies')
                if replies_data and isinstance(replies_data, dict):
                    replies_children = replies_data.get('data', {}).get('children', [])
                    for reply_data in replies_children:
                        processed_reply = process_comment(reply_data, level + 1)
                        if processed_reply:
                            replies.append(processed_reply)
                
                return {
                    'id': comment.get('id'),
                    'author': comment.get('author'),
                    'body': comment.get('body'),
                    'body_html': comment.get('body_html'),
                    'score': score,
                    'upvote_ratio': upvote_ratio,
                    'upvotes': upvotes,
                    'downvotes': downvotes,
                    'total_votes': total_votes,
                    'created_utc': comment.get('created_utc'),
                    'edited': comment.get('edited'),
                    'gilded': comment.get('gilded'),
                    'total_awards_received': comment.get('total_awards_received'),
                    'permalink': comment.get('permalink'),
                    'parent_id': comment.get('parent_id'),
                    'link_id': comment.get('link_id'),
                    'subreddit': comment.get('subreddit'),
                    'is_submitter': comment.get('is_submitter'),
                    'stickied': comment.get('stickied'),
                    'locked': comment.get('locked'),
                    'controversiality': comment.get('controversiality'),
                    'depth': level,
                    'replies_count': len(replies),
                    'replies': replies,
                    'full_url': f"https://www.reddit.com{comment.get('permalink', '')}" if comment.get('permalink') else None,
                }
            
            # Process all top-level comments
            comments = []
            for comment_data in comments_data:
                processed_comment = process_comment(comment_data)
                if processed_comment:
                    comments.append(processed_comment)
            
            # Get post basic info
            post_info = {
                'id': post_data.get('id'),
                'title': post_data.get('title'),
                'author': post_data.get('author'),
                'subreddit': post_data.get('subreddit'),
                'score': post_data.get('score'),
                'num_comments': post_data.get('num_comments'),
                'created_utc': post_data.get('created_utc'),
                'url': post_data.get('url'),
                'permalink': post_data.get('permalink'),
                'full_url': f"https://www.reddit.com{post_data.get('permalink', '')}" if post_data.get('permalink') else None,
            }
            
            def count_total_comments(comments_list):
                """Recursively count all comments including replies"""
                total = len(comments_list)
                for comment in comments_list:
                    total += count_total_comments(comment.get('replies', []))
                return total
            
            return {
                'post': post_info,
                'comments': comments,
                'total_comments_retrieved': count_total_comments(comments),
                'sort_order': sort,
                'parameters': {
                    'limit': limit,
                    'depth': depth,
                    'sort': sort
                }
            }
            
        except Exception as e:
            if isinstance(e, RedditAPIError):
                raise
            raise RedditAPIError(f"Error getting post comments: {str(e)}")
    
    def get_formatted_post_analysis(self, post_url: str, include_attractiveness: bool = True) -> Dict[str, Any]:
        """
        Get a complete formatted analysis of a Reddit post including comments and attractiveness scoring
        
        Args:
            post_url: Reddit post URL
            include_attractiveness: Whether to include attractiveness analysis
            
        Returns:
            Dictionary containing post data, comments, attractiveness analysis, and formatted markdown
        """
        try:
            # Get post comments using existing method (no limit to get ALL comments)
            print(f"  Fetching comments for: {post_url}")
            post_comments_data = self.get_post_comments(post_url, limit=None, depth=None)
            
            if not post_comments_data or 'post' not in post_comments_data:
                print(f"  ERROR: Failed to fetch post data for {post_url}")
                print(f"  Response: {post_comments_data}")
                raise RedditAPIError("Failed to fetch post data")
            
            post_data = post_comments_data['post']
            comments_data = post_comments_data.get('comments', [])
            
            # Calculate attractiveness analysis if requested
            attractiveness_analysis = None
            if include_attractiveness:
                try:
                    attractiveness_analysis = calculate_post_attractiveness_score(
                        post_data, 
                        comments_data, 
                        include_time_factor=True
                    )
                    # Add tier information
                    tier_info = get_attractiveness_tier(attractiveness_analysis['attractiveness_score'])
                    attractiveness_analysis['tier'] = tier_info
                except Exception as e:
                    print(f"Warning: Could not calculate attractiveness score: {e}")
                    attractiveness_analysis = None
            
            # Generate formatted markdown
            try:
                formatted_post = format_post(post_data, comments_data, attractiveness_analysis)
            except Exception as e:
                print(f"Warning: Could not format post: {e}")
                formatted_post = "Error generating formatted output"
            
            # Calculate basic metrics
            total_comments = len(comments_data)
            total_comment_score = sum(comment.get('score', 0) for comment in self._flatten_comments(comments_data))
            
            return {
                'success': True,
                'post_data': post_data,
                'comments_data': comments_data,
                'attractiveness_analysis': attractiveness_analysis,
                'formatted_post': formatted_post,
                'basic_metrics': {
                    'total_comments': total_comments,
                    'total_comment_score': total_comment_score,
                    'post_score': post_data.get('score', 0),
                    'engagement_rate': post_data.get('upvote_ratio', 0),
                    'has_media': bool(post_data.get('url', '').lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')))
                },
                'analysis_timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'post_data': None,
                'comments_data': [],
                'attractiveness_analysis': None,
                'formatted_post': None,
                'basic_metrics': {},
                'analysis_timestamp': time.time()
            }
    
    def _flatten_comments(self, comments: list) -> list:
        """Flatten nested comments structure for metrics calculation"""
        flattened = []
        for comment in comments:
            flattened.append(comment)
            if comment.get('replies'):
                flattened.extend(self._flatten_comments(comment['replies']))
        return flattened
    
    def get_full_subreddit_posts(self, subreddit_name: str, sort: str = "hot", 
                                time_period: Optional[str] = None, limit: int = 25,
                                after: Optional[str] = None, before: Optional[str] = None,
                                include_comments: bool = True, sort_by_attractiveness: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive analysis of subreddit posts with attractiveness scoring and formatted output
        
        Args:
            subreddit_name: Name of the subreddit (without r/ prefix)
            sort: Sort method (hot, new, top, rising, controversial, best)
            time_period: Time period for top/controversial sorts
            limit: Maximum number of posts to fetch
            after: Pagination - get posts after this ID
            before: Pagination - get posts before this ID
            include_comments: Whether to fetch comments for each post
            sort_by_attractiveness: Whether to sort results by attractiveness score
            
        Returns:
            Dictionary containing comprehensive analysis of all posts
        """
        try:
            # First, get the list of posts from the subreddit
            posts_response = self.get_subreddit_posts(
                subreddit_name=subreddit_name,
                sort=sort,
                time_period=time_period,
                limit=limit,
                after=after,
                before=before,
                include_attractiveness_score=True
            )
            
            if not posts_response or 'posts' not in posts_response:
                raise RedditAPIError("Failed to fetch subreddit posts")
            
            posts = posts_response['posts']
            analyzed_posts = []
            
            print(f"Analyzing {len(posts)} posts from r/{subreddit_name}...")
            
            # Analyze each post individually
            for i, post in enumerate(posts, 1):
                try:
                    print(f"Processing post {i}/{len(posts)}: {post.get('title', 'No title')[:50]}...")
                    
                    # Get post URL for detailed analysis
                    post_url = f"https://www.reddit.com{post.get('permalink', '')}"
                    
                    if include_comments:
                        # Get full analysis including comments
                        analysis = self.get_formatted_post_analysis(post_url, include_attractiveness=True)
                        
                        if analysis['success']:
                            # Debug: Check if comments were actually fetched
                            comments_count = len(analysis['comments_data']) if analysis['comments_data'] else 0
                            expected_comments = post.get('num_comments', 0)
                            print(f"  Comments fetched: {comments_count}, Expected: {expected_comments}")
                            
                            # Create simplified post data for response
                            simplified_post_data = {
                                'title': analysis['post_data'].get('title', ''),
                                'author': analysis['post_data'].get('author', ''),
                                'score': analysis['post_data'].get('score', 0),
                                'upvote_ratio': analysis['post_data'].get('upvote_ratio', 0),
                                'num_comments': analysis['post_data'].get('num_comments', 0),
                                'created_utc': analysis['post_data'].get('created_utc', 0),
                                'url': analysis['post_data'].get('url', ''),
                                'permalink': analysis['post_data'].get('permalink', ''),
                                'selftext': analysis['post_data'].get('selftext', ''),
                                'is_video': analysis['post_data'].get('is_video', False),
                                'media': analysis['post_data'].get('media'),
                                'preview': analysis['post_data'].get('preview')
                            }
                            
                            analyzed_posts.append({
                                'post_data': simplified_post_data,
                                'attractiveness_analysis': analysis['attractiveness_analysis'],
                                'basic_metrics': analysis['basic_metrics'],
                                'formatted_post': analysis['formatted_post']
                            })
                        else:
                            print(f"Warning: Failed to analyze post {i}: {analysis.get('error', 'Unknown error')}")
                            # Still add the post but without full analysis
                            # Create simplified post data for response
                            simplified_post_data = {
                                'title': post.get('title', ''),
                                'author': post.get('author', ''),
                                'score': post.get('score', 0),
                                'upvote_ratio': post.get('upvote_ratio', 0),
                                'num_comments': post.get('num_comments', 0),
                                'created_utc': post.get('created_utc', 0),
                                'url': post.get('url', ''),
                                'permalink': post.get('permalink', ''),
                                'selftext': post.get('selftext', ''),
                                'is_video': post.get('is_video', False),
                                'media': post.get('media'),
                                'preview': post.get('preview')
                            }
                            
                            analyzed_posts.append({
                                'post_data': simplified_post_data,
                                'attractiveness_analysis': None,
                                'formatted_post': f"Error analyzing post: {analysis.get('error', 'Unknown error')}",
                                'basic_metrics': {
                                    'total_comments': post.get('num_comments', 0),
                                    'total_comment_score': 0,
                                    'post_score': post.get('score', 0),
                                    'engagement_rate': post.get('upvote_ratio', 0),
                                    'has_media': bool(post.get('url', '').lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')))
                                }
                            })
                    else:
                        # Just get post data with attractiveness scoring
                        attractiveness_analysis = None
                        try:
                            attractiveness_analysis = calculate_post_attractiveness_score(
                                post, [], include_time_factor=True
                            )
                            tier_info = get_attractiveness_tier(attractiveness_analysis['attractiveness_score'])
                            attractiveness_analysis['tier'] = tier_info
                        except Exception as e:
                            print(f"Warning: Could not calculate attractiveness for post {i}: {e}")
                        
                        # Generate formatted output without comments
                        formatted_post = format_post(post, [], attractiveness_analysis)
                        
                        # Create simplified post data for response
                        simplified_post_data = {
                            'title': post.get('title', ''),
                            'author': post.get('author', ''),
                            'score': post.get('score', 0),
                            'upvote_ratio': post.get('upvote_ratio', 0),
                            'num_comments': post.get('num_comments', 0),
                            'created_utc': post.get('created_utc', 0),
                            'url': post.get('url', ''),
                            'permalink': post.get('permalink', ''),
                            'selftext': post.get('selftext', ''),
                            'is_video': post.get('is_video', False),
                            'media': post.get('media'),
                            'preview': post.get('preview')
                        }
                        
                        analyzed_posts.append({
                            'post_data': simplified_post_data,
                            'attractiveness_analysis': attractiveness_analysis,
                            'formatted_post': formatted_post,
                            'basic_metrics': {
                                'total_comments': post.get('num_comments', 0),
                                'total_comment_score': 0,
                                'post_score': post.get('score', 0),
                                'engagement_rate': post.get('upvote_ratio', 0),
                                'has_media': bool(post.get('url', '').lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')))
                            }
                        })
                        
                except Exception as e:
                    print(f"Error processing post {i}: {e}")
                    continue
            
            # Sort by attractiveness score if requested
            if sort_by_attractiveness and analyzed_posts:
                analyzed_posts.sort(
                    key=lambda x: x['attractiveness_analysis']['attractiveness_score'] if x['attractiveness_analysis'] else 0,
                    reverse=True
                )
            
            # Calculate summary metrics
            total_posts = len(analyzed_posts)
            attractiveness_scores = [
                p['attractiveness_analysis']['attractiveness_score'] 
                for p in analyzed_posts 
                if p['attractiveness_analysis']
            ]
            
            summary_metrics = {
                'total_posts_analyzed': total_posts,
                'average_attractiveness_score': sum(attractiveness_scores) / len(attractiveness_scores) if attractiveness_scores else 0,
                'max_attractiveness_score': max(attractiveness_scores) if attractiveness_scores else 0,
                'min_attractiveness_score': min(attractiveness_scores) if attractiveness_scores else 0,
                'total_post_score': sum(p['basic_metrics']['post_score'] for p in analyzed_posts),
                'average_post_score': sum(p['basic_metrics']['post_score'] for p in analyzed_posts) / total_posts if total_posts > 0 else 0,
                'total_comments': sum(p['basic_metrics']['total_comments'] for p in analyzed_posts),
                'average_comments_per_post': sum(p['basic_metrics']['total_comments'] for p in analyzed_posts) / total_posts if total_posts > 0 else 0,
                'posts_with_media': sum(1 for p in analyzed_posts if p['basic_metrics']['has_media']),
                'media_percentage': (sum(1 for p in analyzed_posts if p['basic_metrics']['has_media']) / total_posts * 100) if total_posts > 0 else 0
            }
            
            return {
                'success': True,
                'subreddit': subreddit_name,
                'sort_method': sort,
                'time_period': time_period,
                'total_posts_fetched': total_posts,
                'posts_analyzed': analyzed_posts,
                'summary_metrics': summary_metrics,
                'analysis_timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'success': False,
                'subreddit': subreddit_name,
                'sort_method': sort,
                'time_period': time_period,
                'total_posts_fetched': 0,
                'posts_analyzed': [],
                'summary_metrics': {},
                'analysis_timestamp': time.time(),
                'error': str(e)
            }
    
