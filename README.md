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

## 🔍 Module 3: Semantic Analysis and Type Checking

### What Semantic Analysis Does
Semantic analysis is the third phase of compilation. It checks context-sensitive rules that grammar alone cannot enforce:
- Resolves identifier scopes and verifies variables are defined before use.
- Performs definite assignment analysis across `IF-ELSE` branches.
- Type checks operations and enforces strict operand compatibility.
- Detects static runtime hazards like division or modulo by literal zero.

### Supported Data Types
- `INTEGER`: Whole numbers (e.g. `42`, `0`, `-15`).
- `DECIMAL`: Floating-point numbers (e.g. `3.14`, `0.5`).
- `STRING`: Quoted character sequences (e.g. `"Eligible"`).
- `BOOLEAN`: Truth values (`True`, `False`) resulting from relational or logical expressions.

### The Symbol Table Concept
The `SymbolTable` maintains scoped records of all known variables:
- **Variable Name**: Identifier key.
- **Data Type**: `INTEGER`, `DECIMAL`, `STRING`, or `BOOLEAN`.
- **Kind**: External `Input` vs `Internal` assignment.
- **Source Location**: Line and column where defined.
- **Rule Scope Isolation**: Variables assigned inside one rule do not leak into another rule.

### Type Checking & Inference Rules
1. **Arithmetic (`+`, `-`, `*`, `/`, `%`)**: Requires numeric operands (`INTEGER` or `DECIMAL`).
   - `INTEGER op INTEGER -> INTEGER` (for `+`, `-`, `*`, `%`)
   - `INTEGER / INTEGER -> DECIMAL` (true division)
   - Mixing `INTEGER` and `DECIMAL` widens to `DECIMAL`.
   - Division or modulo by literal zero raises a static `SemanticError`.
2. **Relational (`<`, `<=`, `>`, `>=`)**: Requires numeric operands; yields `BOOLEAN`.
3. **Equality (`==`, `!=`)**: Requires compatible operand types; yields `BOOLEAN`.
4. **Logical (`AND`, `OR`, `NOT`)**: Operands must be `BOOLEAN`; yields `BOOLEAN`.
5. **Conditionals (`IF`)**: Condition must evaluate to `BOOLEAN`.
6. **Definite Assignment**:
   - Variables assigned in both branches of an `IF-ELSE` remain defined after the `IF`.
   - Variables assigned only in the `THEN` branch (or without `ELSE`) are not considered definitely assigned after the `IF`.

---

## ⚙️ Module 4: Intermediate Code Generation and Optimization

### What Intermediate Representation (IR) Means
The Intermediate Representation serves as a bridge between the front-end (Lexer, Parser, Semantic Analyzer) and the back-end (Target Code Generator). It linearizes the hierarchical AST into an architecture-independent instruction stream that is easy to optimize.

### Three-Address Code (TAC)
RuleFlow uses **Three-Address Code**, where each instruction has at most one operator and at most three operands/addresses (two sources and one target):
- **Assignment**: `x = 10`
- **Binary Operation**: `t1 = 20 * 2`
- **Unary Operation**: `t2 = -x`
- **Conditional Jump**: `IF_FALSE cond GOTO L_else`
- **Unconditional Jump**: `GOTO L_end`
- **Label**: `LABEL L_else`

### Temporary Variables and Control Flow
- Compiler-generated temporary variables (`t1`, `t2`, `t3`, ...) store intermediate results of compound expressions in strict evaluation order.
- Conditional branches (`IF-THEN`, `IF-THEN-ELSE`) and short-circuit boolean logic (`AND`, `OR`) are translated into conditional jumps and unique destination labels.

### Optimization Passes
1. **Constant Propagation**:
   - Tracks known constants and replaces variable usages with their literal values.
   - *Safety Rule*: Constants are safely cleared across branch boundaries (`LABEL`, `GOTO`, `IF_FALSE`) to prevent invalid propagation across control-flow joins.
2. **Constant Folding**:
   - Statically evaluates compile-time operations (arithmetic, comparisons, equality, logic).
   - Division and modulo by zero are safely guarded without crashing.
3. **Dead Code Elimination (DCE)**:
   - Removes unused compiler temporaries (`t1`, `t2`, ...) that have no observable side effects.
   - *Safety Rule*: Named RuleFlow variables and control-flow labels/jumps are strictly preserved.

---

## 🧪 Running Tests

Verify the compiler modules using `pytest`:

```bash
# Run Module 4 IR and Optimizer tests only
.\venv\Scripts\pytest.exe tests/test_ir.py tests/test_optimizer.py -v

# Run entire test suite (Lexer + Parser + Semantic + IR + Optimizer + Structure)
.\venv\Scripts\pytest.exe -v
```

---

## 🗺️ Implementation Roadmap

- [x] Initial project scaffolding & module separation
- [x] Streamlit UI pipeline visualizer
- [x] **Module 1: Lexical Analysis (Lexer, Tokens, Line/Column tracking, Error handling)**
- [x] **Module 2: Syntax Analysis & Abstract Syntax Tree (Parser & AST, Grammar, Error handling)**
- [x] **Module 3: Semantic Analysis & Symbol Table Management (Types, Scopes, Definite Assignment)**
- [x] **Module 4: Intermediate Code Generation (TAC) & Optimization (Folding, Propagation, DCE)**
- [ ] Module 5: Target Code Generation
- [ ] Module 6: Execution Engine / Runtime VM
