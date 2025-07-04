#!/bin/bash

HOST=localhost python3 -m llama_cpp.server --hf_model_repo_id fedora-copr/Mistral-7B-Instruct-v0.2-GGUF --model 'ggml-model-Q4_K_S.gguf' &

#podman run -it --rm -p 5432:5432 -e POSTGRES_PASSWORD=my-password -v /path/to/data:/var/lib/pgsql/data:Z registry.suse.com/suse/postgres:17 &
export POSTGRESQL_HOST=localhost
export POSTGRESQL_USER=postgres
export POSTGRESQL_PASSWORD=postgres
export POSTGRESQL_DATABASE=postgres
gunicorn -c gunicorn-dev.config.py logdetective.server.server:app


# python3 gen-mr-comment.py ../logs/openSUSE:Factory/python-celery:test_standard_x86_64.log
