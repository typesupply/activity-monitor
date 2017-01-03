from mojo.extensions import getExtensionDefault, setExtensionDefault

try:
    from mojo.extensions import registerExtensionsDefaults
except ImportError:
    def registerExtensionsDefaults(d):
        for k, v in d.items():
            setExtensionDefault(k, v)

defaultKeyStub = "com.typesupply.ActivityMonitor."
defaultStateKey = defaultKeyStub + "poll"
defaultIntervalKey = defaultKeyStub + "interval"
defaults = {
    defaultStateKey : True,
    defaultIntervalKey : 2.0
}
registerExtensionsDefaults(defaults)

def getDefaultPollingState():
    return getExtensionDefault(defaultStateKey)

def setDefaultPollingState(value):
    setExtensionDefault(defaultStateKey, value)

def getDefaultPollingInterval():
    return getExtensionDefault(defaultIntervalKey)

def setDefaultPollingInterval(value):
    setExtensionDefault(defaultIntervalKey, value)