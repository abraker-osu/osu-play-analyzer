# osu! Performance Analyzer

### What is this?

This is a tool made figure out how BPM, note distance, and angle affect the ability to hit notes precisely. Set the settings, hit "Start", and it will automaticaly generate a map for you in your osu! folder and waits for a new play to be made. Once it detects a new play, it will update the data accordingly.

The data it plots is variance against BPM and Note distance. The lower the variance the more precise you were with the hits. You can also view how your hits are spread out by checking the "Show hits" option. This is great if you want to practice aim!

If more than 10% of the play are misses, it will reject the play. There might be some bugs with score processing, so don't hesitate to report any issues - just make sure to include a replay and settings with the report so I can debug it.

![](https://i.imgur.com/Ks4ZjIp.png)


### Setup

Run the scripts/setup.bat file

Add the following to .vscode/settings.json if linting is failing on libraries in venv/src:
```
"python.analysis.extraPaths": [
    "venv\\src",
]
```
