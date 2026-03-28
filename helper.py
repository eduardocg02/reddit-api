#!/usr/bin/env python3
"""
Reddit Post Analysis Helper Functions

Contains utility functions for calculating post attractiveness scores
and other analytical metrics for Reddit posts and comments.
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import re
import html

def calculate_comment_metrics(comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Recursively calculate metrics from comments and their replies
    
    Args:
        comments: List of comment dictionaries with potential nested replies
        
    Returns:
        Dictionary containing aggregated comment metrics
    """
    total_comment_score = 0
    total_comment_length = 0
    total_comments_count = 0
    max_depth = 0
    unique_authors = set()
    
    def process_comment_recursive(comment: Dict[str, Any], current_depth: int = 0):
        nonlocal total_comment_score, total_comment_length, total_comments_count, max_depth, unique_authors
        
        # Update counters
        total_comments_count += 1
        total_comment_score += comment.get('score', 0)
        
        # Add comment body length
        body = comment.get('body', '')
        if body:
            total_comment_length += len(body)
        
        # Track unique authors
        author = comment.get('author')
        if author and author not in ['[deleted]', '[removed]']:
            unique_authors.add(author)
        
        # Track max depth
        max_depth = max(max_depth, current_depth)
        
        # Process replies recursively
        replies = comment.get('replies', [])
        for reply in replies:
            process_comment_recursive(reply, current_depth + 1)
    
    # Process all top-level comments
    for comment in comments:
        process_comment_recursive(comment)
    
    return {
        'total_comment_score': total_comment_score,
        'total_comment_length': total_comment_length,
        'total_comments_count': total_comments_count,
        'max_comment_depth': max_depth,
        'unique_commenters': len(unique_authors)
    }

def calculate_post_attractiveness_score(
    post_data: Dict[str, Any], 
    comments_data: Optional[List[Dict[str, Any]]] = None,
    include_time_factor: bool = True
) -> Dict[str, Any]:
    """
    Calculate a post's attractiveness score based on engagement metrics
    
    Args:
        post_data: Dictionary containing post information
        comments_data: Optional list of comments for more detailed analysis
        include_time_factor: Whether to include time-based velocity calculations
        
    Returns:
        Dictionary containing the attractiveness score and component breakdown
    """
    
    # Extract basic post metrics
    num_comments = post_data.get('num_comments', 0)
    total_votes = post_data.get('total_votes', 0)
    awards = post_data.get('total_awards_received', 0)
    post_score = post_data.get('score', 0)
    
    # Initialize comment metrics
    comment_metrics = {
        'total_comment_score': 0,
        'total_comment_length': 0,
        'total_comments_count': 0,
        'max_comment_depth': 0,
        'unique_commenters': 0
    }
    
    # If we have detailed comments data, calculate enhanced metrics
    if comments_data:
        comment_metrics = calculate_comment_metrics(comments_data)
        # Use actual comment count if available
        num_comments = max(num_comments, comment_metrics['total_comments_count'])
    
    # Core attractiveness formula components
    comment_score = num_comments * 5
    votes_score = total_votes * 2
    awards_score = awards * 20
    comment_upvotes_score = comment_metrics['total_comment_score'] * 1
    length_bonus = min(comment_metrics['total_comment_length'] / 100, 50)  # Cap at 50 points
    
    # Time velocity factor (if enabled and we have creation time)
    time_velocity_bonus = 0
    if include_time_factor and post_data.get('created_utc'):
        post_age_hours = (time.time() - post_data['created_utc']) / 3600
        if post_age_hours > 0:
            # Engagement per hour, with diminishing returns for very old posts
            total_engagement = num_comments + total_votes + (awards * 5)
            velocity = total_engagement / max(post_age_hours, 0.1)
            time_velocity_bonus = min(velocity * 2, 100)  # Cap at 100 points
    
    # Calculate final score
    attractiveness_score = (
        comment_score + 
        votes_score + 
        awards_score + 
        comment_upvotes_score + 
        length_bonus + 
        time_velocity_bonus
    )
    
    return {
        'attractiveness_score': round(attractiveness_score, 2),
        'score_breakdown': {
            'comments_contribution': comment_score,
            'votes_contribution': votes_score,
            'awards_contribution': awards_score,
            'comment_upvotes_contribution': comment_upvotes_score,
            'length_bonus': round(length_bonus, 2),
            'time_velocity_bonus': round(time_velocity_bonus, 2)
        },
        'engagement_metrics': {
            'total_comments': num_comments,
            'total_votes': total_votes,
            'total_awards': awards,
            'post_score': post_score,
            **comment_metrics
        },
        'scoring_weights': {
            'comments_multiplier': 5,
            'votes_multiplier': 2,
            'awards_multiplier': 20,
            'comment_upvotes_multiplier': 1,
            'length_divisor': 100,
            'time_velocity_multiplier': 2
        }
    }

