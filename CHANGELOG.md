# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of iPhone Alarms Sync integration
- Sync iPhone/iPad alarms to Home Assistant
- Device registration and configuration flow
- Alarm state tracking (enabled/disabled)
- Alarm time sensors
- Repeat days sensors
- Device triggers (goes_off, snoozed, stopped)
- Alarm datetime sensors (next/last occurrence)
- Snooze time number entity
- Alarm ID sensor
- Device trigger labels and filtering
- iCloud shortcut integration with QR code
- Alarm event shortcuts support
- Wake-Up/Any services
- Sleep events support
- Sync disabled alarms option

### Changed
- Improved device registration flow
- Enhanced configuration form
- Refactored to single config entry architecture
- Multi-entry architecture support
- Improved sensor structure and organization
- Updated native_value properties to return datetime objects
- Improved alarm ID display and documentation
- Enhanced device configuration flow

### Fixed
- Fixed custom name input handling
- Fixed integration setup issues
- Fixed options flow errors
- Fixed device relation and registry API
- Fixed sensor unavailable states
- Fixed alarms sync functionality
- Fixed datetime timezone errors
- Fixed recursion in alarm event handlers
- Fixed snooze time display
- Fixed entity_description reference issues
- Fixed next alarm recalculation

### Documentation
- Added detailed iOS Shortcuts setup instructions
- Simplified shortcut setup documentation
- Added shortcut import instructions

### Removed
- Removed general .cursorrules file

---

*This changelog will be automatically updated on each release.*
