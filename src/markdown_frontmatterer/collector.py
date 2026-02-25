"""Instagram collection pipeline using instaloader."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

import instaloader
from instaloader import ConnectionException, LoginException, Profile, QueryReturnedNotFoundException

from markdown_frontmatterer.collect_models import (
    CollectedHighlight,
    CollectedMedia,
    CollectedPost,
    CollectedProfile,
    CollectedStoryItem,
    CollectResult,
)

logger = logging.getLogger(__name__)


# ── Loader creation ─────────────────────────────────────────


def create_loader(*, delay: float = 5.0) -> instaloader.Instaloader:
    """Create an Instaloader instance with conservative settings."""
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        max_connection_attempts=3,
        request_timeout=30.0,
    )
    loader.context.sleep = True
    return loader


# ── Authentication ──────────────────────────────────────────


def _authenticate_via_playwright(loader: instaloader.Instaloader) -> str:
    """Open a browser for Instagram login via Playwright persistent context.

    Uses ~/.mdh/browser-profile/ to persist login state across runs.
    Returns the authenticated username.
    """
    from playwright.sync_api import sync_playwright

    from markdown_frontmatterer.i18n import t

    user_data_dir = Path.home() / ".mdh" / "browser-profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=False,
            channel="chrome",
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        cookies = context.cookies(["https://www.instagram.com"])
        cookie_dict = {c["name"]: c["value"] for c in cookies}

        if cookie_dict.get("sessionid"):
            logger.info(t("collect_browser_already_logged_in"))
        else:
            input(t("collect_browser_login_prompt"))
            cookies = context.cookies(["https://www.instagram.com"])
            cookie_dict = {c["name"]: c["value"] for c in cookies}

        context.close()

    if not cookie_dict.get("sessionid"):
        raise LoginException("Instagram 로그인이 완료되지 않았습니다.")

    loader.context.update_cookies(cookie_dict)
    csrftoken = cookie_dict.get("csrftoken", "")
    if csrftoken:
        loader.context._session.headers.update({"X-CSRFToken": csrftoken})

    username = loader.test_login()
    if not username:
        raise LoginException("쿠키가 만료되었거나 유효하지 않습니다.")

    loader.context.username = username
    return username


def authenticate(
    loader: instaloader.Instaloader,
    *,
    login_user: str | None = None,
    password: str | None = None,
    session_file: str | None = None,
    browser: bool = False,
) -> bool:
    """Authenticate with Instagram. Returns True on success.

    Priority:
    1. --browser → Playwright persistent context (recommended)
    2. --login + session file → load + test_login() validation
    3. --login + --password → password login (unstable, warns)
    4. --login only → interactive login (unstable, warns)
    """
    # 1. Playwright browser authentication (recommended path)
    if browser:
        username = _authenticate_via_playwright(loader)
        loader.save_session_to_file(login_user or username)
        logger.info("Authenticated via Playwright browser as %s", username)
        return True

    if not login_user:
        return False

    # 2. Session file load + validation
    session_loaded = False
    if session_file:
        try:
            loader.load_session_from_file(login_user, session_file)
            logger.info("Loaded session from %s", session_file)
            session_loaded = True
        except FileNotFoundError:
            logger.info("Session file not found: %s", session_file)

    if not session_loaded:
        try:
            loader.load_session_from_file(login_user)
            logger.info("Loaded existing session for %s", login_user)
            session_loaded = True
        except FileNotFoundError:
            pass

    if session_loaded:
        username = loader.test_login()
        if username:
            logger.info("Session valid for %s", username)
            return True
        logger.warning("Session expired for %s, need re-authentication", login_user)

    # 3. Password / interactive login (unstable — instaloader login is broken since 2024)
    logger.warning("login()/interactive_login() is unstable. Use --browser instead.")
    if password:
        loader.login(login_user, password)
        loader.save_session_to_file()
        logger.info("Logged in as %s (password)", login_user)
        return True

    loader.interactive_login(login_user)
    loader.save_session_to_file()
    logger.info("Logged in as %s (interactive)", login_user)
    return True


# ── Profile collection ──────────────────────────────────────


def collect_profile(profile: Profile) -> CollectedProfile:
    """Extract profile information into our model."""
    return CollectedProfile(
        username=profile.username,
        full_name=profile.full_name,
        biography=profile.biography,
        media_count=profile.mediacount,
        followers=profile.followers,
        followees=profile.followees,
        profile_pic_url=str(profile.profile_pic_url),
        is_private=profile.is_private,
        is_verified=profile.is_verified,
    )


# ── Post collection ─────────────────────────────────────────


def _collect_post_media(post: instaloader.Post) -> list[CollectedMedia]:
    """Extract media files from a post."""
    media: list[CollectedMedia] = []

    if post.typename == "GraphSidecar":
        # Carousel: multiple slides
        for idx, node in enumerate(post.get_sidecar_nodes(), 1):
            if node.is_video:
                media.append(CollectedMedia(
                    url=node.video_url,
                    filename=f"{post.shortcode}_{idx}.mp4",
                    is_video=True,
                ))
            else:
                media.append(CollectedMedia(
                    url=node.display_url,
                    filename=f"{post.shortcode}_{idx}.jpg",
                ))
    elif post.is_video:
        media.append(CollectedMedia(
            url=post.video_url,
            filename=f"{post.shortcode}.mp4",
            is_video=True,
        ))
    else:
        media.append(CollectedMedia(
            url=post.url,
            filename=f"{post.shortcode}.jpg",
        ))

    return media


def collect_posts(
    profile: Profile,
    *,
    delay: float = 5.0,
    limit: int | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> list[CollectedPost]:
    """Collect posts from a profile.

    Returns whatever posts were collected before any fatal error.
    The iterator itself can throw ConnectionException during pagination,
    so we wrap the entire loop to preserve partial results.
    """
    posts: list[CollectedPost] = []
    count = 0

    try:
        for post in profile.get_posts():
            if limit and count >= limit:
                break

            try:
                location_name = ""
                try:
                    if post.location:
                        location_name = post.location.name or ""
                except (ConnectionException, Exception):
                    pass

                collected = CollectedPost(
                    shortcode=post.shortcode,
                    author=profile.username,
                    date=post.date_utc,
                    caption=post.caption or "",
                    likes=post.likes if isinstance(post.likes, int) else 0,
                    comments=post.comments,
                    is_video=post.is_video,
                    content_type="post",
                    location=location_name,
                    hashtags=list(post.caption_hashtags),
                    mentions=list(post.caption_mentions),
                    media=_collect_post_media(post),
                )
                posts.append(collected)
                count += 1

                if progress_callback:
                    progress_callback(f"post:{post.shortcode}")

                time.sleep(delay)

            except QueryReturnedNotFoundException:
                logger.warning("Post not found (deleted?), skipping")
            except ConnectionException as exc:
                logger.warning("Connection error on post %s: %s", post.shortcode, exc)
                time.sleep(delay * 3)  # Extra backoff

    except ConnectionException as exc:
        logger.warning("Pagination error after %d posts: %s", count, exc)
    except KeyboardInterrupt:
        logger.info("Interrupted by user after %d posts", count)

    return posts


def collect_reels(
    profile: Profile,
    *,
    delay: float = 5.0,
    limit: int | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> list[CollectedPost]:
    """Collect reels from a profile. Returns partial results on pagination errors."""
    reels: list[CollectedPost] = []
    count = 0

    try:
        for reel in profile.get_reels():
            if limit and count >= limit:
                break

            try:
                collected = CollectedPost(
                    shortcode=reel.shortcode,
                    author=profile.username,
                    date=reel.date_utc,
                    caption=reel.caption or "",
                    likes=reel.likes if isinstance(reel.likes, int) else 0,
                    comments=reel.comments,
                    is_video=True,
                    video_url=str(reel.video_url),
                    video_duration=getattr(reel, "video_duration", None),
                    video_view_count=getattr(reel, "video_view_count", None),
                    content_type="reel",
                    hashtags=list(reel.caption_hashtags),
                    mentions=list(reel.caption_mentions),
                    media=[CollectedMedia(
                        url=str(reel.video_url),
                        filename=f"{reel.shortcode}.mp4",
                        is_video=True,
                    )],
                )
                reels.append(collected)
                count += 1

                if progress_callback:
                    progress_callback(f"reel:{reel.shortcode}")

                time.sleep(delay)

            except QueryReturnedNotFoundException:
                logger.warning("Reel not found, skipping")
            except ConnectionException as exc:
                logger.warning("Connection error on reel: %s", exc)
                time.sleep(delay * 3)

    except ConnectionException as exc:
        logger.warning("Reel pagination error after %d reels: %s", count, exc)
    except KeyboardInterrupt:
        logger.info("Interrupted by user after %d reels", count)
    except AttributeError:
        logger.info("get_reels() not available, skipping reels collection")

    return reels


# ── Story collection ────────────────────────────────────────


def collect_stories(
    loader: instaloader.Instaloader,
    profile: Profile,
    *,
    delay: float = 5.0,
    progress_callback: Callable[[str], None] | None = None,
) -> list[CollectedStoryItem]:
    """Collect stories for a profile (requires login + following)."""
    stories: list[CollectedStoryItem] = []

    try:
        for story in loader.get_stories(userids=[profile.userid]):
            for item in story.get_items():
                try:
                    media: list[CollectedMedia] = []
                    mediaid = str(item.mediaid)

                    if item.is_video:
                        media.append(CollectedMedia(
                            url=str(item.video_url),
                            filename=f"story_{mediaid}.mp4",
                            is_video=True,
                        ))
                    else:
                        media.append(CollectedMedia(
                            url=str(item.url),
                            filename=f"story_{mediaid}.jpg",
                        ))

                    collected = CollectedStoryItem(
                        mediaid=mediaid,
                        date=item.date_utc,
                        is_video=item.is_video,
                        url=str(item.url),
                        video_url=str(item.video_url) if item.is_video else "",
                        media=media,
                    )
                    stories.append(collected)

                    if progress_callback:
                        progress_callback(f"story:{mediaid}")

                    time.sleep(delay)

                except Exception as exc:
                    logger.warning("Error collecting story item: %s", exc)

    except Exception as exc:
        logger.warning("Could not collect stories: %s", exc)

    return stories


# ── Highlight collection ────────────────────────────────────


def collect_highlights(
    loader: instaloader.Instaloader,
    profile: Profile,
    *,
    delay: float = 5.0,
    progress_callback: Callable[[str], None] | None = None,
) -> list[CollectedHighlight]:
    """Collect highlights for a profile (requires login)."""
    highlights: list[CollectedHighlight] = []

    try:
        for highlight in loader.get_highlights(profile.userid):
            items: list[CollectedStoryItem] = []

            for item in highlight.get_items():
                try:
                    media: list[CollectedMedia] = []
                    mediaid = str(item.mediaid)

                    if item.is_video:
                        media.append(CollectedMedia(
                            url=str(item.video_url),
                            filename=f"highlight_{highlight.title}_{mediaid}.mp4",
                            is_video=True,
                        ))
                    else:
                        media.append(CollectedMedia(
                            url=str(item.url),
                            filename=f"highlight_{highlight.title}_{mediaid}.jpg",
                        ))

                    collected = CollectedStoryItem(
                        mediaid=mediaid,
                        date=item.date_utc,
                        is_video=item.is_video,
                        url=str(item.url),
                        video_url=str(item.video_url) if item.is_video else "",
                        media=media,
                    )
                    items.append(collected)

                    if progress_callback:
                        progress_callback(f"highlight:{highlight.title}:{mediaid}")

                    time.sleep(delay)

                except Exception as exc:
                    logger.warning("Error collecting highlight item: %s", exc)

            highlights.append(CollectedHighlight(title=highlight.title, items=items))

    except Exception as exc:
        logger.warning("Could not collect highlights: %s", exc)

    return highlights


# ── Main pipeline ───────────────────────────────────────────


def run_collect(
    target: str,
    *,
    login_user: str | None = None,
    password: str | None = None,
    session_file: str | None = None,
    browser: bool = False,
    output_dir: Path = Path("./collected"),
    include_stories: bool = False,
    include_highlights: bool = False,
    include_reels: bool = True,
    limit: int | None = None,
    delay: float = 5.0,
    progress_callback: Callable[[str], None] | None = None,
) -> CollectResult:
    """Run the full Instagram collection pipeline.

    Pipeline:
    1. Create loader + authenticate
    2. Fetch profile
    3. Collect posts (+ reels, stories, highlights as requested)
    4. Write markdown + download media
    5. Return result
    """
    # Clean target username
    username = target.lstrip("@")

    loader = create_loader(delay=delay)

    # Authenticate
    if browser or login_user:
        authenticate(
            loader,
            login_user=login_user,
            password=password,
            session_file=session_file,
            browser=browser,
        )

    # Fetch profile
    profile = Profile.from_username(loader.context, username)
    collected_profile = collect_profile(profile)

    # Check private account access
    if profile.is_private and not profile.followed_by_viewer:
        raise PermissionError(
            f"@{username} is a private account and you are not following them."
        )

    if progress_callback:
        progress_callback("profile_done")

    errors: list[str] = []

    # Collect posts
    posts = collect_posts(
        profile, delay=delay, limit=limit, progress_callback=progress_callback,
    )

    # Collect reels
    reels: list[CollectedPost] = []
    if include_reels:
        try:
            reels = collect_reels(
                profile, delay=delay, limit=limit, progress_callback=progress_callback,
            )
        except Exception as exc:
            errors.append(f"reels: {exc}")
            logger.warning("Failed to collect reels: %s", exc)

    # Collect stories
    stories: list[CollectedStoryItem] = []
    if include_stories:
        try:
            stories = collect_stories(
                loader, profile, delay=delay, progress_callback=progress_callback,
            )
        except Exception as exc:
            errors.append(f"stories: {exc}")
            logger.warning("Failed to collect stories: %s", exc)

    # Collect highlights
    highlights: list[CollectedHighlight] = []
    if include_highlights:
        try:
            highlights = collect_highlights(
                loader, profile, delay=delay, progress_callback=progress_callback,
            )
        except Exception as exc:
            errors.append(f"highlights: {exc}")
            logger.warning("Failed to collect highlights: %s", exc)

    result = CollectResult(
        profile=collected_profile,
        posts=posts,
        reels=reels,
        stories=stories,
        highlights=highlights,
        errors=errors,
    )

    if progress_callback:
        progress_callback("collection_done")

    return result
