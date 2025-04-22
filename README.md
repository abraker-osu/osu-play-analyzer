# osu! Performance Analyzer

### What is this?

This is a tool made for analyzing osu! standard gamemode difficulty and player performance.

![](https://abraker.s-ul.eu/YOiC9E13)


### Features

The analyzer has no concept of notes. Instead it operates on scorepoints, which are like slider aimpoints. It differentiates between press, hold, and release scorepoints.

#### Record replays as you play maps

The analyzer monitors your osu folder for new replays and loads them a few seconds after the result screen shows up. Save loaded plays to a *.h5 file to be able to analyze at a later time.

**NOTE: Make sure you are not overwriting an already loaded file by accidently playing while it's loaded**

#### Display replays

![](https://abraker.s-ul.eu/pcXBBpFP)

- Scroll through replays frame by frame
- Zoom in on precise moments
- See M1 / M2 button taps

#### Display cursor metrics

![](https://abraker.s-ul.eu/VnkOakG4)

See graphs of cursor positon, velocity, and acceleration

#### Multi-map pattern analysis

![](https://abraker.s-ul.eu/RuQt7u2n)

Shift-select or ctrl-select multiple plays in the listing for analysis. Filter out plays by time period using the range selector on bottom. The map composition overview displays maps' properties, graphed as a scatter plot for all selected maps:

- `CS` - Circle size of each scorepoint
- `AR` - Approach rate of each scorepoint
- `T_PRESS_DIFF` - Milliseconds between each press scorepoint timing
- `T_PRESS_RATE` - Milliseconds between 3 previous press timings of each press scorepoint
- `T_PRESS_INC` - Milliseconds since last increase in timing interval for a given press scorepoint
- `T_PRESS_DEC` - Milliseconds since last decrease in timing interval for a given press scorepoint
- `T_PRESS_RHM` - Press scorepoint's relative spacing compared to other presses scorepoints (in % t_1/(t_2 - t_0))
- `T_HOLD_DUR` - Milliseconds duration of between each press scorepoint and release scorepoints
- `T_OFFSET_SCR` - Player timing error on each press scorepoint
- `XY_DIST` - Distance between press or hold scorepoints
- `XY_ANGLE` - Angle formed between 3 press or hold scorepoints
- `XY_LIN_VEL` - Linear velocity between press or hold scorepoints
- `XY_ANG_VEL` - Angular velocity between press or hold scorepoints
- `XY_DIST_SRC` - Player distance error on each press scorepoint
- `VIS_VISIBLE` - Number of press scorepoints visible from each press scorepoint

Loading thousands of maps is possible. Several minutes of processing time need to be given when all 1000 maps are selected.

#### Load maps and replays and see hit errors

![](https://abraker.s-ul.eu/iT8F7Yp8)

**Note: This is based on analyzer's custom score processor. So it may not be 100% accurate to stable or lazer.**

#### Programmatically generate maps

![](https://abraker.s-ul.eu/2ZibkXS8)

- View generated maps in the map display window
- Ability to save maps to folder
- Generate many maps at a time

#### Graphs of interest (single play)

Analyze single plays. Right click on graphs to export *.csv.

![](https://abraker.s-ul.eu/vaewTngB)
![](https://abraker.s-ul.eu/ZhGsnmsx)
![](https://abraker.s-ul.eu/FGnUJMri)

#### Graphs of interest (multi play)

Analyze many plays made on a map. Right click on graphs to export *.csv

![](https://abraker.s-ul.eu/GzYM9JYU)

#### Hit distribution display



### Setup

#### Windows:
In cmd run the setup script. This will set up the python virtual environment as `venv_win` and install python libraries.
- `> scripts/setup.bat install` - To setup the project for osu_performance_analyzer development.
- `> scripts/setup.bat install all` - To install osu analysis libraries for development as well.

Add the following to .vscode/settings.json if linting is failing on libraries in venv/src:
```
"python.analysis.extraPaths": [
    "venv\\src",
]
```

#### Linux:
Install the following prerequisites:
- Needed for pyqt6 (debian):
  - `libxkbcommon-x11-0` `libxcb-cursor-dev` `libxcb-icccm4` `libxcb-keysyms1`
- Needed for pyqt6 (arch):
  - `xorg-xkbcommon` `xcb-util-cursor` `xcb-util-keysyms`
- Needed for pyinstaller and built binary metadata info setting
  - `binutils` `attr`
- Python prerequsites
  - `python` `python-virtualenv`

In cmd run the setup script. This will set up the python virtual environment as `venv_win` and install python libraries.
- `$ bash scripts/setup.bat install` - To setup the project for osu_performance_analyzer development.
- `$ bash scripts/setup.bat install all` - To install osu analysis libraries for development as well.

