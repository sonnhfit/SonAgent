# Standard Skills Auto-Copy Feature

## Overview

When the SonAgent starts, it automatically checks if the `user_data/skills/` directory contains any skill files. If the directory is empty, it copies standard skills from the `sonagent/standard_skills/` directory.

## How It Works

1. **Agent Initialization**: When `SkillsManager` is instantiated (during agent startup), it calls `copy_standard_skills_if_needed()`.

2. **Directory Check**: The method checks if `user_data/skills/` exists and creates it if needed.

3. **Skill Detection**: It scans for existing `.py` files (excluding `__init__.py`) in the skills directory.

4. **Conditional Copy**: 
   - If skills already exist → Skip copying (logs a message)
   - If directory is empty → Copy all standard skills from `sonagent/standard_skills/`

5. **Logging**: All operations are logged for debugging and monitoring.

## Standard Skills

The following standard skills are included:

- **TextPrinter**: Print text to the console
- **WeatherAPISkill**: Fetch weather information via API
- **HanoiWeatherChecker**: Check weather for Hanoi
- **SkillBuilder**: Dynamically generate new skills

## Benefits

- **Easy Onboarding**: New users get working examples immediately
- **No Manual Setup**: Skills are automatically available on first run
- **Customizable**: Users can modify or remove copied skills
- **Version Controlled**: Standard skills are stored in the repository
- **Safe**: Won't overwrite existing user skills

## File Structure

```
sonagent/
├── standard_skills/          # Source: Standard skill templates
│   ├── __init__.py
│   ├── TextPrinter.py
│   ├── WeatherAPISkill.py
│   ├── SkillBuilder.py
│   └── HanoiWeatherChecker.py
└── skills/
    └── skills_manager.py     # Contains copy logic

user_data/
└── skills/                   # Destination: User's skill directory
    ├── .gitkeep             # Preserves directory in git
    └── *.py                 # Skills copied on first run (gitignored)
```

## Developer Notes

- Standard skills are tracked in git at `sonagent/standard_skills/`
- User skills at `user_data/skills/*.py` are gitignored
- The `.gitkeep` file ensures the directory structure is preserved
- Skills are copied using `shutil.copy2()` to preserve metadata
- The copy only happens once when the directory is empty
