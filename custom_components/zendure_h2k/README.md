# Integration 101 Template

So this is your starting point into writing your first Home Assistant integration (or maybe just advancing your knowledge and improving something you have already written).

Well, firstly, I hope you enjoy doing it.  There is something very satisfying to be able to build something into Home Assistant that controls your devices!

So, below is a more detailed explanaition of the major building blocks demonstrated in this example.

If you get stuck, either post a forum question or an issue on this github repo and I'll try my best to help you.  As a note, it always helps if I can see your code, so please make sure you provide a link to that.

1. **Config Flow**

    This is the functionality to provide setup via the UI.  Many new starters to coding, start with a yaml config as it seems easier, but once you understand how to write a config flow (and it is quite simple), this is a much better way to setup and manage your integration from the start.

    See the config_flow.py file with comments to see how it works.  This is much enhanced from the scaffold version to include a reconfigure flow and options flow.

    It is possible (and quite simple) to do multi step flows, which will be covered in another later example.

2. **The DataUpdateCoordinator**

    To me, this should be a default for any integration that gets its data from an api (whether it be a pull (polling) or push type api). It provides much of the functionality to manage polling, receive a websocket message, process your data and update all your entities without you having to do much coding and ensures that all api code is ring fenced within this class.

3. **Devices**

    These are a nice way to group your entities that relate to the same physical device.  Again, this is often very confusing how to create these for an integration.  However, with simple explained code, this can be quite straight forward.

4. **Platform Entities**

    These are your sensors, switches, lights etc, and this example covers the 2 most simple ones of binary sensors, things that only have 2 states, ie On/Off or Open/Closed or Hot/Cold etc and sensors, things that can have many states ie temperature, power, luminance etc.

    There are within Home Assistant things called device classes that describe what your sensor is and set icons, units etc for it.
