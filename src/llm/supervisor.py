from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from src.contracts.messages import Critique
from src.llm.provider import LLMConfig, LLMResult, run_completion, llm_enabled


def _extract_missing_lines(payload: Dict) -> List[int]:
    coverage_details = payload.get("coverageDetails", {})
    if not isinstance(coverage_details, dict):
        return []
    missing = coverage_details.get("missing_lines", [])
    if not isinstance(missing, list):
        return []
    return [int(x) for x in missing if isinstance(x, int)]


def _as_float(value: object, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _lint_stats(static_metrics: Dict) -> tuple[int, List[str], bool]:
    if not isinstance(static_metrics, dict):
        return 0, [], True
    linters = static_metrics.get("linters", {})
    total_issues = 0
    missing_tools: List[str] = []
    if isinstance(linters, dict):
        for tool, info in linters.items():
            if not isinstance(info, dict):
                continue
            available = bool(info.get("available", True))
            if not available:
                missing_tools.append(tool)
                continue
            total_issues += max(int(info.get("issue_count", 0)), 0)
    syntax_ok = bool(static_metrics.get("syntax_ok", True))
    return total_issues, missing_tools, syntax_ok


def _reliability_guidance(
    pre_reliability: Optional[Dict], post_reliability: Optional[Dict]
) -> List[str]:
    tips: List[str] = []
    for label, rel in (("pre", pre_reliability), ("post", post_reliability)):
        if not isinstance(rel, dict):
            continue
        level = str(rel.get("level", "")).lower()
        if label == "post" and level and level not in ("trusted", "pass"):
            reasons = rel.get("reasons")
            if isinstance(reasons, list) and reasons:
                tip = "; ".join(str(r) for r in reasons if isinstance(r, str))
                if tip:
                    tips.append(f"Reliability blockers: {tip}.")
        lint_block = rel.get("lint")
        if isinstance(lint_block, dict):
            issues = lint_block.get("issues")
            if isinstance(issues, int) and issues > 0:
                tips.append(f"Fix {issues} lint/type issues noted in reliability analysis.")
        test_error = rel.get("test_error")
        if isinstance(test_error, str) and test_error:
            tips.append(f"Address runner error reported: {test_error}.")
    return tips


def _build_llm_supervisor_prompt(
    payload: Dict,
    target_coverage: float,
    target_mutation: float,
    missing_lines: List[int],
    static_metrics: Optional[Dict],
    test_src: Optional[str] = None,
) -> str:
    """Build a comprehensive prompt for LLM-based test analysis and improvement suggestions."""
    
    # Extract key metrics
    coverage = _as_float(payload.get("coverage"), 0.0)
    mutation_score = _as_float(payload.get("mutation_score"), -1.0)
    success = bool(payload.get("success", False))
    status = str(payload.get("status", "error"))
    test_error = payload.get("test_error", "")
    
    # Extract reliability info
    pre_reliability = payload.get("pre_reliability", {})
    post_reliability = payload.get("post_reliability", {})
    
    # Extract static analysis
    lint_issue_count, lint_missing_tools, syntax_ok = _lint_stats(static_metrics or {})
    
    # Build context section
    context_lines = [
        "You are an expert Python test analysis supervisor.",
        "Analyze the test execution results and provide specific, actionable improvement suggestions.",
        "",
        "## Test Execution Results:",
        f"- Success: {success}",
        f"- Status: {status}",
        f"- Coverage: {coverage:.2f}% (target: {target_coverage:.2f}%)",
        f"- Mutation Score: {mutation_score:.2f}% (target: {target_mutation:.2f}%)" if mutation_score >= 0 else f"- Mutation Score: Not available (target: {target_mutation:.2f}%)",
        f"- Test Error: {test_error}" if test_error else "- Test Error: None",
    ]
    
    if missing_lines:
        context_lines.append(f"- Missing Coverage Lines: {', '.join(map(str, missing_lines[:15]))}")
    
    # Add static analysis info
    if static_metrics:
        context_lines.extend([
            "",
            "## Static Analysis:",
            f"- Syntax OK: {syntax_ok}",
            f"- Lint Issues: {lint_issue_count}",
        ])
        
        if lint_missing_tools:
            context_lines.append(f"- Missing Tools: {', '.join(lint_missing_tools)}")
            
        # Add complexity/structure info if available
        if isinstance(static_metrics, dict):
            line_count = static_metrics.get("line_count")
            function_count = static_metrics.get("function_count")
            class_count = static_metrics.get("class_count")
            complexity = static_metrics.get("complexity")
            
            if any(x is not None for x in [line_count, function_count, class_count, complexity]):
                context_lines.extend([
                    "- Code Structure:",
                    f"  * Lines: {line_count}" if line_count else "",
                    f"  * Functions: {function_count}" if function_count else "",
                    f"  * Classes: {class_count}" if class_count else "",
                    f"  * Complexity: {complexity}" if complexity else "",
                ])
    
    # Add reliability context
    if pre_reliability or post_reliability:
        context_lines.extend([
            "",
            "## Reliability Assessment:",
        ])
        if pre_reliability:
            pre_level = pre_reliability.get("level", "unknown")
            entropy = pre_reliability.get("entropy")
            context_lines.append(f"- Pre-execution: {pre_level}" + (f" (entropy: {entropy:.3f})" if entropy else ""))
        
        if post_reliability:
            post_level = post_reliability.get("level", "unknown")
            reasons = post_reliability.get("reasons", [])
            context_lines.append(f"- Post-execution: {post_level}")
            if reasons:
                context_lines.append(f"  * Reasons: {'; '.join(reasons)}")
    
    # Add test source if available (truncated)
    if test_src:
        lines = test_src.split('\n')
        if len(lines) > 50:
            truncated_src = '\n'.join(lines[:25]) + '\n... (truncated) ...\n' + '\n'.join(lines[-25:])
        else:
            truncated_src = test_src
        context_lines.extend([
            "",
            "## Current Test Source:",
            "```python",
            truncated_src,
            "```",
        ])
    
    # Build the instruction section
    instruction_lines = [
        "",
        "## Your Task:",
        "Provide a JSON response with specific, actionable improvement suggestions.",
        "Focus on the most impactful changes first.",
        "",
        "Required JSON format:",
        "{",
        '  "priority_issues": ["list of critical issues to fix first"],',
        '  "coverage_suggestions": ["specific suggestions to improve coverage"],',
        '  "mutation_suggestions": ["specific suggestions to improve mutation score"],',
        '  "code_quality_suggestions": ["suggestions for lint/style/structure improvements"],',
        '  "test_strategy_suggestions": ["higher-level testing strategy improvements"],',
        '  "next_steps": ["prioritized list of 3-5 concrete next steps"]',
        "}",
        "",
        "Guidelines:",
        "- Be specific about which lines/functions/branches to target",
        "- Suggest concrete test cases, not generic advice",
        "- Consider edge cases, error conditions, and boundary values",
        "- Prioritize changes that will have the biggest impact on coverage and mutation",
        "- If tests are failing, focus on fixing execution issues first",
        "- If coverage is low, identify specific uncovered code paths",
        "- If mutation score is low, suggest tests that kill more mutants",
        "",
        "Respond with ONLY the JSON object, no additional text or formatting.",
    ]
    
    return "\n".join(context_lines + instruction_lines)


def _parse_llm_supervisor_response(llm_result: LLMResult) -> Dict[str, List[str]]:
    """Parse LLM supervisor response and extract structured suggestions."""
    try:
        import json
        response_text = llm_result.text.strip()
        
        # Try to extract JSON from the response
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        parsed = json.loads(response_text)
        
        # Ensure all expected keys exist with lists
        expected_keys = [
            "priority_issues",
            "coverage_suggestions", 
            "mutation_suggestions",
            "code_quality_suggestions",
            "test_strategy_suggestions",
            "next_steps"
        ]
        
        result = {}
        for key in expected_keys:
            value = parsed.get(key, [])
            if isinstance(value, list):
                result[key] = [str(item) for item in value if item]
            elif isinstance(value, str):
                result[key] = [value] if value else []
            else:
                result[key] = []
        
        return result
        
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        # Fallback: extract any useful text
        return {
            "priority_issues": ["LLM response parsing failed"],
            "coverage_suggestions": [],
            "mutation_suggestions": [],
            "code_quality_suggestions": [],
            "test_strategy_suggestions": [],
            "next_steps": [f"Review LLM response manually: {llm_result.text[:200]}..."]
        }


def analyze_with_llm(
    payload: Dict, 
    target_coverage: float, 
    target_mutation: float = 0.0,
    llm_config: Optional[LLMConfig] = None
) -> Tuple[Critique, Optional[LLMResult]]:
    """Enhanced supervisor analysis using LLM for intelligent suggestions."""
    
    # First, run the rule-based analysis
    rule_based_critique = analyze(payload, target_coverage, target_mutation)
    
    # If LLM is not enabled or configured, return rule-based only
    if not llm_enabled() or not llm_config:
        return rule_based_critique, None
    
    # Extract additional context for LLM
    missing_lines = rule_based_critique["missing_lines"]
    static_metrics = payload.get("static_metrics")
    test_src = payload.get("test_src")  # May be available in some payloads
    
    # Build LLM prompt
    prompt = _build_llm_supervisor_prompt(
        payload, target_coverage, target_mutation, 
        missing_lines, static_metrics, test_src
    )
    
    try:
        # Get LLM analysis
        llm_result = run_completion(prompt, llm_config)
        llm_suggestions = _parse_llm_supervisor_response(llm_result)
        
        # Enhance the rule-based critique with LLM insights
        enhanced_instructions = list(rule_based_critique["instructions"])
        
        # Add LLM suggestions to instructions, prioritizing by category
        if llm_suggestions["priority_issues"]:
            enhanced_instructions.extend([
                f"PRIORITY: {issue}" for issue in llm_suggestions["priority_issues"][:3]
            ])
        
        if llm_suggestions["coverage_suggestions"]:
            enhanced_instructions.extend([
                f"Coverage: {suggestion}" for suggestion in llm_suggestions["coverage_suggestions"][:3]
            ])
            
        if llm_suggestions["mutation_suggestions"]:
            enhanced_instructions.extend([
                f"Mutation: {suggestion}" for suggestion in llm_suggestions["mutation_suggestions"][:3]
            ])
            
        if llm_suggestions["code_quality_suggestions"]:
            enhanced_instructions.extend([
                f"Quality: {suggestion}" for suggestion in llm_suggestions["code_quality_suggestions"][:2]
            ])
        
        # Store LLM suggestions in critique for debugging/analysis
        enhanced_critique = dict(rule_based_critique)
        enhanced_critique["instructions"] = enhanced_instructions
        enhanced_critique["llm_suggestions"] = llm_suggestions
        
        return enhanced_critique, llm_result
        
    except Exception as e:
        # If LLM analysis fails, fall back to rule-based
        fallback_critique = dict(rule_based_critique)
        fallback_critique["instructions"] = list(rule_based_critique["instructions"]) + [
            f"LLM supervisor analysis failed: {str(e)[:100]}"
        ]
        return fallback_critique, None


def analyze(payload: Dict, target_coverage: float, target_mutation: float = 0.0) -> Critique:
    status = str(payload.get("status", "error"))
    success = bool(payload.get("success", False))
    coverage = _as_float(payload.get("coverage"), 0.0)
    mutation_score = _as_float(payload.get("mutation_score"), -1.0)
    missing_lines = _extract_missing_lines(payload)
    static_metrics = payload.get("static_metrics") if isinstance(payload, dict) else None
    lint_issue_count, lint_missing_tools, syntax_ok = _lint_stats(static_metrics or {})

    compile_error = (not success and status == "error") or not syntax_ok
    no_tests = status == "no_tests_collected"
    coverage_target = _as_float(target_coverage, 0.0)
    low_coverage = coverage_target > 0.0 and coverage < coverage_target
    mutation_target = _as_float(target_mutation, 0.0)
    low_mutation = (
        mutation_target > 0.0
        and (
            mutation_score < mutation_target
            if mutation_score >= 0.0
            else True
        )
    )

    instructions: List[str] = []
    if not syntax_ok:
        instructions.append("Static analyzer found syntax issues; fix parser errors first.")
    if lint_issue_count > 0:
        instructions.append(
            f"Resolve {lint_issue_count} lint/type errors reported by available tools."
        )
    elif lint_missing_tools:
        instructions.append(
            f"Install lint/type tools ({', '.join(lint_missing_tools)}) to improve diagnostics."
        )
    if compile_error and syntax_ok:
        instructions.append("Resolve Runner errors and ensure tests execute successfully.")
    if no_tests:
        instructions.append("Add at least one pytest/unittest case so tests are collected.")
    if low_coverage:
        if missing_lines:
            targets = ", ".join(str(m) for m in missing_lines[:10])
            instructions.append(f"Add coverage for lines: {targets}.")
        else:
            instructions.append("Increase test coverage with more assertions.")
    if low_mutation and mutation_target > 0.0:
        if mutation_score >= 0.0:
            instructions.append(
                f"Improve mutation score from {mutation_score:.2f}% toward {mutation_target:.2f}%."
            )
        else:
            instructions.append(
                "Mutation score unavailable; ensure mutation testing runs and improves surviving mutants."
            )

    instructions.extend(
        _reliability_guidance(
            payload.get("pre_reliability"), payload.get("post_reliability")
        )
    )

    critique: Critique = {
        "compile_error": compile_error,
        "no_tests": no_tests,
        "low_coverage": low_coverage,
        "low_mutation": low_mutation,
        "mutation_score": mutation_score if mutation_score >= 0.0 else -1.0,
        "lint_issue_count": lint_issue_count,
        "lint_missing_tools": lint_missing_tools,
        "coverage_delta": 0.0,
        "mutation_delta": 0.0,
        "no_progress": False,
        "missing_lines": missing_lines,
        "instructions": instructions,
    }
    return critique
