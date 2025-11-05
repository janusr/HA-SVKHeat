# Commit Command

## Description
Analyzes git status, shows changed files, provides a summary, allows review, generates commit message, and pushes changes to remote repository.

## Command
```bash
# Analyze git status and show changed files
git status --porcelain

# Get change statistics
git diff --stat

# Stage all changes
git add -A

# Generate commit message based on changes and commit
git commit -m "Generated commit message"

# Push to remote repository
git push origin main
```

## Implementation
1. Check if we're in a git repository
2. Get project context (detect Home Assistant integration)
3. Analyze git status to show changed files
4. Provide summary of changes (files modified, insertions, deletions)
5. Generate appropriate commit message based on the changes:
   - Identify affected areas (components, file types)
   - Create contextual commit message for SVK heat pump integration
6. Allow user to review and edit the commit message
7. Check and update patch version if not already changed:
   - Read current version from manifest.json
   - Increment patch version if needed
   - Update version in manifest.json
8. Add changed files to git
9. Commit with the generated/approved message
10. Push changes to origin/main

## Project-Specific Logic
- Detects Home Assistant integration structure
- Identifies component changes (sensor, binary_sensor, number, etc.)
- Generates contextual commit messages like "Update sensor, binary_sensor: improve functionality and fix issues for SVK Heat Pump integration"
- Handles Python files, configuration files, and documentation appropriately
- Automatically updates the patch version in manifest.json if not already changed:
  - Checks if version field in manifest.json has been modified
  - If not, increments the patch version (x.y.z where z is incremented)
  - Stages the version update along with other changes

## User Interaction
- Shows colored output for different file statuses
- Displays change statistics
- Only prompt for permission and confirmation of final commit action
- Allows editing the commit message
- Provides clear feedback at each step