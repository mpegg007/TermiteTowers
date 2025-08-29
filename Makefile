SHELL := /bin/bash

.PHONY: lint yaml compose-up compose-down test hooks

lint:
	@echo "Running shellcheck..." && \
	find . -type f \( -name "*.sh" -o -name "*.bash" -o -name "*.ksh" \) -print0 | xargs -0 -r shellcheck -S warning

yaml:
	@yamllint -c .yamllint.yml .

compose-up:
	@docker compose -f docker/openweb-dev1.yml up -d

compose-down:
	@docker compose -f docker/openweb-dev1.yml down

hooks:
	@echo "Installing pre-commit/post-commit wrappers" && \
	mkdir -p .git/hooks && \
	echo '#!/usr/bin/env bash' > .git/hooks/pre-commit && \
	echo '"$$(git rev-parse --show-toplevel)"/git-automation/update-keywords.sh' >> .git/hooks/pre-commit && \
	chmod +x .git/hooks/pre-commit && \
	echo '#!/usr/bin/env bash' > .git/hooks/post-commit && \
	echo '"$$(git rev-parse --show-toplevel)"/git-automation/post-commit-update-keywords.sh' >> .git/hooks/post-commit && \
	chmod +x .git/hooks/post-commit