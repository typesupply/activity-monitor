from __future__ import division
import time
import re
import subprocess
from Foundation import NSObject, NSTimer
from AppKit import NSApp
from mojo.events import publishEvent
from mojo.events import addObserver, removeObserver
from mojo.roboFont import AllFonts

# --------
# Defaults
# --------

fallbackIdleThreshold = 2.0

def getDefaultMonitoringState():
    return True

def setDefaultMonitoringState(value):
    pass

def getDefaultMonitoringThreshold():
    return fallbackIdleThreshold

def setDefaultMonitoringThreshold(value):
    pass

# -------
# Monitor
# -------

class ActivityMonitor(NSObject):

    _timer = None
    _threshold = fallbackIdleThreshold

    def init(self):
        self = super(ActivityMonitor, self).init()
        return self

    def _startTimer(self):
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            self._threshold,
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
        app = NSApp()
        appIsActive = app.isActive()
        sinceFontActivity = fontObserver.fontIdleTime()
        sinceUserActivity = None
        idleTimes = [
            sinceFontActivity
        ]
        if appIsActive:
            sinceUserActivity = userIdleTime()
            idleTimes.append(sinceUserActivity)
        info = dict(
            appIsActive=appIsActive,
            sinceFontActivity=sinceFontActivity,
            sinceUserActivity=sinceUserActivity
        )
        if min(idleTimes) >= self._threshold:
            self.postIdleEventWithInfo_(info)
        else:
            self.postActiveEventWithInfo_(info)
        self._startTimer()

    def monitoring(self):
        return self._timer is not None

    def startMonitoring(self):
        fontObserver.startObserving()
        self._startTimer()

    def stopMonitoring(self):
        fontObserver.stopObserving()
        self._stopTimer()

    def setThreshold_(self, value):
        self._threshold = value
        if self.monitoring():
            self.stopMonitoring()
            self.startMonitoring()

    def postIdleEventWithInfo_(self, info):
        publishEvent("applicationIsIdle", **info)

    def postActiveEventWithInfo_(self, info):
        publishEvent("applicationIsActive", **info)


activityMonitor = ActivityMonitor.alloc().init()

# -------------
# Font Observer
# -------------

class _FontObserver(object):

    _lastNotificationTime = None

    def fontIdleTime(self):
        if self._lastNotification is None:
            return 0
        return time.time() - self._lastNotification

    def startObserving(self):
        self._lastNotification = time.time()
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
        self._lastNotification = None
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
        self._lastNotification = time.time()


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

from AppKit import NSColor
import vanilla

class ActivityMonitorSettingsWindow(object):

    def __init__(self):
        threshold = str(getDefaultMonitoringThreshold())
        self.w = vanilla.Window((250, 140), "Activity Monitor")
        self.w.stateIndicator = vanilla.ColorWell((0, 0, -0, 50))
        self.w.stateIndicator.enable(False)
        self.w.stateIndicator.getNSColorWell().setBordered_(False)
        self.w.thresholdTextBox1 = vanilla.TextBox((20, 67, -20, 17), "Check every")
        self.w.thresholdEditText = vanilla.EditText((110, 66, 50, 22), threshold, callback=self.thresholdEditTextCallback)
        self.w.thresholdTextBox2 = vanilla.TextBox((170, 67, -20, 17), "seconds.")
        self.w.toggleStateButton = vanilla.Button((20, 100, -20, 20), "Stop Monitoring", callback=self.toggleStateButtonCallback)
        self.w.bind("close", self.closeWindowCallback)
        addObserver(
            self,
            "activeEventCallback",
            "applicationIsActive"
        )
        addObserver(
            self,
            "idleEventCallback",
            "applicationIsIdle"
        )
        if getDefaultMonitoringState():
            self.activeEventCallback(None)
        else:
            self.toggleStateButtonCallback(self.w.toggleStateButton)
        self.w.open()

    def closeWindowCallback(self, window):
        removeObserver(
            self,
            "applicationIsActive"
        )
        removeObserver(
            self,
            "applicationIsIdle"
        )

    def activeEventCallback(self, info):
        self.w.stateIndicator.set(NSColor.greenColor())

    def idleEventCallback(self, info):
        self.w.stateIndicator.set(NSColor.redColor())

    def thresholdEditTextCallback(self, sender):
        value = sender.get()
        try:
            value = float(value)
            activityMonitor.setThreshold_(value)
            setDefaultMonitoringThreshold(value)
        except ValueError:
            pass

    def toggleStateButtonCallback(self, sender):
        if activityMonitor.monitoring():
            activityMonitor.stopMonitoring()
            sender.setTitle("Start Monitoring")
            self.w.stateIndicator.set(NSColor.grayColor())
            setDefaultMonitoringState(False)
        else:
            activityMonitor.startMonitoring()
            sender.setTitle("Stop Monitoring")
            self.w.stateIndicator.set(NSColor.greenColor())
            setDefaultMonitoringState(True)


if __name__ == "__main__":
    if getDefaultMonitoringState():
        activityMonitor.startMonitoring()
    ActivityMonitorSettingsWindow()
