# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.
from flux_led import WifiLedBulb
from colormath.color_objects import sRGBColor, xyYColor, HSVColor

class Plugin(indigo.PluginBase):
    ########################################
    # Main Functions
    ######################

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.updatePrefs(pluginPrefs)
        self.runUpdateLoop = True
        self.debug = False

    def runConcurrentThread(self):
        self.debugLog(u"runConcurrentThread called")
        while self.runUpdateLoop:
            # self.debugLog(u"runConcurrentThread loop")
            for dev in indigo.devices.iter("self"):
                self.updateStatus(dev)

            self.sleep(3)

    def stopConcurrentThread(self):
        self.debugLog(u"stopConcurrentThread called")
        self.runUpdateLoop = False

    def updatePrefs(self, prefs):
        self.debug = prefs.get("showDebugInfo", False)

        if self.debug:
            self.debugLog("logger debugging enabled")
        else:
            self.debugLog("logger debugging disabled")

    def deviceStartComm(self, device):
        self.debugLog(u"Starting device: " + device.name)
        self.updateStatus(device)

    def updateStatus(self, device):
        # self.debugLog(u"Updating device: " + device.name)

        try:
            keyValueList = []

            bulb = WifiLedBulb(device.address)
            keyValueList.append({'key': "online", 'value': True})
            currentRGBW = bulb.getRgbw()

            device.pluginProps["supportsWhite"] = bulb.rgbwcapable
            device.pluginProps["supportsWhiteTemperature"] = False
            # self.debugLog(str(currentRGBW))
            channelKeys = []

            if bulb.rgbwcapable:
                channelKeys.extend(['whiteLevel'])

            brightness = int(round(sRGBColor(currentRGBW[0], currentRGBW[1], currentRGBW[2]).convert_to('hsv').hsv_v * 100))

            keyValueList.append({'key': "onOffState", 'value': bulb.isOn()})
            keyValueList.append({'key': "redLevel", 'value': currentRGBW[0]})
            keyValueList.append({'key': "greenLevel", 'value': currentRGBW[1]})
            keyValueList.append({'key': "blueLevel", 'value': currentRGBW[2]})
            keyValueList.append({'key': 'brightnessLevel', 'value': brightness})
            if bulb.rgbwcapable:
                keyValueList.append({'key': "whiteLevel", 'value': currentRGBW[3]})

            device.updateStatesOnServer(keyValueList)
        except Exception as e:
            self.errorLog(f"Error updating device: {device.name}. Is the IP address correct: {device.address}?")

        keyValueList = []

        bulb = WifiLedBulb(device.address, timeout=20)
        keyValueList.append({'key': "online", 'value': True})
        currentRGBW = bulb.getRgbw()
        device.pluginProps["supportsWhite"] = bulb.rgbwcapable
        device.pluginProps["supportsWhiteTemperature"] = False
        # self.debugLog(str(currentRGBW))
        channelKeys = []

        if bulb.rgbwcapable:
            channelKeys.extend(['whiteLevel'])

        keyValueList.append({'key': "onOffState", 'value': bulb.isOn()})
        keyValueList.append({'key': "redLevel", 'value': currentRGBW[0]})
        keyValueList.append({'key': "greenLevel", 'value': currentRGBW[1]})
        keyValueList.append({'key': "blueLevel", 'value': currentRGBW[2]})
        if bulb.rgbwcapable:
            keyValueList.append({'key': "whiteLevel", 'value': currentRGBW[3]})

        device.updateStatesOnServer(keyValueList)

    def rgbColorPickerUpdated(self, valuesDict, typeId, devId):
        self.debugLog(u"Starting rgbColorPickerUpdated.")
        self.debugLog(f"typeId: {typeId}, devId: {devId}, valuesDict: {valuesDict}")
        # Get the raw 3 byte, space-separated hex string from the color picker.
        rgbHexList = valuesDict['rgbColor'].split()
        # Assign the RGB values.
        red = int(rgbHexList[0], 16)
        green = int(rgbHexList[1], 16)
        blue = int(rgbHexList[2], 16)
        # Convert the RGB values to HSL/HSV for use in the HSB actions.
        rgb = sRGBColor(red, green, blue, rgb_type='wide_gamut_rgb')
        hsb = rgb.convert_to('hsv')
        hue = int(round(hsb.hsv_h * 1.0))
        saturation = int(round(hsb.hsv_s * 100.0))
        brightness = int(round(hsb.hsv_v * 100.0))

        # Assign the values to the appropriate valuesDict items.
        valuesDict['red'] = red
        valuesDict['green'] = green
        valuesDict['blue'] = blue
        valuesDict['hue'] = hue
        valuesDict['saturation'] = saturation
        valuesDict['brightness'] = brightness

        # Can send a live update to the hardware here:
        #    self.sendSetRGBWCommand(valuesDict, typeId, devId)

        del valuesDict['rgbColor']
        return valuesDict

    def rgbColorFieldUpdated(self, valuesDict, typeId, devId):
        self.debugLog(u"Starting rgbColorFieldUpdated.")
        self.debugLog(f"typeId: {typeId}, devId: {devId}, valuesDict: {valuesDict}")
        valuesDict['rgbColor'] = self.calcRgbHexValsFromRgbLevels(valuesDict)

        # Can send a live update to the hardware here:
        #    self.sendSetRGBWCommand(valuesDict, typeId, devId)

        del valuesDict['red']
        del valuesDict['green']
        del valuesDict['blue']
        return valuesDict

    # Set RGB Level Action
    ########################################
    def setRGB(self, action, device):
        self.debugLog(f"setRGB: device: {device.name}, action: {action}")

        red = action.props.get('red', 0)
        green = action.props.get('green', 0)
        blue = action.props.get('blue', 0)
        bulb = WifiLedBulb(device.address, timeout=20)
        # bulb.mode = 'color'
        bulb.pattern_code = 0x61

        if red + green + blue > 0:
            bulb.turnOn()
        bulb.setRgb(red, green, blue)

    # Set Preset Action
    ########################################
    def setPreset(self, action, device):
        self.debugLog(f"setPreset: device: {device.name }, action: {action}")

        preset = int(action.props.get('preset', 0), 0)
        speed = int(action.props.get('speed', 0), 0)

        bulb = WifiLedBulb(device.address)
        bulb.refreshState()

        bulb.setPresetPattern(preset, speed)
        bulb.turnOn()

    # Dimmer/Relay Control Actions
    ########################################
    def actionControlDimmerRelay(self, action, device):
        try:
            self.debugLog(u"actionControlDimmerRelay called for device " + device.name + u". actionValue: " + str(action))
        except Exception as e:
            self.debugLog(
                u"actionControlDimmerRelay called for device " + device.name + u". (Unable to display action or device data due to error: " + str(
                    e) + u")")

        currentBrightness = device.states['brightnessLevel']
        currentOnState = device.states['onOffState']
        self.debugLog("current brightness: " + str(currentBrightness))
        bulb = WifiLedBulb(device.address)
        bulb.refreshState()
        self.debugLog(str(bulb))
        # Get key variables
        command = action.deviceAction
        if command == indigo.kDeviceAction.TurnOn:
            self.debugLog(u"device on:\n%s" % action)
            bulb.turnOn()

        elif command == indigo.kDeviceAction.TurnOff:
            self.debugLog(u"device off:\n%s" % action)
            bulb.turnOff()

        elif command == indigo.kDimmerRelayAction.SetColorLevels:
            self.debugLog(u"device set color levels:\n%s" % action)

            actionColorVals = action.actionValue

            useRGB = False
            useHSB = False
            useColorTemp = False

            # The "Set RGBW Levels" action in Indigo 7.0 requires Red, Green, Blue and White levels, as well as
            #   White Temperature for devices that support both RGB and White levels (even if the device doesn't
            #   support simultaneous RGB and W settings).  We have to, therefor, make the assumption here that
            #   when the user sets the RGB and W levels all to 100 that they actually intend to use the White
            #   Temperature value for the action.  Alternatively, if they set the RGB levels to 100 but set a
            #   White level to something less than 100, we're assuming they intend to use the action to change
            #   the HSB saturation with the action and not RGB or color temperature.
            isGenericInterface = False
            if 'redLevel' in actionColorVals and 'greenLevel' in actionColorVals and 'blueLevel' in actionColorVals and 'whiteLevel' in actionColorVals and 'whiteTemperature' in actionColorVals:
                isGenericInterface = True
                self.debugLog(u"Generic Interface.")
                if actionColorVals['redLevel'] == 100.0 and actionColorVals['greenLevel'] == 100.0 and actionColorVals['blueLevel'] == 100.0:
                    useHSB = True
                    if actionColorVals['whiteLevel'] == 100.0:
                        useHSB = False
                        useColorTemp = True
                else:
                    useRGB = True

            self.debugLog(u"Use RGB:" + str(useRGB))
            self.debugLog(u"Use HSB:" + str(useHSB))
            # Construct a list of channel keys that are possible for what this device
            # supports. It may not support RGB or may not support white levels, for
            # example, depending on how the device's properties (SupportsColor, SupportsRGB,
            # SupportsWhite, SupportsTwoWhiteLevels, SupportsWhiteTemperature) have
            # been specified.
            channelKeys = []
            if device.supportsRGB:
                channelKeys.extend(['redLevel', 'greenLevel', 'blueLevel'])
            if device.supportsWhite:
                channelKeys.extend(['whiteLevel'])

            elif device.supportsWhiteTemperature:
                channelKeys.extend(['whiteTemperature'])
            redLevel = 0
            greenLevel = 0
            blueLevel = 0
            whiteLevel = 0
            colorTemp = 0

            # Enumerate through the possible color channels and extract each
            # value from the actionValue (actionColorVals).
            keyValueList = []
            for channel in channelKeys:
                if channel in actionColorVals:
                    brightness = float(actionColorVals[channel])
                    brightnessByte = int(round(255.0 * (brightness / 100.0)))

                    if channel in device.states:
                        if channel == "redLevel":
                            redLevel = brightnessByte
                        elif channel == "greenLevel":
                            greenLevel = brightnessByte
                        elif channel == "blueLevel":
                            blueLevel = brightnessByte
                        elif channel == "whiteLevel":
                            whiteLevel = brightnessByte
                        elif channel == "whiteTemperature":
                            if brightness > 6500.0:
                                brightness = 6500.0
                            if brightness < 2000.0:
                                brightness = 2000.0
                            colorTemp = brightness

                        keyValueList.append({'key': channel, 'value': brightness})

            self.debugLog(u"Setting RGBW: " + str(redLevel) + "|" + str(greenLevel) + "|" + str(blueLevel) + "|" + str(whiteLevel))

