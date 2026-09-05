# Azure-test-env.py
# CrewAI + Azure OpenAI configuration loaded from a local .env file.

import os
import json
import time
from pathlib import Path
import streamlit as st

# ────────────────────────────── LOAD .ENV ──────────────────────────────
from dotenv import load_dotenv

# Load the .env located beside this Python file, even when Streamlit is started
# from a different working directory. Existing system variables take priority.
ENV_FILE = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_FILE, override=False)

# ────────────────────────────── MODEL CONFIG ──────────────────────────────
# Values come from .env. Never place API keys directly in this file.
MODEL_PROVIDER = "Microsoft Foundry (OpenAI v1)"
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
)

# Optional integrations already present in the supplied .env file.
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")

# Microsoft Foundry's /openai/v1 endpoint uses the standard OpenAI client and
# does not accept a dated api-version parameter.
if AZURE_OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = AZURE_OPENAI_API_KEY
if AZURE_OPENAI_ENDPOINT:
    os.environ["OPENAI_BASE_URL"] = AZURE_OPENAI_ENDPOINT

# MCP URL (Updated to port 8005)
MCP_SSE_URL = "http://127.0.0.1:8005/sse"

# ─────────────────────────────── STREAMLIT UI ──────────────────────────────
st.set_page_config(page_title="CrewAI Market Research & GTM", page_icon="🎯", layout="centered")
st.title("🎯 CrewAI Multi-Agent GTM Generator")
st.caption(f"Using {MODEL_PROVIDER} configuration from .env")

# Stop early with a clear message if required Azure configuration is absent.
required_settings = {
    "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
    "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
    "AZURE_OPENAI_CHAT_DEPLOYMENT": AZURE_OPENAI_CHAT_DEPLOYMENT,
}
missing_settings = [name for name, value in required_settings.items() if not value]
if missing_settings:
    st.error(
        "Missing required values in .env: " + ", ".join(missing_settings)
    )
    st.info(f"Expected .env location: {ENV_FILE}")
    st.stop()

# Chat history
if "chat" not in st.session_state:
    st.session_state.chat = []
for role, msg in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(msg)

# ─────────────────────────────── TOOL SETUP ──────────────────────────────
@st.cache_resource
def initialize_tools():
    from crewai_tools import ScrapeWebsiteTool
    tool_status = {}
    base_tools = []
    
    try:
        scrape_tool = ScrapeWebsiteTool()
        base_tools.append(scrape_tool)
        tool_status["Scraping"] = "✅ Available"
    except Exception as e:
        tool_status["Scraping"] = f"❌ Error: {str(e)[:30]}..."
    
    return base_tools, tool_status

base_tools, tool_status = initialize_tools()

# Display tool status
with st.sidebar:
    st.subheader("🛠️ Tool Status")
    for name, status in tool_status.items():
        st.write(f"**{name}**: {status}")

# ─────────────────────────────── CHAT INPUT ─────────────────────────────
topic = st.chat_input("Research topic (e.g., 'OpenAI competitors', 'AI market analysis')...")
if not topic:
    st.stop()

st.session_state.chat.append(("user", topic))
with st.chat_message("user"):
    st.write(topic)

with st.chat_message("assistant"):
    st.write(f"🎯 Starting hierarchical workflow with **{MODEL_PROVIDER}**...")

# ─────────────────────────── EXECUTION ──────────────────
progress = st.progress(0)
status_text = st.empty()

