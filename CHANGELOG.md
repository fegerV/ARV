# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Video Playback Modes**: Implemented three playback modes for AR content videos:
  - **Manual Mode**: Fixed single video playback. User manually selects the active video.
  - **Sequential Mode**: Videos switch sequentially (1→2→3→...→last). Stops at the last video.
  - **Cyclic Mode**: Videos switch cyclically (1→2→3→...→1→2→...). Wraps around after the last video.
- **Automatic Video Rotation**: Videos automatically switch to the next one after the current video ends in AR viewer.
- **Playback Mode API Endpoint**: New endpoint `/api/videos/ar-content/{content_id}/playback-mode` for switching between playback modes.
- **Rotation State Management**: Automatic rotation state updates in viewer endpoints for sequential/cyclic modes.
- **UI Enhancements**: 
  - Playback mode selector with inline help text in AR content detail page
  - Green border highlight for active video
  - Improved video rotation controls

### Changed
- **Video Rotation Logic**: Updated rotation logic to properly handle sequential and cyclic modes:
  - Sequential mode: Returns current video based on rotation_state, stops at last video
  - Cyclic mode: Returns current video based on rotation_state, wraps around
- **AR Viewer**: Modified to disable video loop and automatically switch to next video after playback ends
- **Rotation State Updates**: Rotation state is now automatically incremented when viewer requests active video (for sequential/cyclic modes)

### Fixed
- **Rotation State Not Updating**: Fixed issue where rotation_state was not being updated when viewer requested active video
- **Sequential Mode Logic**: Fixed sequential mode to return current video instead of next video
- **Video Rotation Type**: Updated rotation_type values from (DAILY, WEEKLY, MONTHLY, CUSTOM) to (none, sequential, cyclic)

### Documentation
- Updated API.md with comprehensive documentation for playback modes
- Added examples for all three playback modes
- Updated Viewer API documentation with correct response format and rotation behavior

## [2.0.0] - Previous Release

### Features
- User management and authentication
- Company and project management
- AR content creation and management
- Media file storage and management
- AR marker generation (MindAR)
- Preview and thumbnail generation
- JWT authentication
- OAuth integrations
- API documentation (Swagger/OpenAPI)
- Docker containerization
- Automatic migrations
- Notification system
- Analytics and statistics
