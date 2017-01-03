from __future__ import division
import time
import re
import subprocess
from Foundation import NSObject, NSTimer
from AppKit import *
import vanilla
from mojo.extensions import getExtensionDefault, setExtensionDefault, registerExtensionsDefaults
from mojo.events import publishEvent
from mojo.events import addObserver, removeObserver
from mojo.roboFont import AllFonts

# --------
# Defaults
# --------

defaultKeyStub = "com.typesupply.ActivityMonitor."
defaultStateKey = defaultKeyStub + "poll"
defaultIntervalKey = defaultKeyStub + "interval"
defaults = {
    defaultStateKey : True,
    defaultIntervalKey : 2.0
}
registerExtensionsDefaults(defaults)

def getDefaultPollingState():
    getExtensionDefault(defaultStateKey)

def setDefaultPollingState(value):
    setExtensionDefault(defaultStateKey, value)

def getDefaultPollingInterval():
    getExtensionDefault(defaultIntervalKey)

def setDefaultPollingInterval(value):
    setExtensionDefault(defaultIntervalKey, value)

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
        self._startTimer()

    def polling(self):
        return self._timer is not None

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


activityPoller = ActivityPoller.alloc().init()


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
            None
        )

    # Font Callbacks

    def _fontChangeNotificationCallback(self, notification):
        self._lastNotificationTime = time.time()
        self._notifications.append(notification)


fontObserver = _FontObserver()

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

# --------
# Settings
# --------

class ActivityPollerWindow(object):

    def __init__(self):
        self.pollQueue = []
        self.pollQueueLength = 100

        # Window

        self.w = vanilla.FloatingWindow((500, 400), "Activity Monitor")

        # Settings

        self.w.intervalTextBox1 = vanilla.TextBox((20, 21, 70, 17), "Poll every")
        self.w.intervalEditText = vanilla.EditText((90, 20, 50, 22), str(getDefaultPollingInterval()), callback=self.intervalEditTextCallback)
        self.w.intervalTextBox2 = vanilla.TextBox((148, 21, 62, 17), "seconds.")

        self.w.toggleStateButton = vanilla.Button((-150, 21, -20, 20), "Stop Polling", callback=self.toggleStateButtonCallback)

        # Graph

        self.w.activityGraphImageView = vanilla.ImageView((0, 60, -0, 100))

        # Notifications

        self.w.notificationsList = vanilla.List((0, 160, -0, -60), [])

        # Display Settings

        self.w.pollCountTextBox1 = vanilla.TextBox((20, -41, 98, 17), "Show data for")
        self.w.pollCountEditText = vanilla.EditText((118, -42, 50, 22), str(self.pollQueueLength), callback=self.pollCountEditTextCallback)
        self.w.pollCountTextBox2 = vanilla.TextBox((176, -41, 120, 17), "most recent polls.")

        self.w.clearButton = vanilla.Button((-150, -41, -20, 20), "Clear", self.clearButtonCallback)

        # Bootstrapping

        self.w.bind("close", self.closeWindowCallback)
        addObserver(
            self,
            "activityEventCallback",
            "activity"
        )
        if not getDefaultPollingState():
            self.toggleStateButtonCallback(self.w.toggleStateButton)
        self.updateActivityImage()
        self.w.open()

    def closeWindowCallback(self, window):
        removeObserver(
            self,
            "activity"
        )

    # Settings

    def intervalEditTextCallback(self, sender):
        value = sender.get()
        try:
            value = float(value)
            activityPoller.setInterval_(value)
            setDefaultPollingInterval(value)
        except ValueError:
            pass

    def toggleStateButtonCallback(self, sender):
        if activityPoller.polling():
            activityPoller.stopPolling()
            sender.setTitle("Start Polling")
            setDefaultPollingState(False)
        else:
            activityPoller.startPolling()
            sender.setTitle("Stop Polling")
            setDefaultPollingState(True)

    # Visualization

    def activityEventCallback(self, info):
        self.pollQueue.append(info)
        if len(self.pollQueue) > self.pollQueueLength:
            self.pollQueue.pop(0)
        self.updateActivityImage()
        self.updateNotificationsList()

    def updateActivityImage(self):
        w = 500.0
        h = 100.0
        maxFontNotifications = 10
        image = NSImage.alloc().initWithSize_((w, h))
        image.lockFocus()
        NSColor.blackColor().set()
        NSRectFill(((0, 0), (w, h)))
        xIncrement = w / self.pollQueueLength
        xIncrementHalf = xIncrement / 2.0
        yIncrement = h / maxFontNotifications
        activeColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.2, 0.8, 0.2, 1)
        idleColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.8, 0, 0, 1)
        path = NSBezierPath.bezierPath()
        x = 0
        for i, poll in enumerate(self.pollQueue):
            rect = ((x, 0), (xIncrement, h))
            if poll["userActivity"]:
                c = activeColor
            else:
                c = idleColor
            c.set()
            NSRectFill(rect)
            notifications = len(poll["fontNotifications"])
            if notifications > maxFontNotifications:
                notifications = maxFontNotifications
            y = yIncrement * notifications
            if i == 0:
                path.moveToPoint_((x + xIncrementHalf, y))
            path.lineToPoint_((x + xIncrementHalf, y))
            x += xIncrement
        NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 1, 1, 0.8).set()
        path.setLineWidth_(2)
        path.stroke()
        image.unlockFocus()
        self.w.activityGraphImageView.setImage(imageObject=image)

    def updateNotificationsList(self):
        contents = []
        for poll in reversed(self.pollQueue):
            for notification in reversed(poll["fontNotifications"]):
                line = " ".join((
                    notification.name,
                    str(id(notification.object)),
                    repr(notification.data)
                ))
                contents.append(line)
        self.w.notificationsList.set(contents)

    def pollCountEditTextCallback(self, sender):
        value = sender.get()
        try:
            value = int(value)
            restartPolling = activityPoller.polling()
            self.pollQueueLength = value
            if restartPolling:
                activityPoller.stopPolling()
            self.pollQueue = self.pollQueue[:-self.pollQueueLength]
            self.updateActivityImage()
            self.updateNotificationsList()
            if restartPolling:
                activityPoller.startPolling()
        except ValueError:
            pass

    def clearButtonCallback(self, sender):
        restartPolling = activityPoller.polling()
        if restartPolling:
            activityPoller.stopPolling()
        self.pollQueue = []
        if restartPolling:
            activityPoller.startPolling()


if __name__ == "__main__":
    if getDefaultPollingState():
        activityPoller.startPolling()
