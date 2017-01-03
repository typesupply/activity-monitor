# Idle Monitor

This is an idle monitor for RoboFont. This works by:

1. Getting the time since the most recent interaction by the user with an input method (keyboard, mouse, etc.).
2. Getting the time since the most recent notification by all open fonts.

The first test only applies if the application is active. If the application is not active, it is condered idle unless a font notification indicates otherwise. When an idle state is detected, an `applicationIsIdle` event is posted as a RoboFont event that can be subscribed to with `mojo.events addObserver(observer, "callback", "applicationIsIdle")`. Likewise, when an active state is detected an `applicationIsActive` event is posted. Both events send along an info dictionary with the following data:

| key | description |
| --- | ----------- |
| appIsActive| Boolean indicating if RoboFont is active. |
| sinceAnyActivity | Seconds since the last activity. |
| sinceFontActivity | Seconds since the last font notification. |
| sinceUserActivity | Seconds since the last user interaction. |

There is a settings window that allows you to define how many seconds should pass before the application is declared idle. You can also disable the state testing altogether.