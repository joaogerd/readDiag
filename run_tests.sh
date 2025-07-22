#!/usr/bin/env bash
# run_tests.sh — executa pytest e informa se todos passaram

echo "Executando testes pytest..."
pytest -q --disable-warnings
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo ""
    echo "✅ Todos os testes passaram!"
    exit 0
else
    echo ""
    echo "❌ Alguns testes falharam."
    exit $RESULT
fi

