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
from ruleflow.execution import Executor, ExecutionError

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
    ""
    if "while_loop" in selected_example_name
    else (
        "score: INTEGER\ntax_rate: DECIMAL\nstudent_name: STRING"
        if "builtin_functions" in selected_example_name
        else (
            "marks: INTEGER"
            if "grade_evaluation" in selected_example_name
            else (
                "gpa: DECIMAL\nattendance: INTEGER"
                if "student_eligibility" in selected_example_name
                else (
                    "cart_total: DECIMAL\ncustomer_tier: STRING"
                    if "discount_calculation" in selected_example_name
                    else "score: INTEGER"
                )
            )
        )
    )
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

st.sidebar.markdown("---")
st.sidebar.header("🎮 Runtime Input Values")
default_values_text = (
    ""
    if "while_loop" in selected_example_name
    else (
        'score = 85\ntax_rate = 18.75\nstudent_name = "RuleFlow"'
        if "builtin_functions" in selected_example_name
        else (
            "marks = 82"
            if "grade_evaluation" in selected_example_name
            else (
                "gpa = 3.8\nattendance = 85"
                if "student_eligibility" in selected_example_name
                else ('cart_total = 150.0\ncustomer_tier = "GOLD"' if "discount_calculation" in selected_example_name else "score = 90")
            )
        )
    )
)
runtime_values_input = st.sidebar.text_area(
    "Provide Values (name = value)",
    value=default_values_text,
    height=80,
    help="One per line, e.g.:\ngpa = 3.8\nattendance = 85",
)

runtime_inputs = {}
for line in runtime_values_input.strip().splitlines():
    line = line.strip()
    if not line or line.startswith("//") or line.startswith("#"):
        continue
    if "=" in line:
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            runtime_inputs[k] = v[1:-1]
        elif v.lower() == "true":
            runtime_inputs[k] = True
        elif v.lower() == "false":
            runtime_inputs[k] = False
        else:
            try:
                if "." in v:
                    runtime_inputs[k] = float(v)
                else:
                    runtime_inputs[k] = int(v)
            except ValueError:
                runtime_inputs[k] = v

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

STAGE_NAMES = [
    "Lexical Analysis",
    "Syntax Analysis (Parser)",
    "Semantic Analysis",
    "Intermediate Code Generation",
    "Code Optimization",
    "Target Code Generation",
    "Rule Execution",
]

tabs = st.tabs([
    "1. Lexer (Tokens)",
    "2. Parser & AST",
    "3. Semantic Analysis",
    "4. Intermediate Code (IR)",
    "5. Optimization",
    "6. Code Generation",
    "7. Execution",
])

# Initialize session state for compilation persistence
if "pipeline_results" not in st.session_state:
    st.session_state["pipeline_results"] = None

if compile_btn:
    results = {
        "failed_stage": None,
        "error_message": None,
        "tokens": None,
        "ast": None,
        "symbol_tables": {},
        "symbol_table": {},
        "ir_instructions": None,
        "optimized_ir": None,
        "optimization_log": [],
        "target_code": None,
        "execution_result": None,
    }

    try:
        # Stage 0: Lexical Analysis
        try:
            lexer = Lexer(source_code)
            tokens = lexer.tokenize()
            results["tokens"] = tokens
        except LexerError as err:
            results["failed_stage"] = 0
            results["error_message"] = str(err)
            raise

        # Stage 1: Syntax Analysis (Parser)
        try:
            parser = Parser(tokens)
            ast = parser.parse()
            results["ast"] = ast
        except ParserError as err:
            results["failed_stage"] = 1
            results["error_message"] = str(err)
            raise

        # Stage 2: Semantic Analysis & Scoping
        try:
            analyzer = SemanticAnalyzer(ast, input_types=input_types)
            analyzer.analyze()
            results["symbol_tables"] = {
                name: table.to_dict() for name, table in analyzer.symbol_tables.items()
            }
            results["symbol_table"] = analyzer.symbol_table
        except SemanticError as err:
            results["failed_stage"] = 2
            results["error_message"] = str(err)
            raise

        # Stage 3: Intermediate Code Generation
        try:
            ir_gen = IRGenerator(ast)
            ir_instructions = ir_gen.generate()
            results["ir_instructions"] = ir_instructions
        except Exception as err:
            results["failed_stage"] = 3
            results["error_message"] = str(err)
            raise

        # Stage 4: Code Optimization
        try:
            optimizer = Optimizer(ir_instructions)
            optimized_ir = optimizer.optimize()
            results["optimized_ir"] = optimized_ir
            results["optimization_log"] = optimizer.get_log()
        except Exception as err:
            results["failed_stage"] = 4
            results["error_message"] = str(err)
            raise

        # Stage 5: Target Code Generation
        try:
            codegen = CodeGenerator(optimized_ir)
            target_code = codegen.generate()
            results["target_code"] = target_code
        except Exception as err:
            results["failed_stage"] = 5
            results["error_message"] = str(err)
            raise

        # Stage 6: Rule Execution
        try:
            executor = Executor(target_code, symbol_table=analyzer.symbol_table)
            execution_result = executor.execute(runtime_inputs)
            results["execution_result"] = execution_result
        except ExecutionError as err:
            results["failed_stage"] = 6
            results["error_message"] = str(err)
            raise
        except Exception as err:
            results["failed_stage"] = 6
            results["error_message"] = str(err)
            raise

    except Exception:
        # Errors are captured in results dict
        pass

    st.session_state["pipeline_results"] = results


