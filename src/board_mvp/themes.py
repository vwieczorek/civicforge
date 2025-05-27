"""Theme system for CivicForge boards - allows customizable UI themes."""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

@dataclass
class ThemeColors:
    """Color scheme for a theme."""
    primary: str = "#2563eb"  # Blue
    secondary: str = "#10b981"  # Green
    accent: str = "#f59e0b"  # Amber
    background: str = "#ffffff"
    surface: str = "#f3f4f6"
    text: str = "#111827"
    text_secondary: str = "#6b7280"
    error: str = "#ef4444"
    success: str = "#10b981"
    warning: str = "#f59e0b"
    info: str = "#3b82f6"

@dataclass
class ThemeTypography:
    """Typography settings for a theme."""
    font_family: str = "system-ui, -apple-system, sans-serif"
    font_size_base: str = "16px"
    font_size_small: str = "14px"
    font_size_large: str = "18px"
    font_size_heading: str = "24px"
    line_height: str = "1.5"

@dataclass
class ThemeSpacing:
    """Spacing settings for a theme."""
    unit: str = "0.25rem"  # 4px base unit
    small: str = "0.5rem"
    medium: str = "1rem"
    large: str = "1.5rem"
    xlarge: str = "2rem"

@dataclass
class ThemeComponents:
    """Component-specific styling."""
    border_radius: str = "0.375rem"
    border_width: str = "1px"
    shadow_small: str = "0 1px 2px rgba(0, 0, 0, 0.05)"
    shadow_medium: str = "0 4px 6px rgba(0, 0, 0, 0.1)"
    shadow_large: str = "0 10px 15px rgba(0, 0, 0, 0.1)"
    transition: str = "all 0.2s ease"

@dataclass
class RewardPoints:
    """Point configuration for different task types."""
    base_points: int = 10
    completion_bonus: int = 5
    quality_multiplier: float = 1.5
    speed_bonus: int = 2
    collaboration_bonus: int = 3
    
@dataclass
class RewardDecay:
    """Configuration for point decay over time."""
    enabled: bool = False
    rate_per_day: float = 0.01  # 1% per day
    minimum_retained: float = 0.5  # Keep at least 50%
    grace_period_days: int = 7  # No decay for first week
    
@dataclass
class RewardBadges:
    """Badge/achievement configuration."""
    enabled: bool = True
    milestone_badges: Dict[int, str] = field(default_factory=lambda: {
        10: "Newcomer",
        50: "Contributor", 
        100: "Active Member",
        500: "Community Leader",
        1000: "Champion"
    })
    special_badges: Dict[str, str] = field(default_factory=lambda: {
        "first_task": "Pioneer",
        "streak_7": "Week Warrior",
        "helper": "Helping Hand",
        "quality": "Quality Champion"
    })

@dataclass
class ThemeRewards:
    """Complete rewards and incentives configuration."""
    # Terminology
    points_name: str = "Civic Points"
    points_abbreviation: str = "CP"
    experience_name: str = "Experience"
    experience_abbreviation: str = "XP"
    level_name: str = "Level"
    quest_name: str = "Quest"
    task_name: str = "Task"
    
    # Point system
    point_system: RewardPoints = field(default_factory=RewardPoints)
    decay_config: RewardDecay = field(default_factory=RewardDecay)
    
    # Task-specific rewards
    task_rewards: Dict[str, int] = field(default_factory=lambda: {
        "simple": 10,
        "moderate": 25,
        "complex": 50,
        "critical": 100
    })
    
    # Bonuses and multipliers
    exceptional_multiplier: float = 2.0
    team_multiplier: float = 1.2
    streak_multiplier: float = 1.1
    
    # Visual indicators
    show_points: bool = True
    show_levels: bool = True
    show_badges: bool = True
    animated_rewards: bool = True
    
    # Badge configuration
    badges: RewardBadges = field(default_factory=RewardBadges)

