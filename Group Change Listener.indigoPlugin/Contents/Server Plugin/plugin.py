#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# http://www.indigodomo.com

import indigo

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.
###############################################################################
# globals

# used to warn user if triggers need updating on plugin upgrade
eventPropsKeys = [
    'triggerDevices',
    'filterLogic',
    'stateFilter',
    'triggerVariables',
    'saveBool',
    'saveVar',
    ]

################################################################################
class Plugin(indigo.PluginBase):
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
    
    ########################################
    def __del__(self):
        indigo.PluginBase.__del__(self)
    
    ########################################
    # Start, Stop and Config changes
    ########################################
    def startup(self):
        self.debug = self.pluginPrefs.get("showDebugInfo",False)
        self.logger.debug(u"startup")
        if self.debug:
            self.logger.debug("Debug logging enabled")
        self.triggersDict = dict()
        indigo.devices.subscribeToChanges()
        indigo.variables.subscribeToChanges()
    
    ########################################
    def shutdown(self):
        self.logger.debug("shutdown")
        self.pluginPrefs['showDebugInfo'] = self.debug
    
    ########################################
    def closedPrefsConfigUi (self, valuesDict, userCancelled):
        self.logger.debug("closedPrefsConfigUi")
        if not userCancelled:
            self.debug = valuesDict.get("showDebugInfo",False)
            if self.debug:
                self.logger.debug("Debug logging enabled")
    
    ########################################
    def validateEventConfigUi(self, valuesDict, typeId, triggerId):
        self.logger.debug("validateTriggerConfigUi")
        errorsDict = indigo.Dict()
        if (valuesDict.get('stateFilter',"")) and (not valuesDict.get('filterLogic',False)):
            errorsDict['filterLogic'] = "Required when state filters are defined"
        elif (not valuesDict.get('stateFilter',"")) and (valuesDict.get('filterLogic',"") == "Require"):
            errorsDict['stateFilter'] = "Required when filter logic is 'Require One'"
        if valuesDict.get('saveBool',False):
            if not valuesDict.get('saveVar',""):
                errorsDict['saveVar'] = "Required when 'Save to variable?' is checked"
            elif valuesDict.get('saveVar') in valuesDict.get('triggerVariables',[]):
                errorsDict['saveVar'] = "Can't save to a variable being monitored"
        if len(errorsDict) > 0:
            return (False, valuesDict, errorsDict)
        else:
            valuesDict['version'] = self.pluginVersion
            return (True, valuesDict)
    
    ########################################
    # Trigger handlers
    ########################################
    def triggerStartProcessing(self, trigger):
        self.logger.debug("triggerStartProcessing: "+trigger.name)
        theProps = trigger.pluginProps
        if theProps.get('version','') != self.pluginVersion:
            self.updateTriggerVersion(trigger)
        if theProps.get('saveBool',False):
            saveId = int(theProps.get('saveVar',0))
        else:
            saveId = 0
        devList = []
        for devId in theProps.get('triggerDevices',[]):
            devList.append(int(devId))
        varList = []
        for varId in theProps.get('triggerVariables',[]):
            varList.append(int(varId))
        filter = theProps.get('stateFilter',"").split()
        logic  = theProps.get('filterLogic',"Ignore")
        comm   = theProps.get('commEnabled',"False")
        self.triggersDict[trigger.id] = {'devs':devList, 'vars':varList, 'save':saveId, 'filter':filter, 'logic':logic, 'comm':comm}
    
    ########################################    
    def triggerStopProcessing(self, trigger):
        self.logger.debug("triggerStopProcessing: "+trigger.name)
        if trigger.id in self.triggersDict:
            del self.triggersDict[trigger.id]
    
    ########################################    
    def updateTriggerVersion(self, trigger):
        for key in eventPropsKeys:
            if key not in trigger.pluginProps:
                self.logger.error('Trigger "%s" obsolete (edit/save to update)' % trigger.name)
                break
    
    ########################################
    # Device or Variable updated
    ########################################
    def deviceUpdated(self, oldDev, newDev):
        for tid in self.triggersDict:
            if newDev.id in self.triggersDict[tid]['devs']:
                fireTrigger = False
                for key in newDev.states:
                    if newDev.states[key] != oldDev.states.get(key,None):
                        if (self.triggersDict[tid]['logic'] == "Ignore") and (key not in self.triggersDict[tid]['filter']):
                            fireTrigger = True
                            break
                        elif (self.triggersDict[tid]['logic'] == "Require") and (key in self.triggersDict[tid]['filter']):
                            fireTrigger = True
                            break
                if newDev.enabled != oldDev.enabled:
                    if self.triggersDict[tid]['comm']:
                        fireTrigger = True
                if  fireTrigger:
                    self.logger.debug("deviceUpdated: "+newDev.name)
                    self.saveTriggeringObject(tid, newDev.name)
                    indigo.trigger.execute(tid)
    
    ########################################
    def variableUpdated(self, oldVar, newVar):
        for tid in self.triggersDict:
            if newVar.id in self.triggersDict[tid]['vars']:
                if newVar.value != oldVar.value:
                    self.logger.debug("variableUpdated: "+newVar.name)
                    self.saveTriggeringObject(tid, newVar.name)
                    indigo.trigger.execute(tid)
    
    ########################################
    def saveTriggeringObject(self, tid, name):
        saveId = self.triggersDict[tid]['save']
        if saveId:
            try:
                indigo.variable.updateValue(saveId, name)
            except:
                self.logger.error("Trigger could not be saved to Indigo variable id '%s'. Does it exist?" % saveId)
    
    ########################################    
    # Menu methods
    ########################################        
    def logTriggers(self):
        separator = "".rjust(50,'-')
        justCount = 11
        myTriggers = indigo.triggers.iter('self')
        if not myTriggers:
            self.logger.info("No triggers configured")
            return
        self.logger.info("")
        self.logger.info("List all triggers:")
        self.logger.info(separator)
        for trigger in myTriggers:
            theProps = trigger.pluginProps
            self.logger.info("Trigger: ".rjust(justCount)+trigger.name+" ["+str(trigger.id)+"]")
            self.logger.info("Enabled: ".rjust(justCount)+str(trigger.enabled))
            if theProps.get('saveBool',False):
                try:
                    var = indigo.variables[int(theProps.get('saveVar',""))]
                    self.logger.info("Save To: ".rjust(justCount)+var.name+" ["+str(var.id)+"]")
                except:
                    self.logger.error("Save To: ".rjust(justCount)+"["+theProps.get('saveVar',"")+"] (missing)")
            prefix = "Devices: ".rjust(justCount)
            for devId in theProps.get('triggerDevices',[]):
                try:
                    self.logger.info(prefix+indigo.devices[int(devId)].name+" ["+devId+"]")
                except:
                    self.logger.error(prefix+"["+devId+"] (missing)")
                prefix = "".rjust(justCount)
            prefix = "Variables: ".rjust(justCount)
            for varId in theProps.get('triggerVariables',[]):
                try:
                    self.logger.info(prefix+indigo.variables[int(varId)].name+" ["+varId+"]")
                except:
                    self.logger.error(prefix+"["+varId+"] (missing)")
                prefix = "".rjust(justCount)
            if theProps.get('stateFilter',False):
                self.logger.info("Logic: ".rjust(justCount)+theProps.get('filterLogic',""))
            prefix = "Filter: ".rjust(justCount)
            for state in theProps.get('stateFilter',"").split():
                self.logger.info(prefix+state)
                prefix = "".rjust(justCount)
            if theProps.get('commEnabled',False):
                self.logger.info("Comm: ".rjust(justCount)+"True")
            self.logger.info(separator)
        self.logger.info("")
    
    ########################################        
    def toggleDebug(self):
        if self.debug:
            self.logger.debug("Debug logging disabled")
            self.debug = False
        else:
            self.debug = True
            self.logger.debug("Debug logging enabled")
    
