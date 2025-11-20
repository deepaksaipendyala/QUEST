# LLM-Enhanced Supervisor Implementation

## Overview

The LLM-Enhanced Supervisor extends the rule-based supervisor with intelligent analysis powered by Large Language Models. It provides contextual, actionable feedback for test improvement by analyzing execution results, static analysis data, and reliability metrics.

## Why Use LLM at Supervisor?

The traditional rule-based supervisor provides basic feedback like "increase coverage" or "fix lint issues." The LLM supervisor adds:

1. **Contextual Analysis**: Understands the relationship between coverage gaps, mutation scores, and code quality
2. **Specific Suggestions**: Provides concrete next steps rather than generic advice
3. **Prioritized Feedback**: Identifies the most impactful improvements first
4. **Strategic Guidance**: Suggests testing strategies based on code complexity and error patterns

## Architecture

### Components

1. **`src/llm/supervisor.py`**: Core LLM supervisor logic
   - `_build_llm_supervisor_prompt()`: Constructs comprehensive analysis prompt
   - `_parse_llm_supervisor_response()`: Parses structured LLM responses
   - `analyze_with_llm()`: Enhanced analysis combining rule-based + LLM insights

2. **`src/agents/supervisor.py`**: Agent wrapper with configuration
   - Checks `LLM_SUPERVISOR` environment variable
   - Falls back to rule-based supervisor if LLM unavailable
   - Tracks LLM metadata (cost, tokens, entropy)

3. **`src/contracts/messages.py`**: Extended Critique contract
   - `llm_suggestions`: Structured suggestions by category
   - `llm_supervisor_metadata`: LLM call metadata

### Data Flow

```
Test Results + Static Analysis + Reliability
                    ↓
        Rule-based Analysis (baseline)
                    ↓
        LLM Prompt Construction
                    ↓
        LLM Analysis (if enabled)
                    ↓
        Response Parsing & Integration
                    ↓
        Enhanced Critique with Suggestions
```

## LLM Prompt Design

The supervisor prompt includes:

### Context Section
- Test execution results (success, coverage, mutation score)
- Static analysis metrics (syntax, lint issues, complexity)
- Reliability assessments (pre/post execution)
- Current test source code (truncated if long)

### Analysis Request
- Structured JSON response format
- Six categories of suggestions:
  - `priority_issues`: Critical problems to fix first
  - `coverage_suggestions`: Specific coverage improvements
  - `mutation_suggestions`: Ways to improve mutation killing
  - `code_quality_suggestions`: Lint/style improvements
  - `test_strategy_suggestions`: Higher-level testing approaches
  - `next_steps`: Prioritized concrete actions

### Guidelines
- Be specific about lines/functions to target
- Suggest concrete test cases, not generic advice
- Consider edge cases and boundary values
- Prioritize high-impact changes

## Example LLM Response

```json
{
  "priority_issues": [
    "Fix ImportError preventing test execution",
    "Resolve 8 lint issues blocking code quality"
  ],
  "coverage_suggestions": [
    "Add tests for uncovered lines 15-18 (error handling path)",
    "Test the edge case where input is None",
    "Add boundary value tests for the range validation"
  ],
  "mutation_suggestions": [
    "Add assertion to verify the actual return value, not just type",
    "Test the negative case to kill the negation mutant on line 23"
  ],
  "code_quality_suggestions": [
    "Fix pylint C0103: Variable name doesn't conform to snake_case",
    "Add type hints to resolve mypy errors"
  ],
  "test_strategy_suggestions": [
    "Use unittest.mock to avoid file system dependencies",
    "Focus on unit tests for individual functions first"
  ],
  "next_steps": [
    "Fix import errors to enable test execution",
    "Add tests for lines 15-18 to reach coverage target",
    "Improve assertions to kill more mutants"
  ]
}
```

## Configuration

### Environment Variables
- `LLM_SUPERVISOR=true`: Enable LLM-enhanced supervisor
- `OPENAI_API_KEY`: Required for OpenAI API access

### Config File (`configs/default.yaml`)
```yaml
supervisor:
  use_llm: true  # Enable LLM-enhanced supervisor analysis
```

