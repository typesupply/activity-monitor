from activityMonitorCore import activityPoller
from activityMonitorDefaults import getDefaultPollingState

if getDefaultPollingState():
    activityPoller.startPolling()
