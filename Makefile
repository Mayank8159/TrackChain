# Developer targets: setup, dev, test, docker-up, ml-train, ml-evaluate.

.PHONY: help setup dev test lint format docker-up docker-down ml-train ml-evaluate

help:
	@echo "TrackChain Makefile Targets:"
	@echo "  setup        - Install JS/TS dependencies and configure Python venvs"
	@echo "  dev          - Launch full local development stack (app, backend)"
	@echo "  test         - Run tests across all packages"
	@echo "  docker-up    - Start TimescaleDB and MinIO containers"
	@echo "  docker-down  - Stop all local containers"
	@echo "  ml-train     - Run end-to-end ML model training pipeline"
	@echo "  ml-evaluate  - Run ML model evaluation and generate reports"

setup:
	powershell -ExecutionPolicy Bypass -File ./scripts/setup.ps1

dev:
	powershell -ExecutionPolicy Bypass -File ./scripts/dev.ps1

test:
	pnpm test
	pytest backend/tests ml/tests

docker-up:
	docker compose up -d

docker-down:
	docker compose down

ml-train:
	python ml/scripts/train_all.py

ml-evaluate:
	python ml/scripts/evaluate.py
