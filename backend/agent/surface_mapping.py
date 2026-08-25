"""Deterministic Instagram Platform Surface Mapping per Docs/03_RULE_SETS.md §2.

Maps content type and difficulty to the optimal Instagram placement:
- MCQ -> Story (native Quiz sticker)
- True/False -> Story (native Poll/Quiz sticker)
- This-or-That -> Story (native 2-choice Poll sticker)
- Fill in the Blank -> Feed (longer caption reading time)
- Guess the Number -> Feed (Easy/Medium) or Reel Caption (Hard, high engagement)
"""

from typing import Literal

PlatformSurface = Literal["Story", "Feed", "Reel Caption"]


def get_platform_surface(content_type: str, difficulty: str = "Medium") -> PlatformSurface:
    """Determine the native Instagram platform surface deterministically.

    Args:
        content_type: One of 'MCQ', 'True/False', 'This-or-That', 'Fill in the Blank', 'Guess the Number'.
        difficulty: 'Easy', 'Medium', or 'Hard'.

    Returns:
        One of 'Story', 'Feed', or 'Reel Caption'.
    """
    ct = content_type.strip()
    diff = difficulty.strip().capitalize()

    if ct == "MCQ":
        return "Story"
    elif ct == "True/False":
        return "Story"
    elif ct == "This-or-That":
        return "Story"
    elif ct == "Fill in the Blank":
        return "Feed"
    elif ct == "Guess the Number":
        if diff == "Hard":
            return "Reel Caption"
        return "Feed"
    
    # Default fallback
    return "Story"