@dataclass
class Theme:
    """Complete theme definition for a CivicForge board."""
    id: str
    name: str
    description: str
    author: str
    version: str = "1.0.0"
    colors: ThemeColors = field(default_factory=ThemeColors)
    typography: ThemeTypography = field(default_factory=ThemeTypography)
    spacing: ThemeSpacing = field(default_factory=ThemeSpacing)
    components: ThemeComponents = field(default_factory=ThemeComponents)
    rewards: ThemeRewards = field(default_factory=ThemeRewards)
    custom_css: str = ""
    preview_image: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    downloads: int = 0
    rating: float = 0.0

    def to_css_variables(self) -> str:
        """Convert theme to CSS custom properties."""
        return f"""
:root {{
    /* Colors */
    --color-primary: {self.colors.primary};
    --color-secondary: {self.colors.secondary};
    --color-accent: {self.colors.accent};
    --color-background: {self.colors.background};
    --color-surface: {self.colors.surface};
    --color-text: {self.colors.text};
    --color-text-secondary: {self.colors.text_secondary};
    --color-error: {self.colors.error};
    --color-success: {self.colors.success};
    --color-warning: {self.colors.warning};
    --color-info: {self.colors.info};
    
    /* Typography */
    --font-family: {self.typography.font_family};
    --font-size-base: {self.typography.font_size_base};
    --font-size-small: {self.typography.font_size_small};
    --font-size-large: {self.typography.font_size_large};
    --font-size-heading: {self.typography.font_size_heading};
    --line-height: {self.typography.line_height};
    
    /* Spacing */
    --spacing-unit: {self.spacing.unit};
    --spacing-small: {self.spacing.small};
    --spacing-medium: {self.spacing.medium};
    --spacing-large: {self.spacing.large};
    --spacing-xlarge: {self.spacing.xlarge};
    
    /* Components */
    --border-radius: {self.components.border_radius};
    --border-width: {self.components.border_width};
    --shadow-small: {self.components.shadow_small};
    --shadow-medium: {self.components.shadow_medium};
    --shadow-large: {self.components.shadow_large};
    --transition: {self.components.transition};
}}
"""

    def to_dict(self) -> dict:
        """Convert theme to dictionary for JSON serialization."""
        rewards_dict = {
            "points_name": self.rewards.points_name,
            "points_abbreviation": self.rewards.points_abbreviation,
            "experience_name": self.rewards.experience_name,
            "experience_abbreviation": self.rewards.experience_abbreviation,
            "level_name": self.rewards.level_name,
            "quest_name": self.rewards.quest_name,
            "task_name": self.rewards.task_name,
            "point_system": self.rewards.point_system.__dict__,
            "decay_config": self.rewards.decay_config.__dict__,
            "task_rewards": self.rewards.task_rewards,
            "exceptional_multiplier": self.rewards.exceptional_multiplier,
            "team_multiplier": self.rewards.team_multiplier,
            "streak_multiplier": self.rewards.streak_multiplier,
            "show_points": self.rewards.show_points,
            "show_levels": self.rewards.show_levels,
            "show_badges": self.rewards.show_badges,
            "animated_rewards": self.rewards.animated_rewards,
            "badges": {
                "enabled": self.rewards.badges.enabled,
                "milestone_badges": self.rewards.badges.milestone_badges,
                "special_badges": self.rewards.badges.special_badges
            }
        }
        
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "colors": self.colors.__dict__,
            "typography": self.typography.__dict__,
            "spacing": self.spacing.__dict__,
            "components": self.components.__dict__,
            "rewards": rewards_dict,
            "custom_css": self.custom_css,
            "preview_image": self.preview_image,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "downloads": self.downloads,
            "rating": self.rating
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Theme":
        """Create theme from dictionary."""
        theme = cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            author=data["author"],
            version=data.get("version", "1.0.0")
        )
        
        if "colors" in data:
            theme.colors = ThemeColors(**data["colors"])
        if "typography" in data:
            theme.typography = ThemeTypography(**data["typography"])
        if "spacing" in data:
            theme.spacing = ThemeSpacing(**data["spacing"])
        if "components" in data:
            theme.components = ThemeComponents(**data["components"])
        
        if "rewards" in data:
            rewards_data = data["rewards"]
            theme.rewards = ThemeRewards()
            
            # Set basic terminology
            for field in ["points_name", "points_abbreviation", "experience_name", 
                         "experience_abbreviation", "level_name", "quest_name", "task_name"]:
                if field in rewards_data:
                    setattr(theme.rewards, field, rewards_data[field])
            
            # Set point system
            if "point_system" in rewards_data:
                theme.rewards.point_system = RewardPoints(**rewards_data["point_system"])
            
            # Set decay config
            if "decay_config" in rewards_data:
                theme.rewards.decay_config = RewardDecay(**rewards_data["decay_config"])
            
            # Set task rewards
            if "task_rewards" in rewards_data:
                theme.rewards.task_rewards = rewards_data["task_rewards"]
            
            # Set multipliers
            for field in ["exceptional_multiplier", "team_multiplier", "streak_multiplier"]:
                if field in rewards_data:
                    setattr(theme.rewards, field, rewards_data[field])
            
            # Set visual indicators
            for field in ["show_points", "show_levels", "show_badges", "animated_rewards"]:
                if field in rewards_data:
                    setattr(theme.rewards, field, rewards_data[field])
            
            # Set badges
            if "badges" in rewards_data:
                badges_data = rewards_data["badges"]
                theme.rewards.badges = RewardBadges(
                    enabled=badges_data.get("enabled", True),
                    milestone_badges=badges_data.get("milestone_badges", 
                        {10: "Newcomer", 50: "Contributor", 100: "Active Member", 
                         500: "Community Leader", 1000: "Champion"}),
                    special_badges=badges_data.get("special_badges",
                        {"first_task": "Pioneer", "streak_7": "Week Warrior",
                         "helper": "Helping Hand", "quality": "Quality Champion"})
                )
        
        theme.custom_css = data.get("custom_css", "")
        theme.preview_image = data.get("preview_image")
        theme.tags = data.get("tags", [])
        theme.downloads = data.get("downloads", 0)
        theme.rating = data.get("rating", 0.0)
        
        return theme


