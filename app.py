"""Streamlit User Interface for RuleFlow Compiler.

Provides an interactive dashboard to explore each phase of the compilation
pipeline from source code to execution.
"""

from pathlib import Path
import streamlit as st

from ruleflow.lexer import Lexer, LexerError
from ruleflow.parser import Parser, ParserError
from ruleflow.semantic import SemanticAnalyzer, SemanticError
from ruleflow.ir import IRGenerator
from ruleflow.optimizer import Optimizer
from ruleflow.codegen import CodeGenerator
from ruleflow.execution import Executor

st.set_page_config(
    page_title="RuleFlow Compiler",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ RuleFlow Compiler")
st.caption("A modular, educational compiler for rule-based workflows")

# Sidebar - Example Selector & Information
st.sidebar.header("📁 Source Code")

examples_dir = Path(__file__).parent / "examples"
example_files = list(examples_dir.glob("*.rf")) if examples_dir.exists() else []
example_options = {f.name: f for f in example_files}

selected_example_name = st.sidebar.selectbox(
    "Load an example",
    options=["Custom Input"] + list(example_options.keys()),
    index=0,
)

default_code = "// Write your RuleFlow code here\nRULE SampleRule:\n    IF score >= 80 THEN\n        status = \"Approved\"\n    END\n"

if selected_example_name != "Custom Input" and selected_example_name in example_options:
    selected_path = example_options[selected_example_name]
    try:
        default_code = selected_path.read_text(encoding="utf-8")
    except Exception as e:
        st.sidebar.error(f"Error reading file: {e}")

st.sidebar.markdown("---")
st.sidebar.header("🏷️ External Input Variables")
default_inputs = (
    "gpa: DECIMAL\nattendance: INTEGER"
    if "student_eligibility" in selected_example_name
    else ("cart_total: DECIMAL\ncustomer_tier: STRING" if "discount_calculation" in selected_example_name else "")
)
inputs_text = st.sidebar.text_area(
    "Define Inputs (name: TYPE)",
    value=default_inputs,
    height=80,
    help="One per line, e.g.:\ngpa: DECIMAL\nattendance: INTEGER",
)
input_types = {}
for line in inputs_text.strip().splitlines():
    if ":" in line:
        name, typ = line.split(":", 1)
        name = name.strip()
        typ = typ.strip().upper()
        if name and typ:
            input_types[name] = typ

source_code = st.text_area(
    "RuleFlow Source Code",
    value=default_code,
    height=200,
    help="Enter rule-based code to pass through the compiler pipeline.",
)

# Pipeline Control
compile_btn = st.button("🚀 Run Compiler Pipeline", type="primary")

st.markdown("---")
st.subheader("🔍 Compiler Pipeline Stages")

tabs = st.tabs([
    "1. Lexer (Tokens)",
    "2. Parser & AST",
    "3. Semantic Analysis",
    "4. Intermediate Code (IR)",
    "5. Optimization",
    "6. Code Generation",
    "7. Execution",
])

if compile_btn:
    try:
        # 1. Lexing
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()

        # 2. Parsing & AST
        parser = Parser(tokens)
        ast = parser.parse()

        # 3. Semantic Analysis
        analyzer = SemanticAnalyzer(ast, input_types=input_types)
        is_valid = analyzer.analyze()

        # 4. IR Generation (only after semantic analysis passes)
        ir_gen = IRGenerator(ast)
        ir_instructions = ir_gen.generate()

        # 5. Optimization
        optimizer = Optimizer(ir_instructions)
        optimized_ir = optimizer.optimize()

        # 6. Code Generation (placeholder)
        codegen = CodeGenerator(optimized_ir)
        target_code = codegen.generate()

        # 7. Execution (placeholder)
        executor = Executor(target_code)
        execution_result = executor.execute()

        with tabs[0]:
            st.markdown("#### Lexical Analysis")
            st.info("Module: `ruleflow.lexer` - Tokenizes source text into discrete tokens.")
            st.success(f"Successfully generated {len(tokens)} token(s).")
            st.dataframe([t.to_dict() for t in tokens], use_container_width=True)
            with st.expander("View Raw Token Representation"):
                st.code("\n".join(repr(t) for t in tokens), language="text")

        with tabs[1]:
            st.markdown("#### Syntax Analysis (Abstract Syntax Tree)")
            st.info("Module: `ruleflow.parser` & `ruleflow.ast` - Constructs the AST hierarchy.")
            st.success("Successfully generated Abstract Syntax Tree.")
            st.markdown("**Indented AST View:**")
            st.code(ast.pretty(), language="text")
            with st.expander("View JSON AST Structure"):
                st.json(ast.to_dict())

        with tabs[2]:
            st.markdown("#### Semantic Analysis & Type Checking")
            st.info("Module: `ruleflow.semantic` - Validates types, symbols, and scope rules.")
            st.success("✅ Semantic analysis passed! All types, symbols, and scopes are valid.")
            st.markdown("**Symbol Table:**")
            if analyzer.symbol_table:
                st.dataframe(list(analyzer.symbol_table.values()), use_container_width=True)
            else:
                st.info("No variables in symbol table.")
            with st.expander("View Raw Symbol Table JSON"):
                st.json(analyzer.symbol_table)

        with tabs[3]:
            st.markdown("#### Intermediate Code Generation (Three-Address Code)")
            st.info("Module: `ruleflow.ir` - Produces machine-independent linear Three-Address Code.")
            st.success(f"Generated {len(ir_instructions)} Three-Address Code instruction(s).")
            st.markdown("**Unoptimized TAC:**")
            st.code("\n".join(str(inst) for inst in ir_instructions), language="text")
            with st.expander("View Structured Instruction Table"):
                st.dataframe([inst.to_dict() for inst in ir_instructions], use_container_width=True)

        with tabs[4]:
            st.markdown("#### Code Optimization (TAC)")
            st.info("Module: `ruleflow.optimizer` - Performs Constant Propagation, Constant Folding, and Dead Temporary Elimination.")
            diff = len(ir_instructions) - len(optimized_ir)
            st.success(f"Optimization complete: {len(optimized_ir)} instructions remaining ({diff} eliminated).")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Before (Raw TAC):**")
                st.code("\n".join(str(inst) for inst in ir_instructions), language="text")
            with col2:
                st.markdown("**After (Optimized TAC):**")
                st.code("\n".join(str(inst) for inst in optimized_ir), language="text")

            st.markdown("**Optimization Log:**")
            opt_log = optimizer.get_log()
            if opt_log:
                for entry in opt_log:
                    st.write(f"- `{entry}`")
            else:
                st.info("No constant folding or dead code elimination opportunities detected.")

            with st.expander("View Optimized Instruction Table"):
                st.dataframe([inst.to_dict() for inst in optimized_ir], use_container_width=True)

        with tabs[5]:
            st.markdown("#### Target Code Generation")
            st.info("Module: `ruleflow.codegen` - Emits target code or bytecode.")
            st.write("Target Code:")
            st.json(target_code if target_code else {"status": "Placeholder (Pending Module 5)"})

        with tabs[6]:
            st.markdown("#### Execution / Runtime Output")
            st.info("Module: `ruleflow.execution` - Virtual execution environment or runtime.")
            st.write("Execution Result:")
            st.json(execution_result)

    except LexerError as lex_err:
        st.error(f"❌ {lex_err}")
        with tabs[0]:
            st.error(f"Lexical Error Encountered:\n\n{lex_err}")
    except ParserError as parse_err:
        st.error(f"❌ {parse_err}")
        with tabs[1]:
            st.error(f"Syntax Error Encountered:\n\n{parse_err}")
    except SemanticError as sem_err:
        st.error(f"❌ {sem_err}")
        with tabs[2]:
            st.error(f"Semantic Error Encountered:\n\n{sem_err}")
    except Exception as err:
        st.error(f"❌ Pipeline Error: {err}")
else:
    for i, tab in enumerate(tabs):
        with tab:
            st.info("Click **'Run Compiler Pipeline'** above to trace this stage through the RuleFlow compiler.")
