# osc-ld-plugin

This is an osc plugin that uses logdetective to analyze failed Open Build Service (OBS) builds or local build logs.

## Usage

To install the package run
```
pip install osc_ld_plugin
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