#            bulb.mode = 'color'
            bulb.setRgbw(redLevel, greenLevel, blueLevel, whiteLevel)

            # Tell the Indigo Server to update the color level states:
            if len(keyValueList) > 0:
                device.updateStatesOnServer(keyValueList)

        elif command == indigo.kDeviceAction.RequestStatus:
            self.debugLog(u"device request status:\n%s" % action)
            self.getBulbStatus(device.id)
            # Log the new brightness.
            indigo.server.log(u"\"" + device.name + u"\" status request (received: " + str(device.states['brightnessLevel']) + u")")
        elif command == indigo.kDimmerRelayAction.SetBrightness:
            self.debugLog(u"SetBrightness:")
            self.setBrightness(action, device)

        else:
            indigo.server.log(u"Unhandled command \"%s\"" % command)
        pass

    def getBulbStatus(self, deviceId):
        # Get device status.

        device = indigo.devices[deviceId]
        bulb = WifiLedBulb(device.address)
        bulb.refreshState()
        self.debugLog(str(bulb))

    def deviceCreated(self, newDev):
        self.debugLog("Device Created")

    # Set Brightness
    ########################################
    def setBrightness(self, action, device):
        self.debugLog(f"setBrightness: device: {device.name}, action: {action}")
        bulb = WifiLedBulb(device.address)
        bulb.refreshState()

        # get RGB
        rgb = bulb.getRgb()
        self.debugLog("RGB Read as: " + str(rgb))
        r = rgb[0]
        g = rgb[1]
        b = rgb[2]
        # Convert RGB to HSV
        # hsb = RGBColor(red, green, blue, rgb_type='wide_gamut_rgb').convert_to('hsv')
        # hue = int(round(hsb.hsv_h * 1.0))
        # saturation = int(round(hsb.hsv_s * 100.0))
        # brightness = int(round(hsb.hsv_v * 100.0))
        # Change V

        # Update bulb
        self.debugLog(u"Setting RGB: " + str(r) + "|" + str(g) + "|" + str(b))

        bulb.setRgb(r, g, b, True, action.actionValue * 2.55)

    def deviceUpdated(self, origDev, newDev):
        # call the base's implementation first just to make sure all the right things happen elsewhere
        # self.debugLog("Device Updated")
        indigo.PluginBase.deviceUpdated(self, origDev, newDev)

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        # Since the dialog closed we want to set the debug flag - if you don't directly use
        # a plugin's properties (and for debugLog we don't) you'll want to translate it to
        # the appropriate stuff here.

        if not userCancelled:
            self.updatePrefs(valuesDict)
