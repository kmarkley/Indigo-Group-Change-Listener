# Group Change Listener

This is a simple plugin that creates triggers that fire when any of a selected group of Devices and/or Variables has any change.  More accurately, the trigger will fire when any of the devices' ***states*** or any of the variables' ***values*** change. (Changes to properties will be ignored.)

The primary purpose is to reduce the number of triggers needed by 'listening' for changes to multiple devices/variables, and then use conditions or script actions to decide whether to actually do something useful.
