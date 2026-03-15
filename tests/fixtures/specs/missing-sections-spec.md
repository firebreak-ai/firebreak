# Notification Preferences Feature

## Problem

Users cannot control which notifications they receive, leading to alert
fatigue and reduced engagement with important updates.

## Goals

- Allow users to configure notification channels per event type.
- Provide sensible defaults for new accounts.

## User-facing behavior

A new "Notifications" tab in Settings displays a matrix of event types
and channels (email, push, in-app). Users toggle each cell to enable or
disable delivery. Changes save automatically with a debounced API call.

## Technical approach

Add a `notification_preferences` table with columns for user_id,
event_type, and channel. The API exposes GET/PUT endpoints at
`/api/v1/users/{id}/notification-preferences`. The frontend renders
the matrix using the existing ToggleGrid component.

## Acceptance criteria

- **AC-01**: Users can enable and disable notifications per channel.
- **AC-02**: Default preferences are applied to new accounts.
- **AC-03**: Changes persist across sessions.

## Dependencies

- Push notification service must support per-user channel routing.

## Open questions

- Should we allow granularity below event type (e.g., per-project)?
  Starting with event-type level keeps the UI simple and covers 80% of cases.
