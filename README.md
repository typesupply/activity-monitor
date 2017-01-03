# Activity Monitor

This is an activity monitor for RoboFont. It is intended to be a building block for other tools that need computation time when the user is not actively engaged with RoboFont. The monitor periodically posts `activity` event notifications that contain an info dictionary about the recent activity. Tools can subscribe to these event notifications like so:

```python
from mojo.events import addObserver

addObserver(observer, "callback", "activity")
```

The info dictionary contains the following data:

| key | description |
| --- | ----------- |
| appIsActive| Boolean indicating if RoboFont is active. |
| fontActivity | Boolean indicating if there has been font activity since the previous `activity` notification. |
| sinceFontActivity | Seconds since the last font activity. |
| userActivity | Boolean indicating if there has been user activity since the previous `activity` notification. |
| sinceUserActivity | Seconds since the last user interaction. |
| fontNotifications | All font notifications since the previous `activity` notification. |

There is a settings window that allows you to modify how often the monitor polls for activity. The settings window also visually displays recent activity data.