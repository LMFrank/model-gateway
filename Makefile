.PHONY: help runtime-local runtime-local-stock runtime-docker runtime-docker-stock verify-runtime verify-runtime-stock verify-runtime-docker verify-runtime-docker-stock

help:
	@echo "Available runtime commands:"
	@echo "  make runtime-local               - Switch gateway to local runtime"
	@echo "  make runtime-local-stock         - Switch gateway to local runtime and recreate StockAgents"
	@echo "  make runtime-docker              - Switch gateway to docker runtime"
	@echo "  make runtime-docker-stock        - Switch gateway to docker runtime and recreate StockAgents"
	@echo "  make verify-runtime              - Verify local runtime"
	@echo "  make verify-runtime-stock        - Verify local runtime + StockAgents scenario"
	@echo "  make verify-runtime-docker       - Verify docker runtime"
	@echo "  make verify-runtime-docker-stock - Verify docker runtime + StockAgents scenario"

runtime-local:
	./scripts/release_runtime.sh --mode local

runtime-local-stock:
	./scripts/release_runtime.sh --mode local --with-stock

runtime-docker:
	./scripts/release_runtime.sh --mode docker

runtime-docker-stock:
	./scripts/release_runtime.sh --mode docker --with-stock

verify-runtime:
	./scripts/verify_runtime.sh --mode local

verify-runtime-stock:
	./scripts/verify_runtime.sh --mode local --with-stock

verify-runtime-docker:
	./scripts/verify_runtime.sh --mode docker

verify-runtime-docker-stock:
	./scripts/verify_runtime.sh --mode docker --with-stock
