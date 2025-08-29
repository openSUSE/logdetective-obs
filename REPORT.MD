# GSoC 2025 Report  
**Researching integration for openSUSE with logdetective**  


## Overview  

This blog serves as a report for the work completed during my term as a mentee for **Google Summer of Code 2025** under the **openSUSE** organization.  

My name is **Aazam Thakur**, a recent engineering graduate (2025) majoring in **Artificial Intelligence and Data Science**. This was primarily a **research project**, to investigate various ways of integrating the logdetective model with the openSUSE/OBS workflow. Under the guidance of my mentor **Daniel Garcia**, I successfully completed this project: 

**“Logdetective for openSUSE/OBS.”**

```
3c11c8c06131:/ # osc ld -h
usage: osc [global opts] ld [-h] [--arch ARCH] [--package REGEX] [--show_excluded] [--local-log] [--strip-time]
                            [--offset OFFSET] [--no-display] [-r]

${cmd_name}: Run logdetective on failed OBS builds or local build log

This command finds all failed builds for the given PROJECT
(or processes the last local build), and runs logdetective
on each one by fetching the build log or using the local log.

${cmd_usage}
${cmd_option_list}

options:
  -h, --help       show this help message and exit
  --arch ARCH      Architecture to filter on (default: x86_64)
  --package REGEX  Regex to filter package names
  --show_excluded  Include excluded packages
  --local-log      Process the log of the newest last local build.
  --strip-time     (For --local-log) Remove timestamps from the local build log output when displaying.
  --offset OFFSET  (For --local-log) Start reading the local build log from a specific byte offset when
                   displaying.
  --no-display     (For --local-log) Do not display the local log content to stdout; just feed it to logdetective.
  -r, --remote     Use LogDetective remote API instead of requiring the CLI tool
```

## Observations  

- Logdetective model currently did not provide output explanations of failed build logs accurately.  
- It could provide a general overview of the error, but often the **exact error** causing the failure would be ignored.  
- Large log files reduced accuracy due to **context length limitations**.  
- Editing the prompt file gave **no significant improvements**.  

---

## Model Comparisons  

- **unsloth/Qwen2.5-Coder-7B-Instruct-128K-GGUF** gave the highest accuracy under 7B parameter restrictions.  
- Fine-tuned coding models yielded **better accuracy** compared to base models.  
- Lower parameter models → not enough context length.  
- Higher parameter models → more accurate but **too resource-heavy**.  

---

## Integration with openSUSE Workflow  

- Successful development of the **osc-ld plugin** (published on **PyPi**).  
- Potential integration methods:  
  - General Python script usable by anyone.  
  - osc plugin packaged for easy installation.  
  - Direct UI integration with logdetective website.  
  - Automated bot on Gitea, GitLab, etc.  

---

## Deliverables  

The following table illustrates the development progress:  

| Timeline | GitHub PR |
|----------|-----------|
| Week 1   | [Automating Log Collection from OBS](https://github.com/openSUSE/logdetective-obs/pull/1) |
| Week 2   | [Updated Script to add local model and subdirectory structure](https://github.com/openSUSE/logdetective-obs/pull/3) |
| Week 3   | [Add build logs for analysis](https://github.com/openSUSE/logdetective-obs/pull/4) |
| Week 4   | [Document instructions to use script](https://github.com/openSUSE/logdetective-obs/pull/5) |
| Week 5   | [Osc Plugin first version for logdetective](https://github.com/openSUSE/logdetective-obs/pull/6) |
| Week 6   | [Improve script to parse individual packages](https://github.com/openSUSE/logdetective-obs/pull/7) |
| Week 7   | [PyPi project for osc plugin](https://github.com/openSUSE/logdetective-obs/pull/8) |
| Week 8   | [Minor updates for the osc plugin](https://github.com/openSUSE/logdetective-obs/pull/9) |
| Week 9   | [Update documentation](https://github.com/openSUSE/logdetective-obs/pull/10) |
| Week 10  | [Investigate different models](https://github.com/openSUSE/logdetective-obs/pull/11) |
| Week 11  | [Update script to submit logs for training](https://github.com/openSUSE/logdetective-obs/pull/13) |
| Week 12  | [Update plugin to submit logs](https://github.com/openSUSE/logdetective-obs/pull/15) |

---

## Features  

The Python script and osc plugin allow:  

- Analyze build logs remotely using the **logdetective API**.  
- Analyze remote build logs directly from **open build service (OBS)**.  
- Submit failed build logs with their analysis to logdetective for **training**.  

---

## Future Scope  

- Develop an **automated bot** to review PRs and explain failed build logs.  
- Improve API response times (currently **5–15 mins vs ~1 min locally**).  
- Deploy an **openSUSE instance** with its own API for faster log analysis.  
- Possible **UI tab integration** in OBS & logdetective for direct log input.  

---

## Learning Outcomes  

- Discovered new topics in **LLM applications, fine-tuning, training, prompting**.  
- Tested multiple models and learned about **trade-offs between accuracy, speed, and resources**.  
- Gained experience in **creating & maintaining a PyPi project**.  
- Demonstrated practical applications of **LLMs for log analysis** to cut down debugging time.  

With AI adoption accelerating, **logdetective** can serve as a powerful tool to **boost developer productivity** by simplifying error identification.  