def rank_posts_by_attractiveness(
    posts_with_comments: List[Dict[str, Any]], 
    include_time_factor: bool = True
) -> List[Dict[str, Any]]:
    """
    Rank a list of posts by their attractiveness scores
    
    Args:
        posts_with_comments: List of dictionaries containing post_info and comments_data
        include_time_factor: Whether to include time-based velocity in scoring
        
    Returns:
        List of posts sorted by attractiveness score (highest first)
    """
    
    ranked_posts = []
    
    for post_data in posts_with_comments:
        post_info = post_data.get('post_info', {})
        comments_data = post_data.get('comments_data', {}).get('comments', [])
        
        # Calculate attractiveness score
        score_data = calculate_post_attractiveness_score(
            post_info, 
            comments_data, 
            include_time_factor
        )
        
        # Add score data to post
        enhanced_post = {
            **post_data,
            'attractiveness_analysis': score_data
        }
        
        ranked_posts.append(enhanced_post)
    
    # Sort by attractiveness score (highest first)
    ranked_posts.sort(
        key=lambda x: x['attractiveness_analysis']['attractiveness_score'], 
        reverse=True
    )
    
    return ranked_posts

def get_attractiveness_tier(score: float) -> Dict[str, Any]:
    """
    Categorize a post's attractiveness score into tiers
    
    Args:
        score: The attractiveness score
        
    Returns:
        Dictionary with tier information
    """
    
    if score >= 500:
        return {
            'tier': 'Viral',
            'tier_level': 5,
            'description': 'Highly viral/controversial content with massive engagement'
        }
    elif score >= 200:
        return {
            'tier': 'High Viral Potential',
            'tier_level': 4,
            'description': 'Strong engagement indicating viral potential'
        }
    elif score >= 50:
        return {
            'tier': 'High Engagement',
            'tier_level': 3,
            'description': 'Above average engagement with good discussion'
        }
    elif score >= 10:
        return {
            'tier': 'Moderate Engagement',
            'tier_level': 2,
            'description': 'Moderate community interest and interaction'
        }
    else:
        return {
            'tier': 'Low Engagement',
            'tier_level': 1,
            'description': 'Limited community engagement'
        }

# Example usage and testing functions
def analyze_sample_post():
    """Example function showing how to use the attractiveness calculator"""
    
    sample_post = {
        'num_comments': 25,
        'total_votes': 150,
        'total_awards_received': 2,
        'score': 120,
        'created_utc': time.time() - 3600  # 1 hour ago
    }
    
    sample_comments = [
        {'score': 15, 'body': 'This is a great post with lots of detail!', 'replies': []},
        {'score': 8, 'body': 'I disagree but interesting perspective', 'replies': [
            {'score': 3, 'body': 'Can you explain why?', 'replies': []}
        ]},
        {'score': -2, 'body': 'This is wrong', 'replies': []}
    ]
    
    result = calculate_post_attractiveness_score(sample_post, sample_comments)
    tier = get_attractiveness_tier(result['attractiveness_score'])
    
    print("Sample Post Analysis:")
    print(f"Attractiveness Score: {result['attractiveness_score']}")
    print(f"Tier: {tier['tier']} (Level {tier['tier_level']})")
    print(f"Description: {tier['description']}")
    print("\nScore Breakdown:")
    for component, value in result['score_breakdown'].items():
        print(f"  {component}: {value}")

