# Documentation Index

Quick reference to all documentation files in this repository.

## Main Documentation

### **Project.md** (9.4K)
The original project specification describing QUEST system goals, architecture, and research questions.

**Read this**: To understand the overall vision and research objectives.

### **PROJECT_STATUS.md** (18K) - COMPREHENSIVE
Detailed implementation status comparing what's built vs. what's planned.

**Read this**: For complete understanding of what's done and what's missing.

Includes:
- Component-by-component status (Orchestrator, Agents, Runner, etc.)
- Missing features with estimates
- Implementation roadmap (12-week plan)
- Research question readiness
- Technical debt tracking

### **IMPLEMENTATION_SUMMARY.md** (6.7K) - QUICK OVERVIEW
Executive summary with visual progress bars and key gaps.

**Read this**: For quick status check and priorities.

Includes:
- Progress bars for each component
- Current capabilities
- Critical gaps
- Immediate next steps
- Timeline estimates

---

## Guides and Examples

### **END_TO_END_GUIDE.md** (5.5K)
Quick reference for running the complete pipeline.

**Use this**: To run your first orchestrator pipeline.

### **END_TO_END_EXAMPLE.md** (25K) - DETAILED WALKTHROUGH
Complete walkthrough of a real orchestrator run with all artifacts explained.

**Read this**: To understand exactly what happens during a run.

Includes:
- Step-by-step pipeline execution
- All artifact files with example contents
- LLM prompts and responses
- Coverage progression (44% -> 92%)
- Reliability scoring examples
- Cost breakdown and metrics
- Supervisor critique examples

### **AGENT_PROMPTS_AND_FLOW.md** (12K)
Detailed documentation of all agent prompts and system flow.

**Read this**: To understand agent interactions and prompt engineering.

### **LLM_SUPERVISOR_IMPLEMENTATION.md** (8K)
Documentation of the LLM-enhanced supervisor feature.

**Read this**: To understand intelligent test analysis.

---

## Setup and Operations

### **README.md** (3.0K)
Quick start guide from the original repository.

**Use this**: To understand basic usage and commands.

### **SETUP_SUMMARY.md** (2.9K)
Detailed setup instructions and verification steps.

**Use this**: When setting up the system from scratch.

Includes:
- Installation steps
- Environment setup
- Configuration
- Running commands

### **start_runner.sh** (740B)
Script to start the runner server.

```bash
./start_runner.sh
```

### **stop_runner.sh** (575B)
Script to stop the runner server.

```bash
./stop_runner.sh
```

---

## Quality and Verification

### **CODE_REVIEW.md** (5.0K)
Comprehensive code review identifying issues and recommendations.

**Read this**: To understand code quality and security.

Includes:
- 14 identified issues (categorized by priority)
- Security review
- Best practices
- Recommendations

### **FIXES_APPLIED.md** (4.2K)
Details of 8 critical fixes applied to the codebase.

**Read this**: To understand what was fixed and why.

Includes:
- Server exception handling
- Configuration validation
- Coverage display fixes
- Performance optimizations

### **VERIFICATION_REPORT.md** (3.7K)
Final verification status showing system is production-ready.

**Read this**: For confidence that the system works.

Includes:
- All tests passed
- Security review results
- Deployment checklist
- Known limitations

---

## Test Results

### **FULL_TEST_RESULTS.md** (1.9K)
Results from end-to-end testing with Docker.

Includes:
- Test execution summary
- Coverage achieved (38.10%)
- System status verification

### **TEST_RESULTS.md** (1.4K)
Server endpoint testing results.

Includes:
- Health checks
- API endpoint validation
- Error handling verification

### **ITERATE_PIPELINE_TEST.md** (1.3K)
Results from testing the iterate pipeline.

Includes:
- Iteration results
- OpenAI integration verification
- Usage examples

---

## Reading Order Recommendations

### For New Users
1. **README.md** - Understand what the system does
2. **SETUP_SUMMARY.md** - Set up the environment
3. **END_TO_END_GUIDE.md** - Run your first pipeline
4. **END_TO_END_EXAMPLE.md** - See what happens step-by-step
5. **Project.md** - Understand the research goals

