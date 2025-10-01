# 02-SYSTEMATIC-INVESTIGATION DIRECTORY PLAN

## PURPOSE
Document the methodical approach we used to investigate AI system failures, showing scientific rigor in debugging complex systems.

## TARGET AUDIENCE VALUE PROPOSITION
- **R&D Engineer – Generative AI**: Shows research methodology applied to production AI debugging
- **AI/ML Engineer**: Demonstrates hypothesis-driven debugging of ML systems
- **Lead Software Engineer**: Shows systematic approach to complex technical investigation

## DIRECTORY CONTENTS PLANNED

### 1. hypothesis-formation.md
**What it contains:**
- The scientific method applied to AI system debugging
- How we generated testable hypotheses about failure causes
- Evolution of understanding as evidence accumulated

**Source files from our project:**
- Our conversation history where we debated different possible causes
- The progression from "Groq is broken" → "Gemini is generating bad code" → "System configuration issues" → "Basic syntax errors"
- Examples of how we tested each hypothesis systematically

**Key methodological insights:**
- Start with multiple competing hypotheses rather than tunnel vision
- Design specific tests to validate/invalidate each hypothesis
- Use production data to guide hypothesis priority
- Document failed hypotheses as much as successful ones

### 2. reproduction-strategy.md
**What it contains:**
- Step-by-step approach to reproducing production failures in controlled environments
- The evolution from simple to sophisticated test frameworks
- Challenges of reproducing AI system failures (non-deterministic behavior, environmental differences)

**Source files from our project:**
- `test_gemini_wl_comprehensive.py` - our comprehensive testing framework
- `test_production_failures.py` - our production reproduction script
- `test_gemini_wolfram_pipeline.py` - earlier test iterations
- The conversation where we realized test vs production discrepancies

**Technical evolution to highlight:**
1. Initial simple tests that missed production complexity
2. Recognition that full JSON schema reproduction was needed
3. Discovery of parameter differences (top-k, top-p, model version)
4. Iterative refinement until exact production reproduction

### 3. test-script-evolution/
**What it contains:**
- Chronological progression of our test scripts
- Commentary on why each iteration was insufficient
- Lessons learned about testing AI systems in isolation vs integrated environments

**Source files from our project:**
- `test_wolfram.py` - early simple testing
- `test_gemini_wolfram_pipeline.py` - intermediate complexity
- `test_gemini_wl_comprehensive.py` - comprehensive model comparison
- `test_production_failures.py` - exact production reproduction
- Our conversation documenting why each approach was inadequate

**Subfiles planned:**
- `iteration-1-simple-tests.py` (based on test_wolfram.py)
- `iteration-2-model-comparison.py` (based on test_gemini_wl_comprehensive.py)
- `iteration-3-production-reproduction.py` (based on test_production_failures.py)
- `evolution-commentary.md` - lessons learned from each iteration

## VALUE DEMONSTRATION
This directory shows:
1. **Scientific Rigor**: Hypothesis-driven debugging, not random trial-and-error
2. **Test Design Skills**: Ability to design tests that actually reproduce production issues
3. **Iterative Learning**: Adapting approach based on evidence
4. **AI System Understanding**: Knowledge of how AI systems behave differently in different contexts

## STORY ARC FOR THIS DIRECTORY
"Faced with production AI failures, I didn't just start randomly changing things. I developed competing hypotheses about what could be wrong, designed specific tests to validate each hypothesis, and iteratively refined my testing approach when initial tests failed to reproduce production behavior. This systematic investigation revealed that testing AI systems requires understanding the full production context, not just the AI components in isolation."

## TECHNICAL CHALLENGES TO HIGHLIGHT
1. **Non-deterministic AI behavior**: How to test systems that don't give consistent outputs
2. **Environmental complexity**: Production vs test environment differences
3. **Multi-component debugging**: Isolating failures in AI + API + formatting pipelines
4. **Configuration sensitivity**: How small parameter differences create large behavior changes

## FILES NEEDED FROM CURRENT PROJECT
1. All test scripts: `test_*.py` files
2. Our conversation history documenting the evolution of our understanding
3. The specific moments where we realized our tests were inadequate
4. Examples of failed reproduction attempts and what they taught us

## METHODOLOGY FRAMEWORKS TO EXTRACT
1. **Hypothesis Generation Framework**: How to systematically think about AI failure modes
2. **Test Design Framework**: How to design tests that actually reveal production issues  
3. **Investigation Iteration Framework**: How to evolve testing based on evidence
4. **AI System Testing Principles**: Unique considerations for testing AI vs traditional software

## ANONYMIZATION STRATEGY
- Keep all technical methodology intact
- Replace domain-specific examples with generic ones
- Focus on the process rather than the specific content
- Highlight transferable debugging skills

## INTERVIEW TALKING POINTS FROM THIS DIRECTORY
- "Here's how I approach debugging complex AI systems systematically"
- "I learned that testing AI systems requires different approaches than traditional software"
- "Let me show you how I evolved my testing strategy based on evidence"
- "This is how I balance scientific rigor with production pressure"
