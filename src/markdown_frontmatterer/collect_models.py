"""Data models for the collect command."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CollectedMedia:
    """A single media file (image or video) within a post."""

    url: str
    filename: str
    is_video: bool = False


@dataclass
class CollectedPost:
    """A single Instagram post or reel."""

    shortcode: str
    author: str
    date: datetime
    caption: str = ""
    likes: int = 0
    comments: int = 0
    is_video: bool = False
    video_url: str = ""
    video_duration: float | None = None
    video_view_count: int | None = None
    content_type: str = "post"  # "post" or "reel"
    location: str = ""
    hashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    media: list[CollectedMedia] = field(default_factory=list)


@dataclass
class CollectedStoryItem:
    """A single story or highlight item."""

    mediaid: str
    date: datetime
    is_video: bool = False
    url: str = ""
    video_url: str = ""
    media: list[CollectedMedia] = field(default_factory=list)


@dataclass
class CollectedHighlight:
    """A highlight collection with a title and items."""

    title: str
    items: list[CollectedStoryItem] = field(default_factory=list)


@dataclass
class CollectedProfile:
    """Instagram profile information."""

    username: str
    full_name: str = ""
    biography: str = ""
    media_count: int = 0
    followers: int = 0
    followees: int = 0
    profile_pic_url: str = ""
    is_private: bool = False
    is_verified: bool = False


@dataclass
class CollectResult:
    """Final result of a collect operation."""

    profile: CollectedProfile
    posts: list[CollectedPost] = field(default_factory=list)
    reels: list[CollectedPost] = field(default_factory=list)
    stories: list[CollectedStoryItem] = field(default_factory=list)
    highlights: list[CollectedHighlight] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_media(self) -> int:
        count = sum(len(p.media) for p in self.posts)
        count += sum(len(r.media) for r in self.reels)
        count += sum(len(s.media) for s in self.stories)
        for h in self.highlights:
            count += sum(len(i.media) for i in h.items)
        return count
