# Activity Monitor

This is an activity monitor for RoboFont. This works by:

1. Getting the time since the most recent interaction by the user with an input method (keyboard, mouse, etc.).
2. Getting the time since the most recent notification by all open fonts.

The monitor periodically posts `activity` event notifications that contain an info about the recent activity. Tools can subscribe to these event notifications with `mojo.events addObserver(observer, "callback", "activity")`. The info dictionary contains the following data:

| key | description |
| --- | ----------- |
| appIsActive| Boolean indicating if RoboFont is active. |
| fontActivity | Boolean indicating if there has been font activity since the previous `activity` notification. |
| sinceFontActivity | Seconds since the last font activity. |
| userActivity | Boolean indicating if there has been user activity since the previous `activity` notification. |
| sinceUserActivity | Seconds since the last user interaction. |
| fontNotifications | All font notifications since the previous `activity` notification. |

There is a settings window that allows you to modify how often the monitor polls for activity. The settings window also visually displays recent activity data.