# Built-in themes
THEMES = {
    "default": Theme(
        id="default",
        name="CivicForge Default",
        description="Clean and modern default theme",
        author="CivicForge Team",
        tags=["official", "modern", "clean"],
        rewards=ThemeRewards()  # Uses default rewards
    ),
    
    "earth": Theme(
        id="earth",
        name="Earth & Nature",
        description="Organic theme inspired by nature and environmental action",
        author="CivicForge Team",
        colors=ThemeColors(
            primary="#059669",  # Emerald
            secondary="#84cc16",  # Lime
            accent="#f59e0b",  # Amber
            background="#fefef8",
            surface="#f0fdf4",
            text="#064e3b",
            text_secondary="#059669"
        ),
        rewards=ThemeRewards(
            points_name="Green Points",
            points_abbreviation="GP",
            experience_name="Impact",
            quest_name="Mission",
            task_name="Action",
            point_system=RewardPoints(
                base_points=15,
                completion_bonus=10,
                quality_multiplier=2.0,
                collaboration_bonus=5
            ),
            task_rewards={
                "simple": 15,
                "moderate": 40,
                "complex": 80,
                "critical": 150
            },
            exceptional_multiplier=2.5,
            team_multiplier=1.5,
            decay_config=RewardDecay(enabled=False),  # No decay for environmental actions
            badges=RewardBadges(
                milestone_badges={
                    10: "Seedling",
                    50: "Sapling",
                    100: "Tree",
                    500: "Forest Guardian",
                    1000: "Earth Champion"
                },
                special_badges={
                    "first_task": "First Step",
                    "streak_7": "Weekly Warrior",
                    "helper": "Community Grower",
                    "quality": "Impact Leader"
                }
            )
        ),
        tags=["official", "nature", "environmental"]
    ),
    
    "community": Theme(
        id="community",
        name="Community Connect",
        description="Warm and welcoming theme for neighborhood boards",
        author="CivicForge Team",
        colors=ThemeColors(
            primary="#dc2626",  # Red
            secondary="#f97316",  # Orange
            accent="#fbbf24",  # Yellow
            background="#fffbeb",
            surface="#fef3c7",
            text="#7c2d12",
            text_secondary="#c2410c"
        ),
        tags=["official", "warm", "community"]
    ),
    
    "tech": Theme(
        id="tech",
        name="Tech Forward",
        description="Modern tech-inspired theme with dark mode",
        author="CivicForge Team",
        colors=ThemeColors(
            primary="#6366f1",  # Indigo
            secondary="#8b5cf6",  # Purple
            accent="#ec4899",  # Pink
            background="#0f172a",
            surface="#1e293b",
            text="#f1f5f9",
            text_secondary="#cbd5e1"
        ),
        tags=["official", "tech", "dark"]
    ),
    
    "civic": Theme(
        id="civic",
        name="Civic Pride",
        description="Professional theme for municipal and government boards",
        author="CivicForge Team",
        colors=ThemeColors(
            primary="#1e40af",  # Blue
            secondary="#0f766e",  # Teal
            accent="#dc2626",  # Red
            background="#ffffff",
            surface="#f8fafc",
            text="#0f172a",
            text_secondary="#475569"
        ),
        tags=["official", "professional", "government"]
    ),
    
    "gamified": Theme(
        id="gamified",
        name="Game On!",
        description="Highly gamified theme with RPG-style rewards",
        author="CivicForge Team",
        colors=ThemeColors(
            primary="#7c3aed",  # Purple
            secondary="#f59e0b",  # Amber
            accent="#ef4444",  # Red
            background="#1a1a2e",
            surface="#16213e",
            text="#eee",
            text_secondary="#aaa"
        ),
        rewards=ThemeRewards(
            points_name="Experience Points",
            points_abbreviation="XP",
            experience_name="Power Level",
            level_name="Rank",
            quest_name="Epic Quest",
            task_name="Challenge",
            point_system=RewardPoints(
                base_points=100,
                completion_bonus=50,
                quality_multiplier=3.0,
                speed_bonus=25,
                collaboration_bonus=30
            ),
            task_rewards={
                "simple": 100,
                "moderate": 250,
                "complex": 500,
                "critical": 1000
            },
            exceptional_multiplier=5.0,
            team_multiplier=2.0,
            streak_multiplier=1.5,
            decay_config=RewardDecay(
                enabled=True,
                rate_per_day=0.02,  # 2% decay
                minimum_retained=0.3,  # Keep 30%
                grace_period_days=3  # 3 day grace period
            ),
            show_points=True,
            show_levels=True,
            show_badges=True,
            animated_rewards=True,
            badges=RewardBadges(
                milestone_badges={
                    100: "Novice",
                    500: "Apprentice",
                    1000: "Journeyman",
                    5000: "Master",
                    10000: "Grandmaster",
                    50000: "Legend"
                },
                special_badges={
                    "first_task": "Fresh Start",
                    "streak_7": "Unstoppable",
                    "streak_30": "Marathon Master",
                    "helper": "Team Player",
                    "quality": "Perfectionist",
                    "speed": "Lightning Fast"
                }
            )
        ),
        tags=["official", "gamified", "fun", "dark"]
    )
}


