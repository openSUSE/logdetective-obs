#!/usr/bin/env python3
# Based on https://github.com/TomasTomecek/logdetective-model-battleground/blob/main/run.py

import os
import asyncio
import sys
from dataclasses import make_dataclass

os.environ["LOGDETECTIVE_SERVER_CONF"] = "local-config.yaml"

from logdetective.server.gitlab import generate_mr_comment
from logdetective.server.llm import perform_staged_analysis


Job = make_dataclass("Job", ["id", "project_url", "project_name"])


async def main():
    if len(sys.argv) < 2:
        print("usage: gen-mr-comment.py LOG_FILE")
        sys.exit(1)

    file = sys.argv[1]
    log_url = "..."
    with open(file) as f:
        log_text = f.read()
    staged_response = await perform_staged_analysis(log_text=log_text)
    job = Job(id="1", project_url="https://gitlab.foobar.baz/", project_name="foo")
    short_comment = await generate_mr_comment(job, log_url, staged_response, full=True)
    print(short_comment)

asyncio.run(main())
