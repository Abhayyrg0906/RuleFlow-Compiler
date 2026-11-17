# RuleFlow Compiler

A modular, beginner-friendly **Compiler Design Capstone Project** implemented in Python, featuring an interactive **Streamlit** user interface for visualizing each stage of the compilation pipeline.

---

## 📖 Overview

**RuleFlow Compiler** is designed to demonstrate end-to-end compiler construction principles by processing a domain-specific, rule-based language. 

The project is structured into clear, decoupled phases adhering to classical compiler design architecture:
1. **Lexical Analysis (Lexer)**: Tokenizes source code into a stream of meaningful symbols.
2. **Syntax Analysis (Parser & AST)**: Verifies grammar and builds an Abstract Syntax Tree.
3. **Semantic Analysis**: Ensures type correctness, scope validity, and maintains symbol tables.
4. **Intermediate Code Generation (IR)**: Produces an intermediate, machine-independent representation.
5. **Optimization**: Applies optimization passes (e.g., constant folding, dead code elimination).
6. **Code Generation**: Translates optimized IR into target instructions or bytecode.
7. **Execution**: Interprets or runs target code inside a simulated runtime engine.

---

## 📁 Project Structure

```text
RuleFlow-Compiler/
│
├── app.py                     # Interactive Streamlit web interface
├── requirements.txt           # Project dependencies
├── README.md                  # Project documentation
├── .gitignore                 # Ignored files (venv, cache, etc.)
│
├── ruleflow/                  # Core compiler package
│   ├── __init__.py            # Package initialization
│   ├── ast/                   # Abstract Syntax Tree nodes
│   │   ├── __init__.py
│   │   └── nodes.py
│   ├── lexer/                 # Lexical analysis (tokenization)
│   │   ├── __init__.py
│   │   └── lexer.py
│   ├── parser/                # Syntax analysis (parsing)
│   │   ├── __init__.py
│   │   └── parser.py
│   ├── semantic/              # Semantic validation & symbol tables
│   │   ├── __init__.py
│   │   └── analyzer.py
│   ├── ir/                    # Intermediate code generation (IR)
│   │   ├── __init__.py
│   │   └── ir_generator.py
│   ├── optimizer/             # Code optimization passes
│   │   ├── __init__.py
│   │   └── optimizer.py
│   ├── codegen/               # Target code generation
│   │   ├── __init__.py
│   │   └── codegen.py
│   └── execution/             # Execution engine / runtime
│       ├── __init__.py
│       └── executor.py
│
├── examples/                  # Sample RuleFlow source files
│   ├── hello_rule.rf
│   └── discount_calculation.rf
│
└── tests/                     # Unit and integration tests
    ├── __init__.py
    └── test_structure.py
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ installed on your system.

### 2. Set Up Virtual Environment

If not already activated, create and activate a virtual environment:

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🖥️ Running the Application

Launch the Streamlit web dashboard:

```bash
streamlit run app.py
```

Once running, open your browser at the indicated local URL (typically `http://localhost:8501`). You can:
- Select an example rule from the `examples/` directory or type custom code.
- Trigger the compilation pipeline.
- Inspect the output of each compiler phase in dedicated tabs.

---

## 🧪 Running Tests

Verify the structure and initial modules using `pytest`:

```bash
pytest
```

---

## 🗺️ Implementation Roadmap

- [x] Initial project scaffolding & module separation
- [x] Streamlit UI pipeline visualizer
- [x] **Module 1: Lexical Analysis (Lexer, Tokens, Line/Column tracking, Error handling)**
- [x] **Module 2: Syntax Analysis & Abstract Syntax Tree (Parser & AST, Grammar, Error handling)**
- [ ] Module 3: Semantic Analysis & Symbol Table Management
- [ ] Module 4: Intermediate Code Generation (IR)
- [ ] Module 5: Code Optimization Passes
- [ ] Module 6: Target Code Generation
- [ ] Module 7: Execution Engine / Runtime VM