class ThemeManager:
    """Manages themes for boards."""
    
    def __init__(self, themes_dir: str = "themes"):
        self.themes_dir = themes_dir
        self.themes_cache: Dict[str, Theme] = {}
        self._load_builtin_themes()
    
    def _load_builtin_themes(self):
        """Load built-in themes into cache."""
        self.themes_cache.update(THEMES)
    
    def get_theme(self, theme_id: str) -> Optional[Theme]:
        """Get a theme by ID."""
        # Check cache first
        if theme_id in self.themes_cache:
            return self.themes_cache[theme_id]
        
        # Try to load from file
        theme_file = os.path.join(self.themes_dir, f"{theme_id}.json")
        if os.path.exists(theme_file):
            with open(theme_file, 'r') as f:
                data = json.load(f)
                theme = Theme.from_dict(data)
                self.themes_cache[theme_id] = theme
                return theme
        
        return None
    
    def save_theme(self, theme: Theme):
        """Save a theme to file."""
        os.makedirs(self.themes_dir, exist_ok=True)
        theme_file = os.path.join(self.themes_dir, f"{theme.id}.json")
        
        with open(theme_file, 'w') as f:
            json.dump(theme.to_dict(), f, indent=2)
        
        self.themes_cache[theme.id] = theme
    
    def list_themes(self, tags: Optional[List[str]] = None) -> List[Theme]:
        """List all available themes, optionally filtered by tags."""
        themes = list(self.themes_cache.values())
        
        # Load themes from files
        if os.path.exists(self.themes_dir):
            for filename in os.listdir(self.themes_dir):
                if filename.endswith('.json'):
                    theme_id = filename[:-5]
                    if theme_id not in self.themes_cache:
                        theme = self.get_theme(theme_id)
                        if theme:
                            themes.append(theme)
        
        # Filter by tags if specified
        if tags:
            themes = [t for t in themes if any(tag in t.tags for tag in tags)]
        
        return sorted(themes, key=lambda t: (t.downloads, t.rating), reverse=True)
    
    def generate_theme_css(self, theme_id: str) -> str:
        """Generate complete CSS for a theme."""
        theme = self.get_theme(theme_id)
        if not theme:
            theme = THEMES["default"]
        
        base_css = """
/* Base styles using CSS variables */
* {
    box-sizing: border-box;
}

body {
    font-family: var(--font-family);
    font-size: var(--font-size-base);
    line-height: var(--line-height);
    color: var(--color-text);
    background-color: var(--color-background);
    margin: 0;
    padding: 0;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    line-height: 1.2;
    margin-top: 0;
    margin-bottom: var(--spacing-medium);
}

h1 { font-size: calc(var(--font-size-heading) * 1.5); }
h2 { font-size: calc(var(--font-size-heading) * 1.25); }
h3 { font-size: var(--font-size-heading); }

a {
    color: var(--color-primary);
    text-decoration: none;
    transition: var(--transition);
}

a:hover {
    text-decoration: underline;
}

/* Layout */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--spacing-large);
}

.nav {
    background: var(--color-surface);
    padding: var(--spacing-medium);
    margin-bottom: var(--spacing-large);
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-small);
}

/* Forms */
input, select, textarea, button {
    font-family: inherit;
    font-size: var(--font-size-base);
    padding: var(--spacing-small) var(--spacing-medium);
    border: var(--border-width) solid var(--color-surface);
    border-radius: var(--border-radius);
    background: var(--color-background);
    color: var(--color-text);
    transition: var(--transition);
}

input:focus, select:focus, textarea:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

button {
    background: var(--color-primary);
    color: white;
    border: none;
    cursor: pointer;
    font-weight: 500;
}

button:hover {
    background: color-mix(in srgb, var(--color-primary) 85%, black);
    transform: translateY(-1px);
    box-shadow: var(--shadow-medium);
}

button:active {
    transform: translateY(0);
}

/* Cards */
.quest {
    background: var(--color-surface);
    border-radius: var(--border-radius);
    padding: var(--spacing-large);
    margin-bottom: var(--spacing-medium);
    box-shadow: var(--shadow-small);
    transition: var(--transition);
}

.quest:hover {
    box-shadow: var(--shadow-medium);
}

/* Status indicators */
.error {
    color: var(--color-error);
    background: color-mix(in srgb, var(--color-error) 10%, transparent);
    padding: var(--spacing-small) var(--spacing-medium);
    border-radius: var(--border-radius);
    margin: var(--spacing-medium) 0;
}

.success {
    color: var(--color-success);
    background: color-mix(in srgb, var(--color-success) 10%, transparent);
    padding: var(--spacing-small) var(--spacing-medium);
    border-radius: var(--border-radius);
    margin: var(--spacing-medium) 0;
}

/* Theme switcher */
.theme-switcher {
    position: fixed;
    bottom: var(--spacing-large);
    right: var(--spacing-large);
    background: var(--color-surface);
    padding: var(--spacing-small);
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-large);
}
"""
        
        return theme.to_css_variables() + base_css + theme.custom_css


# Default theme manager instance
theme_manager = ThemeManager()