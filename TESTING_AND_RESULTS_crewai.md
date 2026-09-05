# Testing and Results

## 1. Test Objective

The purpose of this test was to verify that the CrewAI Multi-Agent Market Research & GTM Generator could:

1. Load credentials securely from a local `.env` file.
2. Connect the Streamlit application to Microsoft Foundry OpenAI v1.
3. Connect to a local MCP server through SSE.
4. Discover and use the five MCP market-research tools.
5. Coordinate a hierarchical CrewAI workflow.
6. Generate and display a consolidated market-intelligence and GTM report.

## 2. Test Environment

| Component | Configuration |
| --- | --- |
| Operating system | Windows |
| Development environment | Visual Studio Code and PowerShell |
| Python | 3.12.14 |
| Package manager | `uv` |
| User interface | Streamlit on `http://localhost:8501` |
| MCP transport | SSE |
| MCP server | FastMCP on `http://127.0.0.1:8005/sse` |
| LLM provider | Microsoft Foundry OpenAI v1 |
| Chat deployment | `vt-agi-chat` |
| Search provider | SerpAPI through the MCP server |
| Website extraction | CrewAI `ScrapeWebsiteTool` |

## 3. Security Validation

Application secrets were moved out of the Python source files and stored in `.env`. Both `server.py` and `Azure-test-env.py` load `.env` from the directory containing the script:

```python
ENV_FILE = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_FILE, override=False)
```

The following values are required:

```env
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE-NAME.services.ai.azure.com/openai/v1/
AZURE_OPENAI_API_KEY=your_azure_api_key
AZURE_OPENAI_CHAT_DEPLOYMENT=your_deployment_name
SERPAPI_API_KEY=your_serpapi_key
```

The actual secret values were not placed in the Python code or documentation. `.env` and `.venv/` must remain excluded through `.gitignore`.

## 4. Test Scenario

The final end-to-end test used this research topic:

```text
Simplilearn vs Edureka
```

The application was expected to research and compare the two companies, analyze the market, develop strategic recommendations, and produce a consolidated GTM report.

## 5. Startup Procedure

The two application processes were started in separate PowerShell terminals.

### Terminal 1 - MCP server

```powershell
uv run python server.py
```

Successful server startup was confirmed by:

```text
Uvicorn running on http://127.0.0.1:8005
GET /sse HTTP/1.1 200 OK
POST /messages HTTP/1.1 202 Accepted
```

### Terminal 2 - Streamlit application

```powershell
uv run streamlit run Azure-test-env.py
```

Successful Streamlit startup was confirmed by:

```text
Local URL: http://localhost:8501
```

## 6. Problems Found and Resolutions

| Test stage | Error observed | Cause | Resolution | Result |
| --- | --- | --- | --- | --- |
| Environment creation | ChromaDB/Pydantic `chroma_server_nofile` error | Python 3.14 was incompatible with the installed dependency combination | Changed `requires-python` to `>=3.12,<3.13`, pinned Python 3.12, and rebuilt `.venv` | Passed |
| Azure provider initialization | Azure AI Inference provider unavailable | CrewAI Azure integration was not installed | Installed the required CrewAI provider dependency during diagnosis | Passed; later replaced with OpenAI v1 integration |
| MCP server import | `cannot import name 'GoogleSearch' from 'serpapi'` | The wrong package named `serpapi` conflicted with the server import | Removed the conflicting package and installed `google-search-results` | Passed |
| MCP connection | Connection timeout after 15 seconds | Streamlit started while `server.py` was not running | Started the MCP server first and kept it active in a separate terminal | Passed |
| Streamlit tool initialization | Application requested the `serpapi` package | Streamlit directly instantiated `SerpApiGoogleSearchTool` while the MCP server already provided SerpAPI searches | Removed the duplicate direct SerpAPI tool and routed research through MCP | Passed |
| Azure request | HTTP 404 Resource not found | The full `/responses` URL and provider configuration did not match the expected base endpoint | Used the Microsoft Foundry base URL ending in `/openai/v1/` | Passed |
| Azure request | API version not supported | A dated `api-version` was sent to the versionless Foundry v1 endpoint | Switched CrewAI to OpenAI Responses mode and stopped sending a dated API version | Passed |
| Model execution | Unsupported parameter: `temperature` | The deployed model does not accept a custom temperature value | Removed `temperature` from both LLM configurations | Passed |

