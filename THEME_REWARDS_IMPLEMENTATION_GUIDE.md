# Theme Rewards Implementation Guide

## Quick Start for Next Agent

The theme system with rewards is **already deployed and working** on AWS. Here's what you need to know:

### Current State
- ✅ Theme system extended with rewards configuration
- ✅ Deployed to AWS at http://YOUR_AWS_IP:8000
- ✅ API endpoints working
- ✅ 6 themes available with different reward systems
- ⚠️ Rewards are configured but not yet applied to quest actions

### What Works Now
```bash
# See all themes with their reward configs
curl http://YOUR_AWS_IP:8000/api/themes | jq

# Compare reward systems
curl http://YOUR_AWS_IP:8000/api/theme/default | jq '.rewards.points_name'    # "Civic Points"
curl http://YOUR_AWS_IP:8000/api/theme/gamified | jq '.rewards.points_name'   # "Experience Points"

# Check point values
curl http://YOUR_AWS_IP:8000/api/theme/default | jq '.rewards.task_rewards.complex'   # 50
curl http://YOUR_AWS_IP:8000/api/theme/gamified | jq '.rewards.task_rewards.complex'  # 500
```

## What Needs Implementation

### 1. Apply Rewards When Creating Quests
Currently, quest creation uses hardcoded `QUEST_CREATION_COST = 5`. Update to use theme rewards:

```python
# In api.py, update create_quest endpoint
theme = theme_manager.get_theme(user_theme_id)  # Get user's selected theme
cost = theme.rewards.task_rewards.get('simple', 10)  # Use theme's cost

# Deduct using theme's point name
if user_xp < cost:
    raise HTTPException(400, f"Insufficient {theme.rewards.points_abbreviation}")
```

### 2. Award Points Based on Theme
When completing quests, use theme's reward configuration:

```python
# In complete_quest endpoint
theme = theme_manager.get_theme(board_theme_id)
base_points = theme.rewards.task_rewards.get(quest.complexity, 'moderate')

# Apply multipliers
if exceptional_completion:
    base_points *= theme.rewards.exceptional_multiplier
if team_effort:
    base_points *= theme.rewards.team_multiplier
```

### 3. Update UI to Show Theme Terminology
Replace hardcoded "XP" with theme terminology:

```python
# In web templates
<span>{user_points} {theme.rewards.points_abbreviation}</span>
<div>Level {user_level} {theme.rewards.level_name}</div>
<h3>Available {theme.rewards.quest_name}s</h3>
```

### 4. Implement Point Decay
For themes with decay enabled:

```python
# Create a scheduled task or check on login
if theme.rewards.decay_config.enabled:
    days_inactive = (now - last_activity).days
    if days_inactive > theme.rewards.decay_config.grace_period_days:
        decay_rate = theme.rewards.decay_config.rate_per_day
        new_points = points * (1 - decay_rate) ** days_inactive
        new_points = max(new_points, points * theme.rewards.decay_config.minimum_retained)
```

### 5. Display Badges
Show earned badges based on theme configuration:

```python
# Check milestone badges
user_badges = []
for points_threshold, badge_name in theme.rewards.badges.milestone_badges.items():
    if user_points >= points_threshold:
        user_badges.append(badge_name)
```

## Code Structure

### Key Files to Modify

1. **`api.py`** - Update these endpoints:
   - `create_quest()` - Use theme-based costs
   - `complete_quest()` - Award theme-based points
   - `get_user_stats()` - Show points with theme terminology

2. **`web_themed.py`** - Update templates:
   - Quest cards to show theme-based rewards
   - User profile to display themed points/badges
   - Leaderboard with themed terminology

3. **`models.py`** - Consider adding:
   - `user_theme_preference` field
   - `board_default_theme` field
   - `last_activity_date` for decay calculation

### Database Considerations

The theme system uses file storage, but you'll need to track:
- User's selected theme (add to User model)
- Board's default theme (add to Board model)
- Point history for decay calculations

```sql
-- Suggested additions
ALTER TABLE users ADD COLUMN preferred_theme VARCHAR(50) DEFAULT 'default';
ALTER TABLE boards ADD COLUMN default_theme VARCHAR(50) DEFAULT 'default';
ALTER TABLE experience_transactions ADD COLUMN theme_id VARCHAR(50);
```

## Testing Your Implementation

1. **Test Different Themes**:
   ```bash
   # Create quest with default theme (5 XP cost)
   # Create quest with gamified theme (should be higher)
   ```

2. **Test Multipliers**:
   ```bash
   # Complete quest normally (base points)
   # Complete with team (base * team_multiplier)
   # Complete exceptionally (base * exceptional_multiplier)
   ```

3. **Test Decay**:
   ```bash
   # Set last_activity to 10 days ago
   # Login with gamified theme (should apply decay)
   # Login with earth theme (no decay)
   ```

## Migration Path

1. **Phase 1**: Display theme rewards in UI (read-only)
2. **Phase 2**: Apply rewards to new actions
3. **Phase 3**: Migrate existing points to themed system
4. **Phase 4**: Implement decay and badges

## AWS Deployment Notes

- Current deployment uses task definition version 16
- Version 18 has IAM issues - avoid for now
- Theme files persist in `/app/themes` directory
- No database changes needed for basic theme system

## Quick Win Implementation

For a quick demonstration, just update the quest creation to use theme points:

```python
# In api.py around line 200
@app.post("/quest", dependencies=[Depends(get_current_user)])
def create_quest(quest: QuestCreate, ...):
    # Add this
    user_theme = request.cookies.get('theme', 'default')
    theme = theme_manager.get_theme(user_theme)
    
    # Update cost message
    if user.experience_points < QUEST_CREATION_COST:
        raise HTTPException(400, 
            f"Insufficient {theme.rewards.points_name}. "
            f"Need {QUEST_CREATION_COST} {theme.rewards.points_abbreviation}")
```

This small change will immediately show users how themes affect the reward system!