
prompt_template: |
  Analyze the RPM build log snippets below. Identify the failure, if any, and explain clearly.

  Format: [Snippet] : [Explanation]

  Use '=====' to separate snippets. Provide a summary explanation and possible fix at the end.

  Snippets:

  {}

  Analysis:

snippet_prompt_template: |
  Analyse following RPM build log snippet. Describe contents accurately, without speculation or suggestions for resolution.

  Your analysis must be as concise as possible, while keeping relevant information intact.

  Snippet:

  {}

  Analysis:

prompt_template_staged: |
  Given following log snippets, their explanation, and nothing else, explain what failure, if any, occurred during build of this package.

  Snippets are in a format of [X] : [Y], where [X] is a log snippet, and [Y] is the explanation.

  Snippets are delimited with '================'.

  Drawing on information from all snippets, provide a concise explanation of the issue and recommend a solution.

  Explanation of the issue, and recommended solution, should take a handful of sentences.

  Snippets:

  {}

  Analysis:

# System prompts
# System prompts are meant to serve as general guide for model behavior,
# describing role and purpose it is meant to serve.
# Sample system prompts in this file are intentionally the same,
# however, in some circumstances it may be beneficial have different
# system prompts for each sub case. For example when a specialized model is deployed
# to analyze snippets.

# Default prompt is used by the CLI tool and also for final analysis
# with /analyze and /analyze/stream API endpoints
default_system_prompt: |
  /no_think
  You are an RPM build log expert. Your task is to explain why RPM builds fail, with minimal words, no speculation, and no hallucinations.

  You must only use evidence from the logs.

# Snippet system prompt is used for analysis of individual snippets
snippet_system_prompt: |
  /no_think
  You are an RPM build log expert. Your task is to explain why RPM builds fail, with minimal words, no speculation, and no hallucinations.

  You must only use evidence from the logs.

# Staged system prompt is used by /analyze/staged API endpoint
staged_system_prompt: |
  /no_think
  You are an RPM build log expert. Your task is to explain why RPM builds fail, with minimal words, no speculation, and no hallucinations.

  You must only use evidence from the logs.