## 7. Final Configuration

The working CrewAI LLM configuration uses the Microsoft Foundry OpenAI-compatible v1 endpoint:

```python
model_name = f"openai/{AZURE_OPENAI_CHAT_DEPLOYMENT}"

llm = LLM(
    model=model_name,
    api_key=AZURE_OPENAI_API_KEY,
    base_url=AZURE_OPENAI_ENDPOINT,
    api="responses",
)
```

No dated API version or custom temperature value is passed.

## 8. MCP Integration Results

The Streamlit sidebar confirmed a successful MCP connection and discovered five tools:

1. `company_overview`
2. `list_competitors`
3. `product_portfolio`
4. `pricing_snapshot`
5. `recent_news_pulse`

The server logs returned HTTP `200 OK` for SSE connections and HTTP `202 Accepted` for MCP messages.

## 9. Multi-Agent Workflow Results

The final successful test coordinated these roles:

| Role | Test responsibility |
| --- | --- |
| Head Manager | Coordinated work and compiled the final response |
| Researcher | Used scraping and MCP tools to collect market information |
| Business Analyst | Produced market and competitive analysis |
| GTM Strategist | Developed positioning, messaging, channels, and implementation recommendations |

The Streamlit application reported:

| Metric | Result |
| --- | --- |
| Workflow status | Execution successful |
| Successful tasks | 4 of 4 |
| Total latency | 285.66 seconds |
| Approximate duration | 4 minutes 46 seconds |
| Output | 26-page market-intelligence and GTM report |

## 10. Generated Report Sections

The successful test output included:

- Executive summary
- Methodology and data-source plan
- Market sizing and growth analysis
- Competitor landscape
- Simplilearn and Edureka profiles
- Side-by-side competitive comparison
- Pricing and product portfolio discussion
- Industry trends
- Business analysis and strategic recommendations
- GTM strategy
- 30-60-90-day implementation roadmap
- KPIs and measurement guidance
- Appendices and reproducibility guidance

## 11. Acceptance Criteria

| Acceptance criterion | Status |
| --- | --- |
| Application loads configuration from `.env` | Passed |
| API keys are absent from Python source code | Passed |
| Python 3.12 environment starts successfully | Passed |
| MCP server starts on port 8005 | Passed |
| Streamlit starts on port 8501 | Passed |
| Streamlit discovers five MCP tools | Passed |
| Microsoft Foundry accepts the model request | Passed |
| CrewAI completes all four tasks | Passed |
| Final report is displayed in Streamlit | Passed |
| Output can be exported to PDF | Passed |

## 12. Known Limitations and Validation Requirements

The technical execution passed, but generated business content still requires human review. The sample report contains estimates, provisional claims, and some placeholders that should not be treated as verified facts.

Before using the report for a business, investment, procurement, or academic decision:

1. Open every cited source and confirm that it supports the associated claim.
2. Replace placeholder values with verified data.
3. Validate market-size, pricing, traffic, funding, and company-profile figures.
4. Record the source URL and retrieval date for each material claim.
5. Clearly distinguish verified facts, estimates, assumptions, and AI-generated recommendations.

## 13. Final Test Conclusion

The final end-to-end technical test passed. The application securely loaded its configuration, connected Streamlit to the MCP server, discovered all five research tools, successfully called Microsoft Foundry through the OpenAI v1 Responses API, completed four CrewAI tasks, and generated a downloadable report.

The next quality-improvement phase should focus on source validation, removal of placeholders, automated citation checking, and repeatable test cases for different research topics.
