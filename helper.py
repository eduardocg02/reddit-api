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
    
    # Comments Section
    output.append("## 💬 Comments Thread")
    output.append("")
    
    if not comments_data:
        output.append("*No comments available*")
    else:
        # Count ALL comments including nested replies
        total_comments = count_all_comments(comments_data)
        output.append(f"**Total Comments:** {total_comments:,} (including all replies)")
        output.append(f"**Top-level Comments:** {len(comments_data)}")
        output.append("")
        
        # Format each top-level comment and its replies
        for i, comment in enumerate(comments_data, 1):
            output.append(f"### Comment #{i}")
            output.append("")
            output.append(format_comment_thread(comment))
            
            # Add separator between comments (except for the last one)
            if i < len(comments_data):
                output.append("---")
                output.append("")
    
    # No footer - clean end
    output.append("")
    
    return "\n".join(output)

if __name__ == "__main__":
    analyze_sample_post()
