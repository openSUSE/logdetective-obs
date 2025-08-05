This directory is an output comparision using different models with logdetective.

For this testing, we will assume the analysis on the failed apache-arrow build

We have also created a sample prompt file to further test the model performance.

The prompt.py file that has been provided can be run with the --prompt flag

The models can be used by passing the --model flag and then the -F flag to select the appropriate quantised file

### In order to use the qwen model run the following command
```
logdetective apache-arrow_standard_x86_64.log  --model unsloth/Qwen2.5-Coder-7B-Instruct-128K-GGUF -F Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf --prompt ~/prompt.yml
```