def calculate_thread_engagement(comment: Dict[str, Any]) -> int:
    """
    Calculate total upvotes/engagement for a comment thread (including all replies)
    
    Args:
        comment: Root comment of the thread
        
    Returns:
        Total score/upvotes for the entire thread
    """
    total_score = comment.get('score', 0)
    
    # Add scores from all replies recursively
    replies = comment.get('replies', [])
    for reply in replies:
        total_score += calculate_thread_engagement(reply)
    
    return total_score

def get_top_comment_threads(comments_data: List[Dict[str, Any]], max_threads: int = 10) -> List[Dict[str, Any]]:
    """
    Get the top comment threads sorted by total engagement (upvotes)
    
    Args:
        comments_data: List of root-level comments
        max_threads: Maximum number of threads to return
        
    Returns:
        List of top comment threads sorted by engagement
    """
    if not comments_data:
        return []
    
    # Calculate engagement for each thread and sort
    threads_with_engagement = []
    for comment in comments_data:
        engagement = calculate_thread_engagement(comment)
        threads_with_engagement.append({
            'comment': comment,
            'total_engagement': engagement
        })
    
    # Sort by engagement (highest first) and take top N
    threads_with_engagement.sort(key=lambda x: x['total_engagement'], reverse=True)
    top_threads = threads_with_engagement[:max_threads]
    
    return [thread['comment'] for thread in top_threads]

