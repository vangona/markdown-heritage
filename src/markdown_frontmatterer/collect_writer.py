"""Markdown generation and media download for collected Instagram data."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

import httpx
import yaml

from markdown_frontmatterer.collect_models import (
    CollectedHighlight,
    CollectedMedia,
    CollectedPost,
    CollectedProfile,
    CollectedStoryItem,
    CollectResult,
)

logger = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT = 60.0


# ── Media download ──────────────────────────────────────────


def download_media(
    media: CollectedMedia,
    media_dir: Path,
    *,
    delay: float = 0.5,
    progress_callback: Callable[[str], None] | None = None,
) -> bool:
    """Download a single media file. Returns True on success."""
    dest = media_dir / media.filename
    if dest.exists():
        return True

    try:
        with httpx.Client(timeout=_DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(media.url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        if progress_callback:
            progress_callback(media.filename)
        if delay > 0:
            time.sleep(delay)
        return True
    except Exception as exc:
        logger.warning("Failed to download %s: %s", media.filename, exc)
        return False


def download_all_media(
    result: CollectResult,
    media_dir: Path,
    *,
    delay: float = 0.5,
    progress_callback: Callable[[str], None] | None = None,
) -> int:
    """Download all media from a CollectResult. Returns count of successful downloads."""
    media_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    all_media: list[CollectedMedia] = []

    # Profile pic
    if result.profile.profile_pic_url:
        all_media.append(
            CollectedMedia(
                url=result.profile.profile_pic_url,
                filename="profile_pic.jpg",
            )
        )

    for post in result.posts + result.reels:
        all_media.extend(post.media)
    for story in result.stories:
        all_media.extend(story.media)
    for highlight in result.highlights:
        for item in highlight.items:
            all_media.extend(item.media)

    for media in all_media:
        if download_media(media, media_dir, delay=delay, progress_callback=progress_callback):
            downloaded += 1

    return downloaded


# ── YAML frontmatter helpers ────────────────────────────────


def _yaml_dump(data: dict) -> str:
    """Dump dict to YAML frontmatter string."""
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False).rstrip()


def _post_frontmatter(post: CollectedPost) -> dict:
    """Build frontmatter dict for a post or reel."""
    fm: dict = {
        "source": "instagram",
        "content_type": post.content_type,
        "shortcode": post.shortcode,
        "url": f"https://www.instagram.com/p/{post.shortcode}/",
        "author": post.author,
        "date": post.date.isoformat(),
        "likes": post.likes,
        "comments": post.comments,
        "is_video": post.is_video,
    }
    if post.media:
        fm["media_files"] = [f"../media/{m.filename}" for m in post.media]
    if post.video_duration is not None:
        fm["video_duration"] = post.video_duration
    if post.video_view_count is not None:
        fm["video_view_count"] = post.video_view_count
    if post.location:
        fm["location"] = post.location
    if post.hashtags:
        fm["hashtags"] = post.hashtags
    if post.mentions:
        fm["mentions"] = post.mentions
    return fm


def _story_frontmatter(item: CollectedStoryItem, *, author: str) -> dict:
    """Build frontmatter dict for a story item."""
    fm: dict = {
        "source": "instagram",
        "content_type": "story",
        "mediaid": item.mediaid,
        "author": author,
        "date": item.date.isoformat(),
        "is_video": item.is_video,
    }
    if item.media:
        fm["media_files"] = [f"../media/{m.filename}" for m in item.media]
    return fm


# ── Markdown generation ─────────────────────────────────────


def _make_frontmatter_block(data: dict) -> str:
    """Wrap a dict as a YAML frontmatter block."""
    return f"---\n{_yaml_dump(data)}\n---"


def write_post_md(post: CollectedPost, dest: Path) -> None:
    """Write a single post/reel markdown file."""
    fm = _post_frontmatter(post)
    date_str = post.date.strftime("%Y-%m-%d")
    content_label = "Post" if post.content_type == "post" else "Reel"

    lines = [_make_frontmatter_block(fm), ""]
    lines.append(f"# {content_label} by @{post.author} - {date_str}")
    lines.append("")

    for i, media in enumerate(post.media, 1):
        label = "Video" if media.is_video else "Image"
        lines.append(f"![{label} {i}](../media/{media.filename})")
    lines.append("")

    if post.caption:
        lines.append(post.caption)
        lines.append("")

    dest.write_text("\n".join(lines), encoding="utf-8")


def write_story_md(item: CollectedStoryItem, dest: Path, *, author: str) -> None:
    """Write a single story item markdown file."""
    fm = _story_frontmatter(item, author=author)
    date_str = item.date.strftime("%Y-%m-%d")

    lines = [_make_frontmatter_block(fm), ""]
    lines.append(f"# Story by @{author} - {date_str}")
    lines.append("")

    for i, media in enumerate(item.media, 1):
        label = "Video" if media.is_video else "Image"
        lines.append(f"![{label} {i}](../media/{media.filename})")
    lines.append("")

    dest.write_text("\n".join(lines), encoding="utf-8")


def write_profile_md(profile: CollectedProfile, dest: Path) -> None:
    """Write the _profile.md file."""
    fm: dict = {
        "source": "instagram",
        "content_type": "profile",
        "username": profile.username,
        "full_name": profile.full_name,
        "biography": profile.biography,
        "media_count": profile.media_count,
        "followers": profile.followers,
        "followees": profile.followees,
        "is_private": profile.is_private,
        "is_verified": profile.is_verified,
    }

    lines = [_make_frontmatter_block(fm), ""]
    lines.append(f"# @{profile.username}")
    lines.append("")

    if profile.full_name:
        lines.append(f"**{profile.full_name}**")
        lines.append("")
    if profile.biography:
        lines.append(profile.biography)
        lines.append("")
    if profile.profile_pic_url:
        lines.append("![Profile Picture](./media/profile_pic.jpg)")
        lines.append("")

    lines.append(f"- Posts: {profile.media_count}")
    lines.append(f"- Followers: {profile.followers:,}")
    lines.append(f"- Following: {profile.followees:,}")
    lines.append("")

    dest.write_text("\n".join(lines), encoding="utf-8")


def write_index_md(result: CollectResult, dest: Path) -> None:
    """Write the _index.md table-of-contents file."""
    p = result.profile
    lines = [f"# @{p.username} — Archive Index", ""]

    lines.append(f"Collected {len(result.posts)} posts, {len(result.reels)} reels")
    if result.stories:
        lines.append(f", {len(result.stories)} stories")
    if result.highlights:
        total_items = sum(len(h.items) for h in result.highlights)
        lines.append(f", {len(result.highlights)} highlights ({total_items} items)")
    lines.append("")

    if result.posts:
        lines.append("## Posts")
        lines.append("")
        for post in sorted(result.posts, key=lambda p: p.date, reverse=True):
            date_str = post.date.strftime("%Y-%m-%d")
            fname = f"{date_str}_{post.shortcode}.md"
            preview = (post.caption[:60] + "...") if post.caption and len(post.caption) > 60 else (post.caption or "(no caption)")
            lines.append(f"- [{date_str} {post.shortcode}](./posts/{fname}) — {preview}")
        lines.append("")

    if result.reels:
        lines.append("## Reels")
        lines.append("")
        for reel in sorted(result.reels, key=lambda r: r.date, reverse=True):
            date_str = reel.date.strftime("%Y-%m-%d")
            fname = f"{date_str}_{reel.shortcode}.md"
            preview = (reel.caption[:60] + "...") if reel.caption and len(reel.caption) > 60 else (reel.caption or "(no caption)")
            lines.append(f"- [{date_str} {reel.shortcode}](./reels/{fname}) — {preview}")
        lines.append("")

    if result.stories:
        lines.append("## Stories")
        lines.append("")
        for story in sorted(result.stories, key=lambda s: s.date, reverse=True):
            date_str = story.date.strftime("%Y-%m-%d")
            fname = f"{date_str}_{story.mediaid}.md"
            label = "Video" if story.is_video else "Photo"
            lines.append(f"- [{date_str} {label}](./stories/{fname})")
        lines.append("")

    if result.highlights:
        lines.append("## Highlights")
        lines.append("")
        for highlight in result.highlights:
            lines.append(f"### {highlight.title}")
            lines.append("")
            for item in sorted(highlight.items, key=lambda i: i.date, reverse=True):
                date_str = item.date.strftime("%Y-%m-%d")
                fname = f"{date_str}_{item.mediaid}.md"
                label = "Video" if item.is_video else "Photo"
                lines.append(f"- [{date_str} {label}](./highlights/{highlight.title}/{fname})")
            lines.append("")

    dest.write_text("\n".join(lines), encoding="utf-8")


# ── Main writer ─────────────────────────────────────────────


def write_all(
    result: CollectResult,
    output_dir: Path,
    *,
    delay: float = 0.5,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """Write all collected data to disk.

    Returns a summary dict with counts of written files and downloaded media.
    """
    base = output_dir / f"@{result.profile.username}"
    media_dir = base / "media"
    posts_dir = base / "posts"
    reels_dir = base / "reels"
    stories_dir = base / "stories"

    # Create directories
    for d in [media_dir, posts_dir]:
        d.mkdir(parents=True, exist_ok=True)
    if result.reels:
        reels_dir.mkdir(parents=True, exist_ok=True)
    if result.stories:
        stories_dir.mkdir(parents=True, exist_ok=True)

    counts = {"posts": 0, "reels": 0, "stories": 0, "highlights": 0, "media": 0}

    # Download media
    counts["media"] = download_all_media(
        result, media_dir, delay=delay, progress_callback=progress_callback
    )

    # Write profile
    write_profile_md(result.profile, base / "_profile.md")

    # Write posts
    for post in result.posts:
        date_str = post.date.strftime("%Y-%m-%d")
        write_post_md(post, posts_dir / f"{date_str}_{post.shortcode}.md")
        counts["posts"] += 1

    # Write reels
    for reel in result.reels:
        date_str = reel.date.strftime("%Y-%m-%d")
        write_post_md(reel, reels_dir / f"{date_str}_{reel.shortcode}.md")
        counts["reels"] += 1

    # Write stories
    for story in result.stories:
        date_str = story.date.strftime("%Y-%m-%d")
        write_story_md(
            story, stories_dir / f"{date_str}_{story.mediaid}.md",
            author=result.profile.username,
        )
        counts["stories"] += 1

    # Write highlights
    for highlight in result.highlights:
        h_dir = base / "highlights" / highlight.title
        h_dir.mkdir(parents=True, exist_ok=True)
        for item in highlight.items:
            date_str = item.date.strftime("%Y-%m-%d")
            write_story_md(
                item, h_dir / f"{date_str}_{item.mediaid}.md",
                author=result.profile.username,
            )
            counts["highlights"] += 1

    # Write index last (after all content is ready)
    write_index_md(result, base / "_index.md")

    return counts
