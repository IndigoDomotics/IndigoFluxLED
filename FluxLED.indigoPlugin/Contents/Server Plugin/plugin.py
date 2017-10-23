
import indigo

import os
import sys
import signal
import Queue
import threading
import subprocess
import exceptions
import argparse
import socket
import time
import datetime
# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.
from flux_led import WifiLedBulb

class Plugin(indigo.PluginBase):
	########################################
	# Main Functions
	######################

	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.updatePrefs(pluginPrefs)
		self.runUpdateLoop = True

	def runConcurrentThread(self):
		self.debugLog(u"runConcurrentThread called")
		while self.runUpdateLoop:
			self.debugLog(u"runConcurrentThread loop")
			for	dev in indigo.devices.iter("self"):
				self.updateStatus(dev)

			self.sleep(3)

	
	def stopConcurrentThread(self):
		self.debugLog(u"stopConcurrentThread called")
		self.runUpdateLoop = False

	def updatePrefs(self, prefs):
		self.debug = prefs.get("showDebugInfo", False)


		if self.debug == True:
			self.debugLog("logger debugging enabled")
		else:
			self.debugLog("logger debugging disabled")
			
		
		
	def deviceStartComm(self, device):
		self.debugLog(u"Starting device: " + device.name)	
		self.updateStatus(device)

	def updateStatus(self, device):
		self.debugLog(u"Updating device: " + device.name)	
		
		try:
			keyValueList = []
			
			bulb = WifiLedBulb(device.address)
			keyValueList.append({'key':"online", 'value':True}) 
			currentRGBW = bulb.getRgbw()
			device.pluginProps["supportsWhite"] = bulb.rgbwcapable
			device.pluginProps["supportsWhiteTemperature"] = False
			self.debugLog(str(currentRGBW))
			channelKeys = []
			
			if bulb.rgbwcapable:
				channelKeys.extend(['whiteLevel'])
				
			keyValueList.append({'key':"onOffState", 'value':bulb.isOn()}) 
			keyValueList.append({'key':"redLevel", 'value':currentRGBW[0]}) 
			keyValueList.append({'key':"greenLevel", 'value':currentRGBW[1]})
			keyValueList.append({'key':"blueLevel", 'value':currentRGBW[2]})
			if bulb.rgbwcapable:
				keyValueList.append({'key':"whiteLevel", 'value':currentRGBW[3]})	

		
			

			device.updateStatesOnServer(keyValueList)
		except Exception,e:
			self.errorLog("Error updating device: " + device.name +". Is the IP address correct?")
		
		
		keyValueList = []
		
		bulb = WifiLedBulb(device.address)
		keyValueList.append({'key':"online", 'value':True}) 
		currentRGBW = bulb.getRgbw()
		device.pluginProps["supportsWhite"] = bulb.rgbwcapable
		device.pluginProps["supportsWhiteTemperature"] = False
		self.debugLog(str(currentRGBW))
		channelKeys = []
		
		if bulb.rgbwcapable:
			channelKeys.extend(['whiteLevel'])
			
		keyValueList.append({'key':"onOffState", 'value':bulb.isOn()}) 
		keyValueList.append({'key':"redLevel", 'value':currentRGBW[0]}) 
		keyValueList.append({'key':"greenLevel", 'value':currentRGBW[1]})
		keyValueList.append({'key':"blueLevel", 'value':currentRGBW[2]})
		if bulb.rgbwcapable:
			keyValueList.append({'key':"whiteLevel", 'value':currentRGBW[3]})	

	
		

		device.updateStatesOnServer(keyValueList)

	# Dimmer/Relay Control Actions
	########################################
	def actionControlDimmerRelay(self, action, device):
		try:
			self.debugLog(u"actionControlDimmerRelay called for device " + device.name + u". action: " + str(action) )
		except Exception, e:
			self.debugLog(u"actionControlDimmerRelay called for device " + device.name + u". (Unable to display action or device data due to error: " + str(e) + u")")
		
		currentBrightness = device.states['brightnessLevel']
		currentOnState = device.states['onOffState']

		bulb = WifiLedBulb(device.address)
		bulb.refreshState()
		self.debugLog(str(bulb))
		# Get key variables
		command = action.deviceAction
				##### TURN ON #####
		if command == indigo.kDeviceAction.TurnOn:
			try:
				self.debugLog(u"device on:\n%s" % action)
			except Exception, e:
				self.debugLog(u"device on: (Unable to display action data due to error: " + str(e) + u")")
			# Turn it on.
			bulb.turnOn()
			
			##### TURN OFF #####
		elif command == indigo.kDeviceAction.TurnOff:
			try:
				self.debugLog(u"device off:\n%s" % action)
			except Exception, e:
				self.debugLog(u"device off: (Unable to display action data due to error: " + str(e) + u")")
				# Turn it off by setting the brightness to minimum.
			bulb.turnOff()
		##### SET COLOR LEVELS #####
		elif command == indigo.kDimmerRelayAction.SetColorLevels:
			try:
				self.debugLog(u"device request status:\n%s" % action)
			except Exception, e:
				self.debugLog(u"device request status: (Unable to display action data due to error: " + str(e) + u")")
			
			actionColorVals = action.actionValue

			useRGB = False
			useHSB = False
			useColorTemp = False

			# The "Set RGBW Levels" action in Indigo 7.0 requires Red, Green, Blue and White leves, as well as
			#   White Temperature for devices that support both RGB and White levels (even if the device doesn't
			#   support simultaneous RGB and W settings).  We have to, therefor, make the assumption here that
			#   when the user sets the RGB and W levels all to 100 that they actually intend to use the White
			#   Temperature value for the action.  Alternatively, if they set the RGB levels to 100 but set a
			#   White level to something less than 100, we're assuming they intend to use the action to change
			#   the HSB saturation with the action and not RGB or color temperature.
			isGenericInterface = False
			if 'redLevel' in actionColorVals and 'greenLevel' in actionColorVals and 'blueLevel' in actionColorVals and 'whiteLevel' in actionColorVals and 'whiteTemperature' in actionColorVals:
				isGenericInterface = True
				bulb.set
				if actionColorVals['redLevel'] == 100.0 and actionColorVals['greenLevel'] == 100.0 and actionColorVals['blueLevel'] == 100.0:
					useHSB = True
					if actionColorVals['whiteLevel'] == 100.0:
						useHSB = False
						useColorTemp = True
				else:
					useRGB = True

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
						
						keyValueList.append({'key':channel, 'value':brightness})

		
			bulb.setRgbw(redLevel, greenLevel, blueLevel, whiteLevel)
		
		
			# Tell the Indigo Server to update the color level states:
			if len(keyValueList) > 0:
				device.updateStatesOnServer(keyValueList)
				
		##### REQUEST STATUS #####
		elif command == indigo.kDeviceAction.RequestStatus:
			try:
				self.debugLog(u"device request status:\n%s" % action)
			except Exception, e:
				self.debugLog(u"device request status: (Unable to display action data due to error: " + str(e) + u")")
			self.getBulbStatus(device.id)
			# Log the new brightnss.
			indigo.server.log(u"\"" + device.name + u"\" status request (received: " + str(device.states['brightnessLevel']) + u")", 'Sent Hue Lights')

		#### CATCH ALL #####
		else:
			indigo.server.log(u"Unhandled command \"%s\"" % (command))
		pass

	
	def deviceCreated(self, newDev):
		self.debugLog("Device Created")
				

	def deviceUpdated(self, origDev, newDev):
		# call the base's implementation first just to make sure all the right things happen elsewhere
		self.debugLog("Device Updated")
		indigo.PluginBase.deviceUpdated(self, origDev, newDev)
		

	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		# Since the dialog closed we want to set the debug flag - if you don't directly use
		# a plugin's properties (and for debugLog we don't) you'll want to translate it to
		# the appropriate stuff here. 

		if not userCancelled:
			self.updatePrefs(valuesDict)