def format_post(post_data: Dict[str, Any], comments_data: List[Dict[str, Any]], 
                attractiveness_analysis: Optional[Dict[str, Any]] = None) -> str:
    """
    Format a Reddit post and its comments into a human-readable markdown format
    
    Args:
        post_data: Dictionary containing post information
        comments_data: List of comments with nested replies
        attractiveness_analysis: Optional attractiveness score analysis
        
    Returns:
        Formatted markdown string representation of the post and comments
    """
    
    def format_timestamp(timestamp: Optional[float]) -> str:
        """Convert UTC timestamp to readable format"""
        if not timestamp:
            return "Unknown time"
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "Invalid timestamp"
    
    def format_number(num: Optional[int]) -> str:
        """Format numbers with commas for readability"""
        if num is None:
            return "0"
        return f"{num:,}"
    
    def clean_text(text: str) -> str:
        """Clean and format text content"""
        if not text:
            return "[No content]"
        
        # Decode HTML entities (like &lt; &gt; &amp; etc.)
        text = html.unescape(text)
        
        # Remove excessive whitespace and normalize line breaks
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
        text = text.strip()
        
        # NO TRUNCATION - return full text always
            
        return text
    
    def extract_image_urls(post_data: Dict[str, Any]) -> List[str]:
        """Extract image URLs from post data"""
        urls = []
        
        # Check various image fields
        if post_data.get('url') and any(ext in post_data['url'].lower() 
                                       for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            urls.append(post_data['url'])
        
        # Check media metadata
        media = post_data.get('media', {})
        if media and isinstance(media, dict):
            # Reddit video preview
            if 'reddit_video' in media:
                preview_url = media['reddit_video'].get('fallback_url')
                if preview_url:
                    urls.append(preview_url)
        
        # Check preview images
        preview = post_data.get('preview', {})
        if preview and 'images' in preview:
            for image in preview['images']:
                if 'source' in image and 'url' in image['source']:
                    urls.append(image['source']['url'])
        
        return urls
    
    def format_comment_thread(comment: Dict[str, Any], depth: int = 0) -> str:
        """Recursively format a comment and its replies with proper indentation"""
        
        # Create indentation based on depth
        indent = "    " * depth  # 4 spaces per level
        arrow = "└─> " if depth > 0 else "• "
        
        # Extract comment data
        author = comment.get('author', '[deleted]')
        body = clean_text(comment.get('body', ''))
        score = comment.get('score', 0)
        created = format_timestamp(comment.get('created_utc'))
        
        # Check if this is the original poster
        op_marker = ""
        if author == post_data.get('author', ''):
            op_marker = " **[OP]** 🎯"
        
        # Format the comment
        comment_text = f"{indent}{arrow}**{author}**{op_marker} ({score:+d} points) • {created}\n"
        comment_text += f"{indent}  {body}\n"
        
        # Add replies recursively
        replies = comment.get('replies', [])
        if replies:
            comment_text += "\n"
            for reply in replies:
                comment_text += format_comment_thread(reply, depth + 1)
                comment_text += "\n"
        
        return comment_text
    
    def count_all_comments(comments: List[Dict[str, Any]]) -> int:
        """Recursively count all comments including nested replies"""
        total = 0
        for comment in comments:
            total += 1  # Count this comment
            replies = comment.get('replies', [])
            if replies:
                total += count_all_comments(replies)  # Count all replies recursively
        return total
    
    # Start building the formatted output
    output = []
    
    # Header
    output.append("# 📝 Reddit Post Analysis")
    output.append("=" * 50)
    output.append("")
    
    # Post Details Section
    output.append("## 📋 Post Details")
    output.append("")
    
    # Title
    title = post_data.get('title', 'No Title')
    output.append(f"**Title:** {title}")
    output.append("")
    
    # Author and basic info
    author = post_data.get('author', '[deleted]')
    subreddit = post_data.get('subreddit', 'unknown')
    created = format_timestamp(post_data.get('created_utc'))
    
    output.append(f"**Author:** u/{author}")
    output.append(f"**Subreddit:** r/{subreddit}")
    output.append(f"**Posted:** {created}")
    output.append("")
    
    # Engagement metrics
    score = post_data.get('score', 0)
    upvote_ratio = post_data.get('upvote_ratio', 0)
    num_comments = post_data.get('num_comments', 0)
    
    output.append("### 📊 Engagement Metrics")
    output.append(f"- **Score:** {score:+d} points")
    output.append(f"- **Upvote Ratio:** {upvote_ratio:.1%}")
    output.append(f"- **Comments:** {format_number(num_comments)}")
    
    # Additional metrics if available
    if post_data.get('total_awards_received'):
        output.append(f"- **Awards:** {format_number(post_data['total_awards_received'])}")
    
    output.append("")
    
    # Content Section
    output.append("## 📄 Post Content")
    output.append("")
    
    # Post text content
    selftext = post_data.get('selftext', '')
    if selftext:
        output.append("### Text Content")
        output.append("```")
        output.append(clean_text(selftext))
        output.append("```")
        output.append("")
    
    # Image URLs
    image_urls = extract_image_urls(post_data)
    if image_urls:
        output.append("### 🖼️ Media Content")
        for i, url in enumerate(image_urls, 1):
            output.append(f"{i}. {url}")
        output.append("")
    
    # External URL
    url = post_data.get('url', '')
    if url and not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
        output.append(f"**Link:** {url}")
        output.append("")
    
    # Attractiveness Analysis Section
    if attractiveness_analysis:
        output.append("## 🎯 Attractiveness Analysis")
        output.append("")
        
        score = attractiveness_analysis.get('attractiveness_score', 0)
        output.append(f"**Attractiveness Score:** {score:.2f}")
        
        # Score breakdown
        breakdown = attractiveness_analysis.get('score_breakdown', {})
        if breakdown:
            output.append("")
            output.append("### Score Breakdown")
            for component, value in breakdown.items():
                component_name = component.replace('_', ' ').title()
                output.append(f"- **{component_name}:** {value}")
        
        output.append("")
    
    # Comments Section - Show Top 10 Most Engaging Threads
    output.append("## 💬 Top Comment Threads")
    output.append("")
    
    if not comments_data:
        output.append("*No comments available*")
    else:
        # Get top comment threads by engagement
        top_threads = get_top_comment_threads(comments_data, max_threads=10)
        total_comments = count_all_comments(comments_data)
        
        output.append(f"**Total Comments:** {total_comments:,} (including all replies)")
        output.append(f"**Top-level Comments:** {len(comments_data)}")
        output.append(f"**Showing Top {len(top_threads)} Most Engaging Threads**")
        output.append("")
        
        # Format each top thread with engagement score
        for i, comment in enumerate(top_threads, 1):
            thread_engagement = calculate_thread_engagement(comment)
            output.append(f"### Thread #{i} (Total Engagement: {thread_engagement:+d} points)")
            output.append("")
            output.append(format_comment_thread(comment))
            
            # Add separator between threads (except for the last one)
            if i < len(top_threads):
                output.append("---")
                output.append("")
    
    # No footer - clean end
    output.append("")
    
    return "\n".join(output)

def analyze_user_posting_patterns(posts: List[Dict[str, Any]], comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze user's posting patterns including frequency, timing, and content types
    
    Args:
        posts: List of user's posts
        comments: List of user's comments
        
    Returns:
        Dictionary containing posting pattern analysis
    """
    from datetime import datetime, timedelta
    import collections
    
    if not posts and not comments:
        return {'error': 'No data to analyze'}
    
    # Collect all timestamps
    all_activity = []
    for post in posts:
        if post.get('created_utc'):
            all_activity.append({
                'timestamp': post['created_utc'],
                'type': 'post',
                'subreddit': post.get('subreddit'),
                'score': post.get('score', 0)
            })
    
    for comment in comments:
        if comment.get('created_utc'):
            all_activity.append({
                'timestamp': comment['created_utc'],
                'type': 'comment',
                'subreddit': comment.get('subreddit'),
                'score': comment.get('score', 0)
            })
    
    if not all_activity:
        return {'error': 'No timestamps available'}
    
    # Sort by timestamp
    all_activity.sort(key=lambda x: x['timestamp'])
    
    # Analyze posting frequency
    timestamps = [activity['timestamp'] for activity in all_activity]
    time_diffs = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
    avg_time_between_posts = sum(time_diffs) / len(time_diffs) if time_diffs else 0
    
    # Analyze activity by hour of day
    hours = [datetime.fromtimestamp(ts).hour for ts in timestamps]
    hour_distribution = collections.Counter(hours)
    peak_hour = hour_distribution.most_common(1)[0][0] if hour_distribution else 0
    
    # Analyze activity by day of week
    weekdays = [datetime.fromtimestamp(ts).weekday() for ts in timestamps]
    weekday_distribution = collections.Counter(weekdays)
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    peak_weekday = weekday_names[weekday_distribution.most_common(1)[0][0]] if weekday_distribution else 'Unknown'
    
    # Content type analysis for posts
    content_types = {
        'text_posts': sum(1 for p in posts if p.get('is_self')),
        'link_posts': sum(1 for p in posts if not p.get('is_self')),
        'video_posts': sum(1 for p in posts if p.get('is_video')),
        'image_posts': sum(1 for p in posts if p.get('post_hint') == 'image'),
        'nsfw_posts': sum(1 for p in posts if p.get('over_18'))
    }
    
    # Activity timeline (last 30 days)
    now = time.time()
    thirty_days_ago = now - (30 * 24 * 3600)
    recent_activity = [a for a in all_activity if a['timestamp'] > thirty_days_ago]
    
    return {
        'total_posts': len(posts),
        'total_comments': len(comments),
        'total_activity': len(all_activity),
        'frequency_metrics': {
            'average_time_between_activities_hours': avg_time_between_posts / 3600 if avg_time_between_posts else 0,
            'activities_per_day': len(all_activity) / max((timestamps[-1] - timestamps[0]) / 86400, 1) if len(timestamps) > 1 else 0
        },
        'temporal_patterns': {
            'peak_activity_hour': peak_hour,
            'peak_weekday': peak_weekday,
            'hour_distribution': dict(hour_distribution),
            'weekday_distribution': {weekday_names[k]: v for k, v in weekday_distribution.items()}
        },
        'content_type_distribution': content_types,
        'recent_activity_30_days': len(recent_activity),
        'activity_timeline': {
            'oldest_activity': datetime.fromtimestamp(timestamps[0]).isoformat() if timestamps else None,
            'newest_activity': datetime.fromtimestamp(timestamps[-1]).isoformat() if timestamps else None,
            'total_timespan_days': (timestamps[-1] - timestamps[0]) / 86400 if len(timestamps) > 1 else 0
        }
    }

def calculate_user_engagement_metrics(posts: List[Dict[str, Any]], comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate comprehensive engagement metrics for a user
    
    Args:
        posts: List of user's posts
        comments: List of user's comments
        
    Returns:
        Dictionary containing engagement metrics
    """
    if not posts and not comments:
        return {'error': 'No data to analyze'}
    
    # Post metrics
    post_scores = [p.get('score', 0) for p in posts]
    post_comments = [p.get('num_comments', 0) for p in posts]
    post_upvote_ratios = [p.get('upvote_ratio', 0) for p in posts if p.get('upvote_ratio')]
    
    # Comment metrics
    comment_scores = [c.get('score', 0) for c in comments]
    gilded_posts = sum(1 for p in posts if p.get('gilded', 0) > 0)
    gilded_comments = sum(1 for c in comments if c.get('gilded', 0) > 0)
    
    # Awards
    total_post_awards = sum(p.get('total_awards_received', 0) for p in posts)
    total_comment_awards = sum(c.get('total_awards_received', 0) for c in comments)
    
    # Controversial content
    controversial_comments = sum(1 for c in comments if c.get('controversiality', 0) > 0)
    
    # Calculate percentiles for scores
    def calculate_percentiles(scores):
        if not scores:
            return {'p25': 0, 'p50': 0, 'p75': 0, 'p90': 0}
        sorted_scores = sorted(scores)
        n = len(sorted_scores)
        return {
            'p25': sorted_scores[int(n * 0.25)] if n > 0 else 0,
            'p50': sorted_scores[int(n * 0.50)] if n > 0 else 0,
            'p75': sorted_scores[int(n * 0.75)] if n > 0 else 0,
            'p90': sorted_scores[int(n * 0.90)] if n > 0 else 0
        }
    
    return {
        'post_engagement': {
            'total_posts': len(posts),
            'average_score': sum(post_scores) / len(post_scores) if post_scores else 0,
            'median_score': sorted(post_scores)[len(post_scores)//2] if post_scores else 0,
            'max_score': max(post_scores) if post_scores else 0,
            'min_score': min(post_scores) if post_scores else 0,
            'total_karma_from_posts': sum(post_scores),
            'average_comments_per_post': sum(post_comments) / len(post_comments) if post_comments else 0,
            'average_upvote_ratio': sum(post_upvote_ratios) / len(post_upvote_ratios) if post_upvote_ratios else 0,
            'score_percentiles': calculate_percentiles(post_scores)
        },
        'comment_engagement': {
            'total_comments': len(comments),
            'average_score': sum(comment_scores) / len(comment_scores) if comment_scores else 0,
            'median_score': sorted(comment_scores)[len(comment_scores)//2] if comment_scores else 0,
            'max_score': max(comment_scores) if comment_scores else 0,
            'min_score': min(comment_scores) if comment_scores else 0,
            'total_karma_from_comments': sum(comment_scores),
            'controversial_comments': controversial_comments,
            'controversial_percentage': (controversial_comments / len(comments) * 100) if comments else 0,
            'score_percentiles': calculate_percentiles(comment_scores)
        },
        'awards_and_recognition': {
            'total_post_awards': total_post_awards,
            'total_comment_awards': total_comment_awards,
            'total_awards': total_post_awards + total_comment_awards,
            'gilded_posts': gilded_posts,
            'gilded_comments': gilded_comments,
            'total_gilded_content': gilded_posts + gilded_comments
        },
        'overall_metrics': {
            'total_karma': sum(post_scores) + sum(comment_scores),
            'karma_ratio_posts_to_comments': sum(post_scores) / max(sum(comment_scores), 1) if comment_scores else float('inf'),
            'engagement_rate': (len(posts) + len(comments)) / max(len(posts) + len(comments), 1) * 100,
            'content_diversity': len(set(p.get('subreddit') for p in posts if p.get('subreddit'))) + 
                               len(set(c.get('subreddit') for c in comments if c.get('subreddit')))
        }
    }

def analyze_content_topics(posts: List[Dict[str, Any]], comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze content topics and themes from user's posts and comments
    
    Args:
        posts: List of user's posts
        comments: List of user's comments
        
    Returns:
        Dictionary containing content analysis
    """
    import re
    from collections import Counter
    
    if not posts and not comments:
        return {'error': 'No data to analyze'}
    
    # Collect all text content
    all_text = []
    
    # Extract text from posts
    for post in posts:
        title = post.get('title', '')
        selftext = post.get('selftext', '')
        if title:
            all_text.append(title)
        if selftext:
            all_text.append(selftext)
    
    # Extract text from comments
    for comment in comments:
        body = comment.get('body', '')
        if body and body not in ['[deleted]', '[removed]']:
            all_text.append(body)
    
    if not all_text:
        return {'error': 'No text content to analyze'}
    
    # Combine all text
    combined_text = ' '.join(all_text).lower()
    
    # Basic text analysis
    total_words = len(combined_text.split())
    total_chars = len(combined_text)
    
    # Extract common words (simple approach)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', combined_text)
    word_freq = Counter(words)
    
    # Remove common stop words
    stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'she', 'use', 'her', 'now', 'him', 'time', 'will', 'about', 'after', 'again', 'back', 'other', 'many', 'than', 'then', 'them', 'these', 'some', 'would', 'like', 'into', 'only', 'think', 'know', 'take', 'people', 'year', 'your', 'good', 'just', 'first', 'well', 'work'}
    filtered_words = {word: count for word, count in word_freq.items() if word not in stop_words and len(word) > 3}
    
    # Subreddit distribution
    subreddit_posts = Counter(p.get('subreddit') for p in posts if p.get('subreddit'))
    subreddit_comments = Counter(c.get('subreddit') for c in comments if c.get('subreddit'))
    
    # Combine subreddit activity
    all_subreddits = subreddit_posts + subreddit_comments
    
    # Content type analysis
    text_lengths = [len(text) for text in all_text]
    
    return {
        'text_analysis': {
            'total_words': total_words,
            'total_characters': total_chars,
            'average_text_length': sum(text_lengths) / len(text_lengths) if text_lengths else 0,
            'longest_text': max(text_lengths) if text_lengths else 0,
            'shortest_text': min(text_lengths) if text_lengths else 0
        },
        'vocabulary': {
            'unique_words': len(word_freq),
            'most_common_words': dict(Counter(filtered_words).most_common(20)),
            'vocabulary_diversity': len(word_freq) / max(total_words, 1)
        },
        'subreddit_distribution': {
            'total_unique_subreddits': len(all_subreddits),
            'most_active_subreddits': dict(all_subreddits.most_common(15)),
            'subreddit_diversity': len(all_subreddits) / max(len(posts) + len(comments), 1)
        },
        'content_patterns': {
            'posts_with_text': sum(1 for p in posts if p.get('selftext')),
            'posts_with_links': sum(1 for p in posts if not p.get('is_self')),
            'average_title_length': sum(len(p.get('title', '')) for p in posts) / max(len(posts), 1),
            'average_comment_length': sum(len(c.get('body', '')) for c in comments) / max(len(comments), 1)
        }
    }

def identify_network_connections(posts: List[Dict[str, Any]], comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Identify network connections and interaction patterns
    
    Args:
        posts: List of user's posts
        comments: List of user's comments
        
    Returns:
        Dictionary containing network analysis
    """
    from collections import Counter, defaultdict
    
    if not posts and not comments:
        return {'error': 'No data to analyze'}
    
    # Subreddit interaction analysis
    subreddit_interactions = defaultdict(lambda: {'posts': 0, 'comments': 0, 'total_score': 0})
    
    for post in posts:
        subreddit = post.get('subreddit')
        if subreddit:
            subreddit_interactions[subreddit]['posts'] += 1
            subreddit_interactions[subreddit]['total_score'] += post.get('score', 0)
    
    for comment in comments:
        subreddit = comment.get('subreddit')
        if subreddit:
            subreddit_interactions[subreddit]['comments'] += 1
            subreddit_interactions[subreddit]['total_score'] += comment.get('score', 0)
    
    # Calculate interaction strength
    for subreddit_data in subreddit_interactions.values():
        subreddit_data['total_interactions'] = subreddit_data['posts'] + subreddit_data['comments']
        subreddit_data['average_score'] = subreddit_data['total_score'] / max(subreddit_data['total_interactions'], 1)
    
    # Sort subreddits by interaction strength
    top_subreddits = sorted(
        subreddit_interactions.items(),
        key=lambda x: x[1]['total_interactions'],
        reverse=True
    )[:15]
    
    # Cross-subreddit activity patterns
    subreddit_pairs = []
    user_subreddits = list(subreddit_interactions.keys())
    
    # Find subreddits where user is active in both posts and comments
    active_in_both = [
        subreddit for subreddit, data in subreddit_interactions.items()
        if data['posts'] > 0 and data['comments'] > 0
    ]
    
    # Analyze posting vs commenting preferences
    post_heavy_subreddits = [
        subreddit for subreddit, data in subreddit_interactions.items()
        if data['posts'] > data['comments'] and data['posts'] > 1
    ]
    
    comment_heavy_subreddits = [
        subreddit for subreddit, data in subreddit_interactions.items()
        if data['comments'] > data['posts'] and data['comments'] > 1
    ]
    
    # Community engagement patterns
    high_engagement_subreddits = [
        subreddit for subreddit, data in subreddit_interactions.items()
        if data['average_score'] > 5  # Above average engagement
    ]
    
    return {
        'subreddit_network': {
            'total_unique_subreddits': len(subreddit_interactions),
            'top_subreddits_by_activity': [
                {
                    'subreddit': name,
                    'posts': data['posts'],
                    'comments': data['comments'],
                    'total_interactions': data['total_interactions'],
                    'total_score': data['total_score'],
                    'average_score': round(data['average_score'], 2)
                }
                for name, data in top_subreddits
            ]
        },
        'engagement_patterns': {
            'active_in_both_posts_and_comments': len(active_in_both),
            'post_heavy_subreddits': post_heavy_subreddits[:10],
            'comment_heavy_subreddits': comment_heavy_subreddits[:10],
            'high_engagement_subreddits': high_engagement_subreddits[:10]
        },
        'community_diversity': {
            'subreddit_concentration': len(top_subreddits[:5]) / max(len(subreddit_interactions), 1),
            'interaction_distribution': {
                'top_5_subreddits_percentage': sum(data['total_interactions'] for _, data in top_subreddits[:5]) / 
                                             max(sum(data['total_interactions'] for data in subreddit_interactions.values()), 1) * 100,
                'long_tail_subreddits': len([s for s, d in subreddit_interactions.items() if d['total_interactions'] == 1])
            }
        },
        'cross_subreddit_patterns': {
            'subreddits_with_multiple_posts': len([s for s, d in subreddit_interactions.items() if d['posts'] > 1]),
            'subreddits_with_multiple_comments': len([s for s, d in subreddit_interactions.items() if d['comments'] > 1]),
            'balanced_participation': len(active_in_both)
        }
    }

if __name__ == "__main__":
    analyze_sample_post()
