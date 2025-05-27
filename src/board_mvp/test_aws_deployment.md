# CivicForge Theme System - AWS Testing Guide

## Deployment Status
- **URL**: http://YOUR_AWS_IP:8000
- **Status**: ✅ Deployed and Running
- **Health Check**: ✅ Healthy

## Testing the Theme System

### 1. Web Interface Testing

#### Main Application
- **Home Page**: http://YOUR_AWS_IP:8000
- **Login**: http://YOUR_AWS_IP:8000/login (use test/test or create new account)

#### Theme Features
- **Theme Gallery**: http://YOUR_AWS_IP:8000/themes
- **Theme Editor**: http://YOUR_AWS_IP:8000/editor (requires login)
- **Theme Switcher**: Available at bottom-right of any page

### 2. Available Themes

The system includes several built-in themes with different visual styles and reward configurations:

1. **Default Theme**
   - Standard civic points system
   - Clean, modern visual style
   - Points: Civic Points (CP)

2. **Earth & Nature Theme**
   - Environmental focus
   - Green color scheme
   - Points: Green Points (GP)
   - Special badges: Seedling → Earth Champion

3. **Gamified Theme**
   - RPG-style rewards
   - Dark mode visuals
   - Points: Experience Points (XP)
   - Point decay enabled
   - Extensive badge system

### 3. Testing Theme Features

#### A. Visual Theme Switching
1. Visit http://YOUR_AWS_IP:8000
2. Click the theme switcher (bottom-right)
3. Select different themes
4. Notice color and style changes

#### B. Creating Custom Themes
1. Login at http://YOUR_AWS_IP:8000/login
2. Visit http://YOUR_AWS_IP:8000/editor
3. Customize:
   - Visual elements (colors, fonts, spacing)
   - Rewards configuration (points, badges, multipliers)
   - Terminology (quest names, point names, etc.)
4. Save and test your theme

#### C. Rewards System Testing
Each theme has independent reward configurations:
- Point values for different task types
- Multipliers for exceptional performance
- Team collaboration bonuses
- Streak bonuses
- Optional point decay

### 4. API Testing

```bash
# List all themes
curl http://YOUR_AWS_IP:8000/api/themes

# Get specific theme
curl http://YOUR_AWS_IP:8000/api/theme/default
curl http://YOUR_AWS_IP:8000/api/theme/earth
curl http://YOUR_AWS_IP:8000/api/theme/gamified

# Check reward configuration
curl -s http://YOUR_AWS_IP:8000/api/theme/gamified | jq '.rewards'
```

### 5. Key Features to Test

- **Independent Visual/Reward Selection**: You can mix visual styles with different reward systems
- **Custom Terminology**: Each theme can rename points, quests, tasks, etc.
- **Point Calculations**: Different themes award different points for the same actions
- **Badge Systems**: Each theme has its own achievement badges
- **Decay Settings**: Some themes have point decay over time

### 6. Example Test Flow

1. Create an account
2. Browse available themes
3. Switch between themes and observe changes
4. Create a quest and see how points are displayed
5. Use the theme editor to create a custom theme
6. Mix a professional visual style with gamified rewards

## Notes

- The theme system is fully integrated with the board functionality
- Themes are stored persistently
- Users can create and share custom themes
- All theme settings are independent and can be mixed/matched