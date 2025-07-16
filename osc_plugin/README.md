# osc-ld-plugin

This is an osc plugin that uses logdetective to analyze failed Open Build Service (OBS) builds or local build logs.

## Usage

### For analyzing local failed build
```bash
osc ld --local-log
```

### For analzying failed builds from OBS
```bash
osc ld --project openSUSE:Factory --package blender 