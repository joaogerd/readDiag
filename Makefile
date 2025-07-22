# Makefile para readDiag

# Roda todos os testes
test:
	pytest tests/

# Roda somente benchmarks
benchmark:
	pytest tests/test_benchmark.py --benchmark-only

# Lint com ruff e verificação com black
lint:
	ruff src/ tests/
	black --check src/ tests/

# Formata código com black
format:
	black src/ tests/

# Instala ambiente de desenvolvimento
install-dev:
	pip install -e .[dev]
