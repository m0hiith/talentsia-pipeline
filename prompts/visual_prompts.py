"""
Visual Prompt Generator — auto-converts scripts to FLUX.1 / CogVideoX / Wan2.1 prompts.
Maps script beats to visual scene descriptions for each AI model.
"""


def script_to_visual_prompts(script_text: str, story_title: str) -> dict:
    """Convert a script into visual generation prompts.

    Returns:
        dict with keys:
          - thumbnail: FLUX.1 prompt for cover image
          - images: list of FLUX.1 prompts for key frames
          - broll: list of CogVideoX/Wan2.1 prompts for B-roll clips
    """
    # Extract hook and key keywords
    lines = [l.strip() for l in script_text.strip().split("\n") if l.strip()]
    hook = lines[0] if lines else story_title
    keywords = _extract_keywords(story_title + " " + script_text)

    # ── Thumbnail Prompt ──────────────────────
    thumbnail = _build_thumbnail_prompt(story_title, keywords)

    # ── Key Frame Images ──────────────────────
    images = _build_image_prompts(lines, keywords)

    # ── B-roll Video Clips ────────────────────
    broll = _build_broll_prompts(story_title, keywords)

    return {
        "thumbnail": thumbnail,
        "images": images,
        "broll": broll,
    }


def _extract_keywords(text: str) -> list[str]:
    """Extract relevant visual keywords from text."""
    # Tech/AI visual concepts
    keyword_map = {
        "ai": "artificial intelligence neural network",
        "robot": "humanoid robot futuristic",
        "job": "business office workplace",
        "startup": "modern startup office",
        "code": "programming code screen",
        "data": "data visualization holographic",
        "gpt": "AI brain neural connections",
        "machine learning": "machine learning algorithms",
        "automation": "robotic automation factory",
        "future": "futuristic technology cityscape",
        "chip": "semiconductor microchip close-up",
        "google": "tech company headquarters",
        "apple": "minimalist tech design",
        "tesla": "electric vehicle futuristic",
        "openai": "AI research laboratory",
        "microsoft": "enterprise technology cloud",
    }

    text_lower = text.lower()
    keywords = []
    for key, visual in keyword_map.items():
        if key in text_lower:
            keywords.append(visual)

    if not keywords:
        keywords = ["futuristic technology digital landscape"]

    return keywords[:5]


def _build_thumbnail_prompt(title: str, keywords: list[str]) -> str:
    """Build a compelling thumbnail prompt for FLUX.1."""
    context = keywords[0] if keywords else "futuristic technology"
    return (
        f"Cinematic thumbnail for Instagram Reel about: {title[:80]}. "
        f"Scene: {context}, dramatic lighting, ultra-detailed, "
        f"8K quality, vibrant neon accents on dark background, "
        f"professional tech editorial photography style, "
        f"sharp focus, rule of thirds composition, "
        f"trending on artstation, photorealistic"
    )


def _build_image_prompts(script_lines: list[str], keywords: list[str]) -> list[str]:
    """Build key frame image prompts from script beats."""
    prompts = []

    # Hook frame — dramatic, attention-grabbing
    if script_lines:
        hook_context = keywords[0] if keywords else "technology"
        prompts.append(
            f"Dramatic cinematic shot, {hook_context}, "
            f"dark moody atmosphere with neon blue and purple accents, "
            f"ultra-detailed, 8K, professional photography, "
            f"Instagram Reel thumbnail style, impactful composition"
        )

    # Body frames — informational, clean
    for i, kw in enumerate(keywords[1:3]):
        prompts.append(
            f"Clean modern visualization of {kw}, "
            f"minimalist tech aesthetic, dark background, "
            f"soft ambient lighting, infographic style, "
            f"4K quality, sleek professional look"
        )

    # CTA frame — engaging, warm
    if len(keywords) > 0:
        prompts.append(
            f"Engaging close-up shot, {keywords[-1]}, "
            f"warm lighting, inviting atmosphere, "
            f"social media style, high engagement visual, "
            f"professional quality, eye-catching"
        )

    return prompts[:4]  # Max 4 images per script


def _build_broll_prompts(title: str, keywords: list[str]) -> list[str]:
    """Build B-roll video prompts for CogVideoX or Wan2.1."""
    prompts = []

    # Context B-roll
    if keywords:
        prompts.append(
            f"Cinematic B-roll footage: {keywords[0]}, "
            f"slow motion, smooth camera movement, "
            f"professional videography, bokeh background, "
            f"4K ultra HD, moody ambient lighting, editorial style"
        )

    # Tech/abstract B-roll
    prompts.append(
        f"Abstract technology visualization related to {title[:50]}, "
        f"futuristic holographic interface, "
        f"floating data particles, neon blue and purple glow, "
        f"smooth 60fps camera orbit, cinematic depth of field"
    )

    # Transition B-roll
    if len(keywords) > 1:
        prompts.append(
            f"Dynamic transition shot: {keywords[1]}, "
            f"cinematic camera push-in, dramatic reveal, "
            f"professional film quality, atmospheric lighting, "
            f"tech documentary style footage"
        )

    return prompts[:3]  # Max 3 B-roll clips per script
