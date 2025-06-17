# logdetective-obs
OBS - Log detective integration tools

Repository to store documentation, scripts and tools for the
integration of [openSUSE openbuild
service](https://build.opensuse.org/) with
[log detective](https://log-detective.com).

The goal is to use and improve the LLM AI from Log Detective for
openSUSE packaging development. So we can have a simple plain text
explanation for build failures.

In the future, if the model is good enough we can even get some kind
of automated tools for categorization of build failures, or even get
some kind of automated request creation with easy fix.

### Features

- 🧾 Fetches all failed build logs for a given package from **OBS**
- 🧠 Optionally analyzes logs using the LogDetective model:
  - Run **locally** with the logdetective model.
  - Or use the hosted **LogDetective API**
- 📂 Organizes logs and explanations into structured subfolders by package name

## Installation

The following instructions have been tested on the latest opensuse:Tumbleweed.

Install the OBS command line tool `osc`
```
zypper in osc
```
Install the build-essentials
```
zypper install -y gcc gcc-c++ cmake # Install the compilers and CMake
```
Install the logdetective project using pip/pipx
```
pipx install logdetective
```
Then you can run the script file (eg. command)
```
python3 get-logs.py openSUSE:Factory -e
```

This repository is related to the
[2025 Google Summer of Code project](https://github.com/openSUSE/mentoring/issues/236)
