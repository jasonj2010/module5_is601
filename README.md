# 🧮 Advanced Modular Calculator (Module 5 – IS601)

![Python application](https://github.com/jasonj2010/module5_is601/actions/workflows/python-app.yml/badge.svg)

A fully modular, object-oriented Python calculator demonstrating advanced design patterns, persistent history via pandas, robust error handling, and automated testing with CI.

---

## ✨ Features

- **REPL Interface** – Interactive Read–Eval–Print loop  
- **Operations** – add, subtract, multiply, divide, power, root  
- **Design Patterns**
  - **Factory** – build operations from user input
  - **Strategy** – interchangeable operation algorithms
  - **Observer** – logging & auto-save hooks
  - **Memento** – undo/redo stack
  - **Facade** – simplified access to subsystems
- **Persistent History** – pandas DataFrame ↔ CSV  
- **Config via `.env`** – managed with `python-dotenv`  
- **Testing & CI** – `pytest` + coverage + GitHub Actions  
- **Windows-friendly logging** – avoids locked log files during tests

---

## 🧱 Project Structure

    app/
      calculation.py
      calculator.py
      calculator_config.py
      calculator_memento.py
      calculator_repl.py
      exceptions.py
      history.py
      input_validators.py
      operations.py
    tests/
      test_calculation.py
      test_calculator.py
      test_config.py
      test_exceptions.py
      test_history.py
      test_input_validators.py
      test_operations.py
    .coveragerc
    pytest.ini
    requirements.txt
    .github/workflows/python-app.yml
    main.py
    README.md

---

## ⚙️ Setup

### 1) Clone and enter the repo
    git clone git@github.com:jasonj2010/module5_is601.git
    cd module5_is601

### 2) Create & activate a virtual environment
**Windows (Git Bash)**
    
    python -m venv venv
    source venv/Scripts/activate

**Windows (PowerShell)**
    
    python -m venv venv
    .\venv\Scripts\Activate.ps1

**macOS / Linux**
    
    python3 -m venv venv
    source venv/bin/activate

### 3) Install dependencies
    
    pip install -r requirements.txt

### 4) Create `.env` (defaults shown)
    
    printf "CALCULATOR_MAX_HISTORY_SIZE=100\nCALCULATOR_AUTO_SAVE=true\nCALCULATOR_DEFAULT_ENCODING=utf-8\n" > .env

---

## ▶️ Run the App (REPL)

    python main.py

Example session:

    Calculator started. Type 'help' for commands.
    
    Enter command: add 5 10
    Result: 15.0
    Enter command: history
    Addition(5, 10) = 15.0
    Enter command: exit
    History saved successfully.
    Goodbye!

**Supported commands**
- `help` – list commands  
- `add a b`, `subtract a b`, `multiply a b`, `divide a b`, `power a b`, `root a b`  
- `history` – show history  
- `clear` – clear history + undo/redo stacks  
- `undo` / `redo`  
- `save` – save history CSV  
- `load` – load history CSV  
- `exit` – quit (auto-saves if enabled)

---

## 🔧 Configuration

Managed by `app/calculator_config.py` and `.env`:

| Variable                       | Default | Description                                   |
|-------------------------------|---------|-----------------------------------------------|
| `CALCULATOR_MAX_HISTORY_SIZE` | `100`   | Max history entries to keep in memory         |
| `CALCULATOR_AUTO_SAVE`        | `true`  | Auto-save history on updates/exit             |
| `CALCULATOR_DEFAULT_ENCODING` | `utf-8` | File encoding for CSV/logs                    |

---

## 🧪 Tests & Coverage

### Run tests locally
    
    pytest

### Coverage reports
    
    coverage report

Generate HTML and open:

- **Windows**
  
      coverage html
      start htmlcov/index.html

- **macOS**
  
      coverage html
      open htmlcov/index.html

- **Linux**
  
      coverage html
      xdg-open htmlcov/index.html

**Coverage policy**
- Minimum threshold enforced by `pytest.ini`: **90%**  
- Interactive REPL (`app/calculator_repl.py`) is **excluded** from coverage via `.coveragerc`:

    [run]
    omit =
        app/calculator_repl.py

---

## 🤖 Continuous Integration (GitHub Actions)

Workflow: `.github/workflows/python-app.yml`

- Installs pinned deps  
- Creates `.env` for the job  
- Runs `pytest`  
- Enforces coverage ≥ 90% (see badge at top)

---

## 🧠 Design Patterns (Quick Map)

| Pattern  | Where                                   | Why                                          |
|----------|------------------------------------------|----------------------------------------------|
| Factory  | `operations.py`                          | Map user command → operation object          |
| Strategy | `operations.py`                          | Swap execution logic per operation           |
| Observer | `history.py`, `calculator.py`            | Log/save when history changes                |
| Memento  | `calculator_memento.py`, `calculator.py` | Undo/redo of history state                   |
| Facade   | `calculator.py`                          | Single high-level API for app features       |

---

## 🪛 Troubleshooting

- **Windows log file locked during tests**  
  Addressed by delayed/explicit handler cleanup in `calculator.py`. If you add new handlers, ensure they’re closed and removed (especially in tests/teardown).

- **`code` command not found** (VS Code)  
  - Windows: ensure “Add to PATH” was selected during VS Code install.  
  - macOS: run “Shell Command: Install 'code' command in PATH” from Command Palette.