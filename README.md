# Group Change Listener

This is a simple plugin that does exactly one thing:

***Creates triggers that fire when ANY of a selected group of Devices and/or Variables has ANY change.***

(More accurately, the trigger will fire when any of the devices' ***states*** or any of the variables' ***values*** change. Changes to properties will be ignored.)

Inspired by berkinet's "Group Trigger" plugin, but much less sophisticated.  
berkinet's plugins are here: http://forums.indigodomo.com/viewforum.php?f=22


### Background

It's pretty common to want indigo to take some action or track some status based on multiple 'inputs'.  As a simple example, I have a bug zapper that I want ON when this condition is met (and OFF otherwise):

`(not isRaining) AND (zapperScheduledHours OR ((houseMode == 'outside') AND (not isDaylight)))`

There are several approaches to deal with this.  The first is to create on and off triggers for every input, each with a long list of conditions for all the other inputs.  This can be a PITA to maintain.  A simpler approach is to create a one trigger for  each input (any change) and then have all the triggers execute the same action group that evaluates whether or not to take action.  Simplest of all is to use something like the Group Triggers plugin to create a single trigger that watches all the inputs.

I used Group Triggers for several things, but sometimes the way it segregates ON events and OFF events doesn't quite line up with the needed logic.  Similarly, only using devices and variables that are simply on/off or true/false is also a limitation.  

In the example above, I would first have to create a number of derivative variables and a set of triggers to update them, and then use Group Triggers to monitor these new variables.  At which point the advantage over other approaches is no longer clear.

This plugin solves this by providing a less sophisticated, and therefore somewhat more generic mechanism to determine when to re-evaluate the 'inputs'.

### How to Use
1. Create a new trigger:  
    Type: Group Change Listener Event  
    Event: Listener Group
2. Select zero or more Devices to monitor.
3. Optionally filter device states:   
    a. Filter Logic:  
    Ignore All: to ignore superfluous state changes.  
    Require One: to only consider changes from subset of states.
    b. State Filter: a space-separated list if state ID's.
3. Select zero or more Variables to monitor.
4. Optionally check the box and provide a variable to record the most recent triggering device/variable.
5. Configure the rest of the trigger as usual.

### Tips
* Use a little caution when selecting devices and variables to monitor.  The trigger will fire whenever any of them change, which can be quite frequently.
* Trigger actions can be anything, but the intended use case is short bits of python to evaluate whether or not to actually do something useful.  It might not be a good idea, for example, to send a bunch of insteon commands every time it triggers. Actions from the 'Super Conditions' plugin would be another good choice.
* A short (1 or 2 second) delay for the action is recommended.  It's common for devices to change several of their states in rapid succession, each of which gets reported to the plugin separately.  A delay ensures that the action is not executed until the dust settles.
