from __future__ import division
import time
import re
import subprocess
from Foundation import NSObject, NSTimer
from AppKit import NSApp
from mojo.events import publishEvent
from mojo.events import addObserver, removeObserver
from mojo.roboFont import AllFonts
from activityMonitorDefaults import getDefaultPollingState, setDefaultPollingState, getDefaultPollingInterval, setDefaultPollingInterval

# -------
# Monitor
# -------

class ActivityPoller(NSObject):

    _timer = None
    _interval = getDefaultPollingInterval()
    _lastPoll = None

    def init(self):
        self = super(ActivityPoller, self).init()
        return self

    def _startTimer(self):
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            self._interval,
            self,
            "_timerCallback:",
            None,
            False
        )
        self._timer.setTolerance_(0.25)

    def _stopTimer(self):
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None

    def _timerCallback_(self, timer):
        idle = False
        # App activity
        app = NSApp()
        appIsActive = app.isActive()
        # Font activity
        sinceFontActivity = fontObserver.fontIdleTime()
        notifications = fontObserver.fontNotifications()
        # User activity
        sinceUserActivity = None
        if appIsActive:
            sinceUserActivity = userIdleTime()
        # Activity since last poll
        lastPoll = self._lastPoll
        userActivity = False
        fontActivity = False
        now = time.time()
        self._lastPoll = now
        if lastPoll is not None:
            sinceLastPoll = now - lastPoll
            fontActivity = sinceFontActivity < sinceLastPoll
            if sinceUserActivity is not None:
                userActivity = sinceUserActivity < sinceLastPoll
        # Pose
        info = dict(
            appIsActive=appIsActive,
            userActivity=userActivity,
            sinceUserActivity=sinceUserActivity,
            fontActivity=fontActivity,
            sinceFontActivity=sinceFontActivity,
            fontNotifications=notifications
        )
        self.postEventWithInfo_(info)
        # Restart
        if self.polling():
            self._startTimer()

    def polling(self):
        if self._timer is not None:
            return self._timer.isValid()
        else:
            return False

    def startPolling(self):
        fontObserver.startObserving()
        self._startTimer()

    def stopPolling(self):
        fontObserver.stopObserving()
        self._stopTimer()

    def setInterval_(self, value):
        self._interval = value
        if self.polling():
            self.stopPolling()
            self.startPolling()

    def postEventWithInfo_(self, info):
        publishEvent("activity", **info)


# -------------
# Font Observer
# -------------

class _FontObserver(object):

    _lastNotificationTime = None
    _notifications = []

    def fontIdleTime(self):
        if self._lastNotificationTime is None:
            return 0
        return time.time() - self._lastNotificationTime

    def fontNotifications(self):
        old = self._notifications
        self._notifications = []
        return old 

    def startObserving(self):
        self._lastNotificationTime = time.time()
        openEvents = [
            "newFontDidOpen",
            "fontDidOpen"
        ]
        for event in openEvents:
            addObserver(
                self,
                "_fontDidOpenEventCallback",
                event
            )
        addObserver(
            self,
            "_fontWillCloseEventCallback",
            "fontWillClose"
        )
        for font in AllFonts():
            self._fontDidOpenEventCallback(dict(font=font))

    def stopObserving(self):
        self._lastNotificationTime = None
        openEvents = [
            "newFontDidOpen",
            "fontDidOpen"
        ]
        for event in openEvents:
            removeObserver(
                self,
                event
            )
        removeObserver(
            self,
            "fontWillClose"
        )
        for font in AllFonts():
            self._fontWillCloseEventCallback(dict(font=font))

    # Event Callbacks

    def _fontDidOpenEventCallback(self, info):
        font = info["font"]
        font.addObserver(
            self,
            "_fontChangeNotificationCallback",
            "Font.Changed"
        )

    def _fontWillCloseEventCallback(self, info):
        font = info["font"]
        font.removeObserver(
            self,
            "Font.Changed"
        )

    # Font Callbacks

    def _fontChangeNotificationCallback(self, notification):
        self._lastNotificationTime = time.time()
        self._notifications.append(notification)


# ---------------------
# Idle Time Calculation
# ---------------------

idleTimePattern = re.compile("\"HIDIdleTime\"\s*=\s*(\d+)")
nanoToSec = 10 ** 9

def userIdleTime():
    # http://stackoverflow.com/questions/2425087/testing-for-inactivity-in-python-on-mac
    s = subprocess.Popen(
        ["ioreg", "-c", "IOHIDSystem"], stdout=subprocess.PIPE
    ).communicate()[0]
    times = idleTimePattern.findall(s)
    if not times:
        return 0
    times = [long(t) / nanoToSec for t in times]
    return min(times)


# Main

fontObserver = _FontObserver()
activityPoller = ActivityPoller.alloc().init()