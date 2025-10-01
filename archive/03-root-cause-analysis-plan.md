# 03-ROOT-CAUSE-ANALYSIS DIRECTORY PLAN

## PURPOSE
Document the multi-layered root cause analysis that revealed failures at AI model level, system integration level, and basic deployment level.

## TARGET AUDIENCE VALUE PROPOSITION
- **R&D Engineer – Generative AI**: Shows deep understanding of AI system failure modes and their interactions
- **AI/ML Engineer**: Demonstrates ability to diagnose AI failures vs system failures vs configuration failures
- **Lead Software Engineer**: Shows systematic debugging of complex multi-component systems

## DIRECTORY CONTENTS PLANNED

### 1. ai-model-issues.md
**What it contains:**
- Analysis of AI model configuration problems discovered
- Parameter sensitivity analysis (temperature, top-k, top-p effects)
- Model version differences and their impact
- Prompt engineering failure modes

**Source files from our project:**
- Our discovery that production used `gemini-2.5-flash-lite-preview-06-17` vs test `gemini-2.5-flash-lite`
- Analysis of top-k=40, top-p=0.95 parameter impacts
- `backend/shared-libs/system_prompts.py` - prompt engineering evolution
- `backend/shared-libs/llm_service.py` - model configuration details
- The conversation where we discovered parameter mismatches

**Technical insights to highlight:**
- How small parameter differences (top-k, top-p) dramatically affect AI behavior
- The difference between model capabilities and model configuration
- Why AI system testing requires exact production parameter reproduction
- Cognitive load effects on AI performance (simple vs complex JSON schema)

### 2. system-integration-problems.md
**What it contains:**
- Analysis of API integration failures between components
- Data format mismatches and parsing errors
- Error handling inadequacies in multi-AI-system pipelines
- Race conditions and timing issues in async AI operations

**Source files from our project:**
- `backend/mcp-service/src/services/wolfram_service.py` - Wolfram API integration issues
- `backend/mcp-service/src/intelligent_question_generator.py` - complex JSON schema handling
- The deterministic formatting solution vs Groq formatting approach
- Examples of malformed Wolfram outputs: `_b*(a_over)`, `x /. First[5]`, etc.

**Integration failure patterns to document:**
1. **AI API Response Parsing**: Malformed JSON, unexpected formats, partial responses
2. **Multi-AI Coordination**: Gemini → Wolfram Eval → Groq formatting pipeline failures
3. **Error Propagation**: How failures cascade through AI system components
4. **Async Operation Issues**: Timeout handling, concurrent request management

### 3. deployment-failures.md
**What it contains:**
- Infrastructure and deployment issues that prevented the system from working
- Container startup failures and their diagnosis
- Basic syntax errors that blocked deployment
- Cloud Run debugging methodology

**Source files from our project:**
- `backend/mcp-service/src/database.py` - the IndentationError and SyntaxError fixes
- Cloud Run deployment logs and our debugging process
- The conversation where we diagnosed container startup failures
- `backend/mcp-service/Dockerfile` - containerization configuration

**Deployment failure analysis:**
1. **Basic Syntax Errors**: IndentationError at line 355, SyntaxError at line 192
2. **Container Startup Issues**: Port 8080 binding failures, health check timeouts
3. **Environment Configuration**: Missing environment variables, service dependencies
4. **Infrastructure Dependencies**: Redis connection issues, Supabase configuration

## VALUE DEMONSTRATION
This directory shows:
1. **Multi-Level Debugging**: Can diagnose issues from basic syntax to complex AI behavior
2. **System Thinking**: Understanding how different failure types interact and compound
3. **Production Experience**: Real production failures with real business impact
4. **Technical Breadth**: AI/ML + Backend + DevOps + Infrastructure knowledge

## STORY ARC FOR THIS DIRECTORY
"What initially appeared to be 'AI giving wrong answers' turned out to be a perfect storm of failures at multiple levels: the deployed code had basic Python syntax errors preventing startup, the working AI had configuration mismatches affecting behavior, the system integration had parsing failures between components, and the deployment pipeline had infrastructure issues. Each layer of failure masked the others, requiring systematic investigation to uncover the full picture."

## TECHNICAL DEPTH TO SHOWCASE

### AI Model Issues (Advanced):
- Parameter sensitivity analysis (temperature/top-k/top-p effects)
- Model version differences and their behavioral impacts
- Cognitive load effects on AI performance
- Prompt engineering optimization strategies

### System Integration Issues (Expert):
- Multi-AI system coordination challenges
- Error handling in non-deterministic systems
- Async operation management with AI APIs
- Data format validation and parsing robustness

### Deployment Issues (Production-Ready):
- Container debugging methodology
- Cloud Run troubleshooting
- Infrastructure dependency management
- Production monitoring and alerting

## FILES NEEDED FROM CURRENT PROJECT
1. `backend/mcp-service/src/services/wolfram_service.py` - API integration complexity
2. `backend/mcp-service/src/intelligent_question_generator.py` - JSON schema handling
3. `backend/shared-libs/llm_service.py` - model configuration details
4. `backend/shared-libs/system_prompts.py` - prompt engineering evolution
5. `backend/mcp-service/src/database.py` - syntax error examples
6. Our conversation history documenting each discovery
7. Cloud Run deployment logs and debugging process

## ROOT CAUSE CATEGORIZATION FRAMEWORK

### Level 1: Infrastructure Failures
- Container startup issues
- Network connectivity problems
- Resource allocation failures
- Environment configuration errors

### Level 2: System Integration Failures  
- API integration mismatches
- Data format incompatibilities
- Error handling inadequacies
- Timing and concurrency issues

### Level 3: AI Model Failures
- Parameter configuration issues
- Model version inconsistencies
- Prompt engineering problems
- Context and cognitive load effects

### Level 4: Business Logic Failures
- Algorithm correctness issues
- Mathematical validation problems
- Domain-specific logic errors
- User experience impact

## INTERVIEW TALKING POINTS FROM THIS DIRECTORY
- "Here's how I diagnosed failures across multiple system layers simultaneously"
- "I learned that AI system failures often have compound causes requiring multi-level investigation"
- "Let me show you how I differentiated between AI model issues vs system integration issues"
- "This taught me that production AI reliability requires attention to infrastructure, integration, and AI configuration"

## ANONYMIZATION STRATEGY
- Keep all technical details about debugging methodology
- Replace domain-specific business logic with generic examples
- Focus on system architecture patterns rather than educational content
- Highlight transferable debugging skills across different AI application domains