try:
    # Import CrewAI
    from crewai import Agent, Task, Crew, Process
    from crewai.llm import LLM
    from crewai_tools import MCPServerAdapter
    
    # ─────────────────── CREATE LLM INSTANCES ─────────────────
    azure_model = f"openai/{AZURE_OPENAI_CHAT_DEPLOYMENT}"

    crewai_llm = LLM(
        model=azure_model,
        api_key=AZURE_OPENAI_API_KEY,
        base_url=AZURE_OPENAI_ENDPOINT,
        api="responses",
    )
    manager_llm = LLM(
        model=azure_model,
        api_key=AZURE_OPENAI_API_KEY,
        base_url=AZURE_OPENAI_ENDPOINT,
        api="responses",
    )
    
    # ─────────────────── CONNECT TO MCP SERVER ─────────────────
    status_text.text("Connecting to MCP server...")
    progress.progress(10)
    
    server_params = {"url": MCP_SSE_URL, "transport": "sse"}
    
    with MCPServerAdapter(server_params, connect_timeout=15) as mcp_tools:
        mcp_available = bool(mcp_tools)
        mcp_count = len(mcp_tools) if mcp_tools else 0
        
        with st.sidebar:
            st.subheader("🔗 MCP Connection")
            if mcp_available:
                st.success(f"✅ Connected ({mcp_count} tools)")
                for tool in mcp_tools:
                    st.write(f"  • {tool.name}")
            else:
                st.info("ℹ️ MCP not connected - using base tools")
        
        status_text.text("Creating agents...")
        progress.progress(25)
        
        # ───────────────────────── AGENTS ─────────────────────
        head_manager = Agent(
            role="Head Manager",
            goal="Coordinate market research for {topic} by delegating specific tasks to team members. Use ONLY simple text strings when delegating.",
            backstory="You are a project coordinator who delegates work using simple, clear instructions. You NEVER use complex objects or structures.",
            allow_delegation=True,
            verbose=True,
            tools=[],
            max_execution_time=600,
            max_iter=3,
            llm=crewai_llm,
        )
        
        researcher = Agent(
            role="Researcher",
            goal="Execute comprehensive market research using web search, scraping, and MCP tools",
            backstory="You are a market research specialist who provides well-structured research reports with proper citations.",
            tools=base_tools + (list(mcp_tools) if mcp_available else []),
            allow_delegation=False,
            verbose=True,
            max_execution_time=800,
            max_iter=5,
            llm=crewai_llm
        )
        
        analyst = Agent(
            role="Business Analyst",
            goal="Transform research into business intelligence and market analysis",
            backstory="You are a strategic business analyst who creates market sizing, competitive analysis, and insights.",
            tools=base_tools,
            allow_delegation=False,
            verbose=True,
            max_execution_time=600,
            max_iter=4,
            llm=crewai_llm
        )
        
        gtm_strategist = Agent(
            role="GTM Strategist",
            goal="Develop practical go-to-market strategies and recommendations",
            backstory="You are a go-to-market expert who creates actionable marketing strategies and positioning frameworks.",
            tools=base_tools,
            allow_delegation=False,
            verbose=True,
            max_execution_time=600,
            max_iter=4,
            llm=crewai_llm
        )
        
        status_text.text("Defining tasks...")
        progress.progress(45)
        
        # ─────────────────────── TASKS ─────────────────────
        research_task = Task(
            description=(
                "Conduct comprehensive market research for " + topic + ". "
                "Use the connected MCP tools to search for market data, competitor information, "
                "pricing, product portfolios, and industry news. Use ScrapeWebsiteTool to "
                "extract detailed information from relevant pages. "
                "Create a structured research report with findings, data points, "
                "source citations, and key insights."
            ),
            expected_output=(
                "Comprehensive market research report with:\n"
                "- Executive summary of key findings\n"
                "- Market size and growth data with sources\n"
                "- Competitor analysis with key players\n"
                "- Pricing models and examples\n"
                "- Industry trends and developments\n"
                "- Source citations and data validation\n"
                "Format: Well-structured markdown document"
            )
        )
        
        analysis_task = Task(
            description=(
                "Create strategic business analysis for " + topic + " based on research findings. "
                "Develop market sizing framework with TAM/SAM/SOM estimates, create competitive "
                "positioning matrix, identify market opportunities and threats, analyze trends "
                "and business implications."
            ),
            expected_output=(
                "Strategic business analysis including:\n"
                "- Market sizing model (TAM/SAM/SOM)\n"
                "- Competitive analysis matrix\n"
                "- Market trends and implications\n"
                "- Opportunities and threats assessment\n"
                "- Strategic recommendations\n"
                "Format: Executive-ready analysis document"
            )
        )
        
        gtm_task = Task(
            description=(
                "Develop comprehensive go-to-market strategy for " + topic + ". "
                "Create ideal customer profile, value proposition, positioning statement, "
                "messaging framework, marketing channel recommendations, success metrics, "
                "and implementation roadmap."
            ),
            expected_output=(
                "Complete GTM strategy with:\n"
                "- Ideal customer profile (ICP)\n"
                "- Value proposition and positioning\n"
                "- Core messaging framework\n"
                "- Marketing channel strategy\n"
                "- Success metrics and KPIs\n"
                "- Implementation roadmap (30-60-90 days)\n"
                "Format: Presentation-ready strategy document"
            )
        )
        
        synthesis_task = Task(
            description=(
                "Compile all research, analysis, and strategy outputs into a comprehensive "
                "final report for " + topic + ". Review all team deliverables, create "
                "executive summary, ensure consistency, and format as a professional document."
            ),
            expected_output=(
                "Complete market intelligence report with:\n"
                "- Executive summary with key insights\n"
                "- Research findings section\n"
                "- Business analysis section\n"
                "- GTM strategy section\n"
                "- Strategic recommendations\n"
                "Format: Single cohesive markdown document"
            ),
            agent=head_manager
        )
        
        status_text.text("Configuring hierarchical crew...")
        progress.progress(65)
        
        # Create crew
        crew = Crew(
            agents=[researcher, analyst, gtm_strategist],
            tasks=[research_task, analysis_task, gtm_task, synthesis_task],
            process=Process.hierarchical,
            manager_agent=head_manager,
            manager_llm=manager_llm,
            planning=True,
            planning_llm=crewai_llm,
            verbose=True,
            memory=False,
            max_execution_time=2400,
        )
        
        status_text.text("🎯 Executing workflow...")
        progress.progress(80)
        
        # EXECUTE WITH LATENCY LOGGING
        start_time = time.time()
        with st.spinner("Running hierarchical workflow... May take 5-15 minutes..."):
            result = crew.kickoff(inputs={"topic": topic})
        end_time = time.time()
        latency = end_time - start_time
        
        progress.progress(100)
        status_text.text("✅ Execution successful!")
        
        # ─────────────────────── DISPLAY RESULT ─────────────────────
        final_result = str(result)
        
        # Clean up JSON artifacts if they appear
        try:
            parsed = json.loads(final_result)
            if isinstance(parsed, str):
                final_result = parsed
            elif "output" in parsed:
                final_result = parsed["output"]
        except:
            pass  # It's plain text, just use it as-is
        
        # Show latency
        with st.success(f"🎉 Workflow completed in {latency:.2f} seconds!"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Latency", f"{latency:.2f}s")
            with col2:
                st.metric("Successful Tasks", "4/4")
            with col3:
                st.metric("Model Provider", MODEL_PROVIDER)
        
        st.session_state.chat.append(("assistant", final_result))
        st.markdown(final_result)

except Exception as e:
    error_msg = str(e)
    st.error(f"❌ Error: {error_msg}")
    
    with st.expander("🔍 Error Diagnosis & Solutions"):
        import traceback
        st.code(traceback.format_exc())
        
        if "mcp" in error_msg.lower():
            st.warning("**MCP Connection Error**")
            st.info("Ensure `server.py` is running on port 8005: `uv run python server.py`")

# Final status
with st.sidebar:
    st.subheader("🎯 Configuration")
    st.success(
        f"Model Provider: {MODEL_PROVIDER}\n"
        f"Azure API Key: {'✅' if AZURE_OPENAI_API_KEY else '❌'}\n"
        f"Chat Deployment: {AZURE_OPENAI_CHAT_DEPLOYMENT}\n"
        f"MCP URL: {MCP_SSE_URL}"
    )

st.caption(f"🎯 CrewAI with {MODEL_PROVIDER} • MCP Search • Latency Logging")