# -------------------------------------------------------------
# Tab Rendering (Reads from preserved session state)
# -------------------------------------------------------------
pipeline_results = st.session_state.get("pipeline_results")

if pipeline_results is None:
    for tab in tabs:
        with tab:
            st.info("Click **'Run Compiler Pipeline'** above to trace this stage through the RuleFlow compiler.")
else:
    failed_stage = pipeline_results.get("failed_stage")
    error_message = pipeline_results.get("error_message")

    if failed_stage is not None:
        st.error(f"❌ Pipeline halted at {STAGE_NAMES[failed_stage]}: {error_message}")

    def render_skipped(tab, stage_idx: int) -> None:
        with tab:
            st.warning(
                f"⚠️ Stage skipped: **{STAGE_NAMES[stage_idx]}** was not executed because **{STAGE_NAMES[failed_stage]}** encountered an error."
            )

    # 1. Lexical Analysis
    if failed_stage is not None and failed_stage == 0:
        with tabs[0]:
            st.markdown("#### Lexical Analysis")
            st.error(f"Lexical Error Encountered:\n\n{error_message}")
    elif pipeline_results.get("tokens") is not None:
        tokens = pipeline_results["tokens"]
        with tabs[0]:
            st.markdown("#### Lexical Analysis")
            st.info("Module: `ruleflow.lexer` - Tokenizes source text into discrete tokens.")
            st.success(f"Successfully generated {len(tokens)} token(s).")
            st.dataframe([t.to_dict() for t in tokens], use_container_width=True)
            with st.expander("View Raw Token Representation"):
                st.code("\n".join(repr(t) for t in tokens), language="text")

    # 2. Syntax Analysis (Parser & AST)
    if failed_stage is not None and failed_stage < 1:
        render_skipped(tabs[1], 1)
    elif failed_stage is not None and failed_stage == 1:
        with tabs[1]:
            st.markdown("#### Syntax Analysis (Abstract Syntax Tree)")
            st.error(f"Syntax Error Encountered:\n\n{error_message}")
    elif pipeline_results.get("ast") is not None:
        ast = pipeline_results["ast"]
        with tabs[1]:
            st.markdown("#### Syntax Analysis (Abstract Syntax Tree)")
            st.info("Module: `ruleflow.parser` & `ruleflow.ast` - Constructs the AST hierarchy.")
            st.success("Successfully generated Abstract Syntax Tree.")
            st.markdown("**Indented AST View:**")
            st.code(ast.pretty(), language="text")
            with st.expander("View JSON AST Structure"):
                st.json(ast.to_dict())

    # 3. Semantic Analysis & Scoping
    if failed_stage is not None and failed_stage < 2:
        render_skipped(tabs[2], 2)
    elif failed_stage is not None and failed_stage == 2:
        with tabs[2]:
            st.markdown("#### Semantic Analysis & Type Checking")
            st.error(f"Semantic Error Encountered:\n\n{error_message}")
    else:
        symbol_tables = pipeline_results.get("symbol_tables", {})
        with tabs[2]:
            st.markdown("#### Semantic Analysis & Type Checking")
            st.info("Module: `ruleflow.semantic` - Validates types, symbols, and scope rules.")
            st.success("✅ Semantic analysis passed! All types, symbols, and scopes are valid.")

            if symbol_tables:
                rule_names = list(symbol_tables.keys())
                if len(rule_names) > 1:
                    selected_scope = st.selectbox(
                        "Select Rule Scope to Inspect:",
                        options=rule_names,
                        key="scope_selector",
                        help="Each rule maintains its own isolated variable scope.",
                    )
                    active_table = symbol_tables[selected_scope]
                    st.markdown(f"**Symbol Table for Scope: `{selected_scope}`**")
                else:
                    selected_scope = rule_names[0]
                    active_table = symbol_tables[selected_scope]
                    scope_label = "Global Scope" if selected_scope == "__global__" else f"Rule: `{selected_scope}`"
                    st.markdown(f"**Symbol Table ({scope_label}):**")

                if active_table:
                    st.dataframe(list(active_table.values()), use_container_width=True)
                else:
                    st.info(f"No variables in symbol table for scope '{selected_scope}'.")

                with st.expander("View All Symbol Tables (JSON)"):
                    st.json(symbol_tables)
            else:
                st.info("No variables in symbol table.")

    # 4. Intermediate Code Generation (TAC)
    if failed_stage is not None and failed_stage < 3:
        render_skipped(tabs[3], 3)
    elif failed_stage is not None and failed_stage == 3:
        with tabs[3]:
            st.markdown("#### Intermediate Code Generation (Three-Address Code)")
            st.error(f"IR Generation Error:\n\n{error_message}")
    elif pipeline_results.get("ir_instructions") is not None:
        ir_instructions = pipeline_results["ir_instructions"]
        with tabs[3]:
            st.markdown("#### Intermediate Code Generation (Three-Address Code)")
            st.info("Module: `ruleflow.ir` - Produces machine-independent linear Three-Address Code.")
            st.success(f"Generated {len(ir_instructions)} Three-Address Code instruction(s).")
            st.markdown("**Unoptimized TAC:**")
            st.code("\n".join(str(inst) for inst in ir_instructions), language="text")
            with st.expander("View Structured Instruction Table"):
                st.dataframe([inst.to_dict() for inst in ir_instructions], use_container_width=True)

    # 5. Code Optimization (TAC)
    if failed_stage is not None and failed_stage < 4:
        render_skipped(tabs[4], 4)
    elif failed_stage is not None and failed_stage == 4:
        with tabs[4]:
            st.markdown("#### Code Optimization (TAC)")
            st.error(f"Optimization Error:\n\n{error_message}")
    elif pipeline_results.get("optimized_ir") is not None:
        ir_instructions = pipeline_results["ir_instructions"]
        optimized_ir = pipeline_results["optimized_ir"]
        opt_log = pipeline_results.get("optimization_log", [])
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
            if opt_log:
                for entry in opt_log:
                    st.write(f"- `{entry}`")
            else:
                st.info("No constant folding or dead code elimination opportunities detected.")

            with st.expander("View Optimized Instruction Table"):
                st.dataframe([inst.to_dict() for inst in optimized_ir], use_container_width=True)

    # 6. Target Code Generation
    if failed_stage is not None and failed_stage < 5:
        render_skipped(tabs[5], 5)
    elif failed_stage is not None and failed_stage == 5:
        with tabs[5]:
            st.markdown("#### Target Code Generation")
            st.error(f"Target Code Generation Error:\n\n{error_message}")
    elif pipeline_results.get("target_code") is not None:
        target_code = pipeline_results["target_code"]
        with tabs[5]:
            st.markdown("#### Target Code Generation")
            st.info("Module: `ruleflow.codegen` - Emits executable TAC instructions for the runtime engine.")
            st.success(f"Ready for execution: {len(target_code)} target instruction(s) generated.")
            st.markdown("**Target Code Instructions:**")
            st.code("\n".join(str(inst) for inst in target_code), language="text")
            with st.expander("View Target Code Details"):
                st.dataframe([inst.to_dict() for inst in target_code], use_container_width=True)

    # 7. Execution / Runtime Output
    if failed_stage is not None and failed_stage < 6:
        render_skipped(tabs[6], 6)
    elif failed_stage is not None and failed_stage == 6:
        with tabs[6]:
            st.markdown("#### Execution / Runtime Output")
            st.error(f"Runtime Execution Error:\n\n{error_message}")
    elif pipeline_results.get("execution_result") is not None:
        execution_result = pipeline_results["execution_result"]
        with tabs[6]:
            st.markdown("#### Execution / Runtime Output")
            st.info("Module: `ruleflow.execution` - Direct Three-Address Code Interpreter and Runtime Environment.")

            if execution_result.status == "success":
                st.success(f"✅ Execution completed successfully in {execution_result.steps} step(s)!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Execution Status", execution_result.status.upper())
                with col2:
                    st.metric("Total Steps", execution_result.steps)

                st.markdown("### 📊 Output Variables")
                if execution_result.outputs:
                    out_df = [
                        {"Variable": k, "Value": str(v), "Type": type(v).__name__}
                        for k, v in execution_result.outputs.items()
                    ]
                    st.dataframe(out_df, use_container_width=True)
                else:
                    st.info("No output variables produced.")

                with st.expander("🌐 Complete Runtime Environment"):
                    st.json({k: str(v) for k, v in execution_result.environment.items()})

                with st.expander("📜 Step-by-Step Execution Trace"):
                    if execution_result.trace:
                        st.dataframe(execution_result.trace, use_container_width=True)
                    else:
                        st.info("No execution trace available.")

            elif execution_result.status == "ready":
                st.info("ℹ️ Program parsed successfully, but contains no executable instructions.")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Execution Status", "READY")
                with col2:
                    st.metric("Total Steps", 0)

            else:
                err_text = execution_result.error or execution_result.message or "Execution failed."
                st.error(f"❌ Execution Error: {err_text}")
                if execution_result.trace:
                    with st.expander("📜 Trace Up to Failure"):
                        st.dataframe(execution_result.trace, use_container_width=True)
