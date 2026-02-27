VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

.PHONY: help venv install run run-app test freeze clean

help:
	@echo "make venv           -> crea el entorno virtual"
	@echo "make install        -> instala dependencias"
	@echo "make run            -> ejecuta run_query.py"
	@echo "make run-app        -> ejecuta app.py (usar ARGS='...')"
	@echo "make test           -> corre tests"
	@echo "make freeze         -> actualiza requirements.txt"
	@echo "make clean          -> elimina el entorno virtual"

venv:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install -r requirements.txt

run:
	PYTHONPATH=. $(PYTHON) -m src.query --pregunta $(ARGS)

test:
	PYTHONPATH=. $(PYTHON) -m pytest -v -s tests

freeze:
	$(PIP) freeze > requirements.txt

clean:
	rm -rf $(VENV)
