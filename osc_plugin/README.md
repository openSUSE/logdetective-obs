# osc-ld-plugin

This is an osc plugin that uses logdetective to analyze failed Open Build Service (OBS) builds or local build logs.

## Usage instructions

To install the package run
```
pip install osc_ld_plugin
```

To install the package with logdetective run
```
pip install osc_ld_plugin[logdetective]
```

After installing this package, users must run
```
osc-ld-install
```
this is to install the osc plugin script in the ~/.osc-plugins directory

### For analyzing local failed build
```bash
osc ld --local-log
```

### For analzying failed builds from OBS
```bash
osc ld --project openSUSE:Factory --package blender
```

### For analyzing using the logdetective api instead
```bash
osc ld --project openSUSE:Factory --package blender -
```


## Changelog

### version 0.1.0
Initial version

### version 0.2.0
Added remote logdetective api functionality and optional dependency