### LLM Settings
- Model: `gpt-4o-mini` (efficient for analysis tasks)
- Temperature: `0.1` (low for consistent analysis)
- Top-p: `0.9`
- Logprobs: `false` (not needed for supervisor)

## Integration Points

### Orchestrator Engine
- Calls supervisor after each test run
- Tracks supervisor LLM metadata and costs
- Writes `attempt_k.supervisor_llm_metadata.json`
- Aggregates supervisor costs in run summary

### Streamlit Dashboard
- Displays structured LLM suggestions with icons
- Shows supervisor LLM metadata (entropy, cost, tokens)
- Expandable sections for full analysis
- Separate display from enhancer LLM metadata

### Cost Tracking
- Supervisor LLM calls are tracked separately
- Included in total run cost calculations
- Visible in per-attempt metrics and run summaries

## Benefits

### For Test Quality
1. **Targeted Improvements**: Specific line numbers and functions to test
2. **Strategic Focus**: Prioritizes high-impact changes
3. **Context Awareness**: Understands relationships between metrics

### for Development Workflow
1. **Actionable Feedback**: Concrete next steps vs. generic advice
2. **Learning Tool**: Explains why certain tests are needed
3. **Efficiency**: Reduces trial-and-error in test writing

### For System Observability
1. **Rich Analytics**: Detailed breakdown of improvement suggestions
2. **Cost Tracking**: Supervisor LLM usage monitoring
3. **Confidence Metrics**: Entropy/logprob for supervisor analysis quality

## Usage Examples

### Basic Usage
```python
from src.agents.supervisor import SupervisorAgent
from src.core.config import load_config

# Enable LLM supervisor
os.environ['LLM_SUPERVISOR'] = 'true'

supervisor = SupervisorAgent()
critique = supervisor.call(test_payload, cfg=config)

# Access LLM suggestions
if 'llm_suggestions' in critique:
    priority_issues = critique['llm_suggestions']['priority_issues']
    next_steps = critique['llm_suggestions']['next_steps']
```

### Orchestrator Integration
The orchestrator automatically uses the LLM supervisor when enabled:
```bash
export LLM_SUPERVISOR=true
python src/orchestrator/engine.py --repo django/django --version 4.1 --code-file django/views/static.py
```

### Dashboard Viewing
1. Run Streamlit: `streamlit run streamlit_app.py`
2. Navigate to orchestrator run
3. View "Supervisor critique" section for LLM analysis
4. Check "Supervisor LLM metadata" for cost/confidence metrics

## Performance Considerations

### Cost Management
- Uses efficient `gpt-4o-mini` model
- Supervisor calls are typically 100-200 tokens input, 150-300 tokens output
- Estimated cost: ~$0.0001-0.0003 per supervisor call

### Latency
- Adds ~1-3 seconds per iteration for LLM analysis
- Can be disabled via `LLM_SUPERVISOR=false` for faster runs
- Falls back gracefully to rule-based supervisor

### Reliability
- Robust JSON parsing with fallback handling
- Graceful degradation if LLM call fails
- Always provides rule-based analysis as baseline

## Future Enhancements

1. **Model Selection**: Support for different models based on complexity
2. **Caching**: Cache similar analysis to reduce API calls
3. **Learning**: Fine-tune prompts based on successful suggestions
4. **Integration**: Feed supervisor suggestions directly to enhancer
5. **Metrics**: Track suggestion effectiveness over time

## Troubleshooting

### Common Issues

1. **No LLM suggestions appearing**
   - Check `LLM_SUPERVISOR` environment variable
   - Verify `OPENAI_API_KEY` is set
   - Check network connectivity for API calls

2. **JSON parsing errors**
   - LLM response format issues are handled gracefully
   - Check supervisor LLM metadata for raw response
   - Fallback to rule-based analysis occurs automatically

3. **High costs**
   - Monitor supervisor LLM metadata in dashboard
   - Consider disabling for batch runs: `LLM_SUPERVISOR=false`
   - Use cost tracking in run summaries

### Debugging
- Enable verbose logging to see LLM prompts and responses
- Check `attempt_k.supervisor_llm_metadata.json` files
- Use Streamlit dashboard to inspect full LLM analysis
