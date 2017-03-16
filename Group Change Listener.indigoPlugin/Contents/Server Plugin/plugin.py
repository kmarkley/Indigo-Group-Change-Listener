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
defaultProps = {
    'triggerVariables'  : [],
    'triggerDevices'    : [],
    'advanced'          : False,
    'filterLogic'       : "Ignore",
    'stateFilter'       : [],
    'commEnabled'       : False,
    'saveBool'          : False,
    'saveVar'           : "",
    }

################################################################################
class Plugin(indigo.PluginBase):
    #-------------------------------------------------------------------------------
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
    
    #-------------------------------------------------------------------------------
    def __del__(self):
        indigo.PluginBase.__del__(self)
    
    #-------------------------------------------------------------------------------
    # Start, Stop and Config changes
    #-------------------------------------------------------------------------------
    def startup(self):
        self.debug = self.pluginPrefs.get("showDebugInfo",False)
        self.logger.debug(u"startup")
        if self.debug:
            self.logger.debug("Debug logging enabled")
        self.triggersDict = dict()
        indigo.devices.subscribeToChanges()
        indigo.variables.subscribeToChanges()
    
    #-------------------------------------------------------------------------------
    def shutdown(self):
        self.logger.debug("shutdown")
        self.pluginPrefs['showDebugInfo'] = self.debug
    
    #-------------------------------------------------------------------------------
    def closedPrefsConfigUi (self, valuesDict, userCancelled):
        self.logger.debug("closedPrefsConfigUi")
        if not userCancelled:
            self.debug = valuesDict.get("showDebugInfo",False)
            if self.debug:
                self.logger.debug("Debug logging enabled")
    
    #-------------------------------------------------------------------------------
    def validateEventConfigUi(self, valuesDict, typeId, triggerId):
        self.logger.debug("validateTriggerConfigUi")
        errorsDict = indigo.Dict()
        
        if valuesDict.get('advanced',True):
            if (valuesDict.get('stateFilter',[])) and (not valuesDict.get('filterLogic',False)):
                errorsDict['filterLogic'] = "Required when state filters are defined"
            elif (not valuesDict.get('stateFilter',[])) and (valuesDict.get('filterLogic',"") == "Require"):
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
    
    #-------------------------------------------------------------------------------
    # Trigger Handlers
    #-------------------------------------------------------------------------------
    def triggerStartProcessing(self, trigger):
        self.logger.debug("triggerStartProcessing: "+trigger.name)
        if trigger.pluginProps.get('version','') != self.pluginVersion:
            self.updateTriggerVersion(trigger)
        self.triggersDict[trigger.id] = self.Listener(trigger, self)
    
    #-------------------------------------------------------------------------------
    def triggerStopProcessing(self, trigger):
        self.logger.debug("triggerStopProcessing: "+trigger.name)
        if trigger.id in self.triggersDict:
            del self.triggersDict[trigger.id]
    
    #-------------------------------------------------------------------------------
    def updateTriggerVersion(self, trigger):
        theProps = trigger.pluginProps
        
        for key in defaultProps:
            if key not in theProps:
                theProps[key] = defaultProps[key]
        
        # older versions stored 'stateFilter' as a string
        if isinstance(theProps.get('stateFilter',[]), basestring):
            theProps['stateFilter'] = theProps['stateFilter'].split()
            theProps['stateFilter'] = [s[:-1] if s[-1]=="," else s for s in theProps['stateFilter']]
                
        if theProps != trigger.pluginProps:
            trigger.replacePluginPropsOnServer(theProps)
    
    #-------------------------------------------------------------------------------
    # Variable or Device updated
    #-------------------------------------------------------------------------------
    def variableUpdated(self, oldVar, newVar):
        if newVar.value != oldVar.value:    # ignore property changes
            for tid, listener in self.triggersDict.items():
                if newVar.id in listener.varList:
                    self.logger.debug("variableUpdated: "+newVar.name)
                    listener.saveToVariable(newVar.name)
                    indigo.trigger.execute(tid)
    
    #-------------------------------------------------------------------------------
    def deviceUpdated(self, oldDev, newDev):
            for tid, listener in self.triggersDict.items():
                if newDev.id in listener.devList:
                    fireTrigger = False
                    
                    if listener.advanced:
                        for key in newDev.states:
                            if newDev.states[key] != oldDev.states.get(key,None):
                                if (listener.logic == "Ignore") and (key not in listener.filter):
                                    fireTrigger = True
                                    break
                                elif (listener.logic == "Require") and (key in listener.filter):
                                    fireTrigger = True
                                    break
                        if listener.comm:
                            if newDev.enabled != oldDev.enabled:
                                fireTrigger = True
                    else:
                        if newDev.states != oldDev.states:
                            fireTrigger = True
                    
                    if  fireTrigger:
                        self.logger.debug("deviceUpdated: "+newDev.name)
                        listener.saveToVariable(newDev.name)
                        indigo.trigger.execute(tid)
    
    
    #-------------------------------------------------------------------------------
    # Menu methods
    #-------------------------------------------------------------------------------
    def logTriggers(self):
        myTriggers = indigo.triggers.iter('self')
        if not myTriggers:
            self.logger.info("No triggers configured")
            return
        
        separator   = "".rjust(50,'-')
        width       = 10
        str_name_id = "{p:>{w}} {n} [{i}]".format
        str_missing = "{p:>{w}} [{i}] (missing)".format
        str_value   = "{p:>{w}} {v}".format
        
        self.logger.info("")
        self.logger.info("List all triggers:")
        self.logger.info(separator)
        for trigger in myTriggers:
            listener = self.Listener(trigger, self)
            
            self.logger.info(str_name_id(w=width, p="Trigger:", n=trigger.name, i=trigger.id))
            self.logger.info(str_value(w=width, p="Enabled:", v=trigger.enabled))
            
            prefix = "Variables:"
            for varId in listener.varList:
                try:
                    self.logger.info(str_name_id(w=width, p=prefix, n=indigo.variables[varId].name, i=varId))
                except:
                    self.logger.error(str_missing(w=width, p=prefix, i=varId))
                prefix = ""
            
            prefix = "Devices:"
            for devId in listener.devList:
                try:
                    self.logger.info(str_name_id(w=width, p=prefix, n=indigo.devices[devId].name, i=devId))
                except:
                    self.logger.error(str_missing(w=width, p=prefix, i=devId))
                prefix = ""
            
            if listener.advanced:
                self.logger.info(str_value(w=width, p="Logic:", v=listener.logic))
                prefix = "Filter:"
                for state in listener.filter:
                    self.logger.info(str_value(w=width, p=prefix, v=state))
                    prefix = ""
                self.logger.info(str_value(w=width, p="Status:", v=listener.comm))
            
            if listener.saveId:
                prefix = "Save To:"
                try:
                    var = indigo.variables[listener.saveId]
                    self.logger.info(str_name_id(w=width, p=prefix, n=var.name, i=var.id))
                except:
                    self.logger.error(str_missing(w=width, p=prefix, i=var.id))
            
            self.logger.info(separator)
        self.logger.info("")
    
    #-------------------------------------------------------------------------------
    def toggleDebug(self):
        if self.debug:
            self.logger.debug("Debug logging disabled")
            self.debug = False
        else:
            self.debug = True
            self.logger.debug("Debug logging enabled")
    
    #-------------------------------------------------------------------------------
    # Callbacks
    #-------------------------------------------------------------------------------
    def getStateList(self, filter=None, valuesDict=None, typeId='', targetId=0):
        stateList = []
        for devId in valuesDict.get('triggerDevices',[]):
            for state in indigo.devices[int(devId)].states:
                stateList.append((state,state))
        return sorted(set(stateList))
    
    #-------------------------------------------------------------------------------
    def loadStates(self, valuesDict=None, typeId='', targetId=0):
        pass
    
    
    ################################################################################
    # Classes
    ################################################################################
    class Listener(object):
        
        #-------------------------------------------------------------------------------
        def __init__(self, instance, plugin):
            self.trigger    = instance
            self.name       = instance.name
            
            self.plugin     = plugin
            self.logger     = plugin.logger
            
            self.saveId     = zint(instance.pluginProps.get('saveVar',0))
            self.advanced   = instance.pluginProps.get('advanced',True)
            self.filter     = instance.pluginProps.get('stateFilter',[])
            self.logic      = instance.pluginProps.get('filterLogic',"Ignore")
            self.comm       = instance.pluginProps.get('commEnabled',"False")

            self.devList = []
            for devId in instance.pluginProps.get('triggerDevices',[]):
                self.devList.append(int(devId))
            
            self.varList = []
            for varId in instance.pluginProps.get('triggerVariables',[]):
                self.varList.append(int(varId))
        
        #-------------------------------------------------------------------------------
        def saveToVariable(self, name):
            if self.saveId:
                try:
                    indigo.variable.updateValue(self.saveId, name)
                except:
                    self.logger.error("Trigger could not be saved to Indigo variable id '%s'. Does it exist?" % self.saveId)
            
################################################################################
# Utilities
################################################################################

def zint(value):
    try:
        return int(value)
    except:
        return 0