### For Developers
1. **PROJECT_STATUS.md** - See what's implemented
2. **END_TO_END_EXAMPLE.md** - Understand data flow and artifacts
3. **AGENT_PROMPTS_AND_FLOW.md** - Agent interactions
4. **CODE_REVIEW.md** - Understand code quality
5. **Project.md** - Understand requirements

### For Researchers
1. **Project.md** - Research questions and goals
2. **END_TO_END_EXAMPLE.md** - Detailed run walkthrough with metrics
3. **PROJECT_STATUS.md** - Readiness for each RQ
4. **IMPLEMENTATION_SUMMARY.md** - Timeline to completion
5. **FULL_TEST_RESULTS.md** - Current performance

### For Paper Writing
1. **Project.md** - Problem statement and motivation
2. **END_TO_END_EXAMPLE.md** - Concrete example for methodology section
3. **AGENT_PROMPTS_AND_FLOW.md** - System design details
4. **LLM_SUPERVISOR_IMPLEMENTATION.md** - Novel contribution documentation

### For System Operators
1. **README.md** - Basic commands
2. **SETUP_SUMMARY.md** - Setup procedures
3. **END_TO_END_GUIDE.md** - Running pipelines
4. **start_runner.sh**, **stop_runner.sh** - Operations
5. **VERIFICATION_REPORT.md** - Troubleshooting

---

## Key Findings Summary

### Implementation Progress
- **Foundation**: 90% complete (solid!)
- **Core Features**: 40% complete (working but incomplete)
- **Research Features**: 15% complete (major gaps)

### Critical Gaps
1. **Reliability Predictor** - 0% (blocks RQ3)
2. **Entropy Tracking** - 0% (blocks RQ1 & RQ3)
3. **Mutation Integration** - 30% (incomplete RQ2)
4. **Static Analysis** - 0% (needed for reliability)

### System Health
- ✅ No critical bugs
- ✅ Production-ready infrastructure
- ✅ Robust error handling
- ✅ Security reviewed
- ✅ Working end-to-end

### Next Actions
1. Enable mutation testing (1 week)
2. Add entropy tracking (1 week)
3. Build reliability predictor (2 weeks)
4. Integrate static analysis (1-2 weeks)

---

## File Size Reference
```
END_TO_END_EXAMPLE.md      25K  - Detailed run walkthrough
PROJECT_STATUS.md          18K  - Most comprehensive
AGENT_PROMPTS_AND_FLOW.md  12K  - Agent prompts and flow
Project.md                 9.4K - Original spec
LLM_SUPERVISOR_IMPLEMENTATION.md 8K - LLM supervisor
IMPLEMENTATION_SUMMARY.md  6.7K - Quick overview
END_TO_END_GUIDE.md        5.5K - Quick pipeline guide
CODE_REVIEW.md             5.0K - Quality review
FIXES_APPLIED.md           4.2K - Applied fixes
VERIFICATION_REPORT.md     3.7K - Verification
README.md                  3.0K - Quick start
SETUP_SUMMARY.md           2.9K - Setup guide
FULL_TEST_RESULTS.md       1.9K - Test results
TEST_RESULTS.md            1.4K - API tests
ITERATE_PIPELINE_TEST.md   1.3K - Pipeline tests
```

---

## Quick Navigation

Need to know...
- **How to run it?** → README.md or END_TO_END_GUIDE.md
- **What happens during a run?** → END_TO_END_EXAMPLE.md
- **What's implemented?** → PROJECT_STATUS.md or IMPLEMENTATION_SUMMARY.md
- **What's missing?** → PROJECT_STATUS.md section 7
- **Is it safe?** → VERIFICATION_REPORT.md and CODE_REVIEW.md
- **How to advance it?** → PROJECT_STATUS.md section 13
- **Research questions?** → Project.md and PROJECT_STATUS.md section 5
- **Current performance?** → FULL_TEST_RESULTS.md
- **Agent prompts?** → AGENT_PROMPTS_AND_FLOW.md
- **LLM Supervisor?** → LLM_SUPERVISOR_IMPLEMENTATION.md

---

## Documentation Maintenance

All documentation files are up-to-date as of November 16, 2025.

When making changes:
- Update PROJECT_STATUS.md for feature additions
- Update VERIFICATION_REPORT.md after testing
- Update README.md for user-facing changes
- Keep this index synchronized

