"""
Style Registry - Centralized configuration for all workflow styles.

Adding a new style:
1. Create workflow file: workflows/{type}_{index}_v{version}.json
2. Add entry to STYLES dict below
3. Add translations: locales/*.json under "styles.{id}"
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StyleConfig:
    """Configuration for a workflow style."""
    id: str                      # "i2i_1", "i2v_2"
    type: str                    # "i2i" or "i2v"
    workflow_file: str           # "i2i_1_v5.json"
    locale_key: str              # "styles.i2i_1" (for translations)
    cost: int                    # credits (0 = free)
    is_free: bool                # permanently free?
    demo_link: Optional[str]     # demo video/image link
    enabled: bool                # can disable without deleting
    db_feature_type: str         # backwards-compatible DB value


# Style Registry
STYLES: dict[str, StyleConfig] = {
    # Image-to-Image styles
    "i2i_1": StyleConfig(
        id="i2i_1",
        type="i2i",
        workflow_file="i2i_1_v1.json",
        locale_key="styles.i2i_1",
        cost=0,
        is_free=True,
        demo_link="https://t.me/zuiqiangtuoyi/25",
        enabled=True,
        db_feature_type="image_bra"  # Keep old DB value
    ),
    "i2i_2": StyleConfig(
        id="i2i_2",
        type="i2i",
        workflow_file="i2i_2_v1.json",
        locale_key="styles.i2i_2",
        cost=10,
        is_free=False,
        demo_link="https://t.me/zuiqiangtuoyi/29",
        enabled=True,
        db_feature_type="image_undress"
    ),
    "i2i_3": StyleConfig(
        id="i2i_3",
        type="i2i",
        workflow_file="i2i_3_v1.json",
        locale_key="styles.i2i_3",
        cost=10,
        is_free=False,
        demo_link="https://t.me/zuiqiangtuoyi",
        enabled=True,
        db_feature_type="image_pussydrip"
    ),
    "i2i_4": StyleConfig(
        id="i2i_4",
        type="i2i",
        workflow_file="i2i_4_v1.json",
        locale_key="styles.i2i_4",
        cost=10,
        is_free=False,
        demo_link="https://t.me/zuiqiangtuoyi",
        enabled=True,
        db_feature_type="image_mouthdrip"
    ),
    "i2i_5": StyleConfig(
        id="i2i_5",
        type="i2i",
        workflow_file="i2i_5_v1.json",
        locale_key="styles.i2i_5",
        cost=10,
        is_free=False,
        demo_link="https://t.me/zuiqiangtuoyi",
        enabled=True,
        db_feature_type="image_backpussydrip"
    ),
    "i2i_6": StyleConfig(
        id="i2i_6",
        type="i2i",
        workflow_file="i2i_6_v1.json",
        locale_key="styles.i2i_6",
        cost=10,
        is_free=False,
        demo_link="https://t.me/zuiqiangtuoyi",
        enabled=True,
        db_feature_type="image_blowjobdrip"
    ),
    "i2i_7": StyleConfig(
        id="i2i_7",
        type="i2i",
        workflow_file="i2i_7_v1.json",
        locale_key="styles.i2i_7",
        cost=10,
        is_free=False,
        demo_link="https://t.me/zuiqiangtuoyi",
        enabled=True,
        db_feature_type="image_girlwithdick"
    ),
    "i2i_8": StyleConfig(
        id="i2i_8",
        type="i2i",
        workflow_file="i2i_8_v1.json",
        locale_key="styles.i2i_8",
        cost=10,
        is_free=False,
        demo_link="https://t.me/zuiqiangtuoyi",
        enabled=True,
        db_feature_type="image_cowgirl"
    ),
    "i2i_9": StyleConfig(
        id="i2i_9",
        type="i2i",
        workflow_file="i2i_9_v1.json",
        locale_key="styles.i2i_9",
        cost=10,
        is_free=False,
        demo_link="https://t.me/zuiqiangtuoyi",
        enabled=True,
        db_feature_type="image_upskirt"
    ),

    # Image-to-Video styles
    "i2v_1": StyleConfig(
        id="i2v_1",
        type="i2v",
        workflow_file="i2v_1_v1.json",
        locale_key="styles.i2v_1",
        cost=30,
        is_free=False,
        demo_link="https://t.me/zuiqiangtuoyi/13",
        enabled=True,
        db_feature_type="video_style_a"
    ),
    "i2v_2": StyleConfig(
        id="i2v_2",
        type="i2v",
        workflow_file="i2v_2_v1.json",
        locale_key="styles.i2v_2",
        cost=30,
        is_free=False,
        demo_link="https://t.me/zuiqiangtuoyi/15",
        enabled=True,
        db_feature_type="video_style_b"
    ),
    "i2v_3": StyleConfig(
        id="i2v_3",
        type="i2v",
        workflow_file="i2v_3_v1.json",
        locale_key="styles.i2v_3",
        cost=30,
        is_free=False,
        demo_link="https://t.me/zuiqiangtuoyi/19",
        enabled=True,
        db_feature_type="video_style_c"
    ),
}


def get_style(style_id: str) -> StyleConfig:
    """Get style config by ID. Raises KeyError if not found."""
    return STYLES[style_id]


def get_style_or_none(style_id: str) -> Optional[StyleConfig]:
    """Get style config by ID, returns None if not found."""
    return STYLES.get(style_id)


def get_styles_by_type(style_type: str) -> list[StyleConfig]:
    """Get all styles of a given type (i2i or i2v)."""
    return [s for s in STYLES.values() if s.type == style_type]


def get_enabled_styles() -> list[StyleConfig]:
    """Get all enabled styles."""
    return [s for s in STYLES.values() if s.enabled]


def get_enabled_styles_by_type(style_type: str) -> list[StyleConfig]:
    """Get all enabled styles of a given type."""
    return [s for s in STYLES.values() if s.type == style_type and s.enabled]


def get_style_by_db_feature_type(db_feature_type: str) -> Optional[StyleConfig]:
    """Get style config by legacy DB feature_type value."""
    for style in STYLES.values():
        if style.db_feature_type == db_feature_type:
            return style
    return None


# Convenience constants for common lookups
I2I_STYLES = get_styles_by_type("i2i")
I2V_STYLES = get_styles_by_type("i2v")
