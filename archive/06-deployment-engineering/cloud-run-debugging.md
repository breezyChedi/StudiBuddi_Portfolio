# Cloud Run Debugging for AI Systems

## Overview

This document provides a comprehensive guide to debugging Google Cloud Run deployments specifically for AI systems, based on real-world experience debugging production deployment failures. AI services present unique challenges in containerized environments that require specialized debugging approaches.

## Cloud Run Deployment Failure Categories

### Category 1: Build-Time Failures
**Characteristics**: Failures during the container image build process
**Common Causes**: Dockerfile errors, dependency resolution issues, source code problems
**Detection**: Build logs show compilation or packaging errors

```bash
# Example build failure investigation
gcloud builds logs <build-id>

# Sample error pattern:
# Step #1 - "builder": ERROR: Could not find a version that satisfies the requirement torch==2.0.1
# Step #1 - "builder": No matching distribution found for torch==2.0.1
```

#### Common Build-Time Issues for AI Services

**1. Large AI Dependencies**
```dockerfile
# PROBLEMATIC: Can cause timeout or memory issues
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt  # Timeout on large AI packages

# OPTIMIZED: Multi-stage build with dependency caching
FROM python:3.11-slim as deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ ./src/
```

**2. Platform-Specific AI Libraries**
```dockerfile
# ISSUE: AI libraries often have platform-specific builds
RUN pip install tensorflow  # May install wrong architecture

# SOLUTION: Explicit platform specification
RUN pip install tensorflow --platform linux_x86_64 --only-binary=all
```

### Category 2: Runtime Startup Failures
**Characteristics**: Container builds successfully but fails to start
**Common Causes**: Application syntax errors, missing environment variables, resource limits
**Detection**: Container startup logs show application initialization errors

#### Debugging Runtime Failures

**Investigation Command Sequence**:
```bash
# 1. Check service status
gcloud run services describe mcp-service --region=africa-south1 --format="value(status)"

# 2. Get revision status
gcloud run revisions describe mcp-service-<revision> --region=africa-south1

# 3. Extract startup logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=mcp-service" \
  --limit=50 --format="table(timestamp,severity,textPayload)" --freshness=1h
```

#### Real-World Example: Python Syntax Error Debugging

**Symptom**: 
```
Default STARTUP TCP probe failed 1 time consecutively for container
Container failed to start and listen on the port defined by the PORT environment variable
```

**Log Analysis**:
```bash
# Extract detailed startup logs
gcloud logging read "resource.type=cloud_run_revision" \
  --filter="resource.labels.service_name=mcp-service" \
  --limit=100 --format="value(textPayload)"

# Key error found:
File "/app/src/database.py", line 192
    await self.redis_client.close()
        ^^^^^
SyntaxError: expected 'except' or 'finally' block
```

**Root Cause Analysis**:
```python
# PROBLEMATIC CODE (line 189-194):
try:
    if self.redis_client:
        logger.info("Closing Redis connection...")
await self.redis_client.close()  # WRONG INDENTATION!
    logger.info("Redis connection closed")
except Exception as e:
    logger.error(f"Error closing Redis connection: {e}")
```

**Fix Applied**:
```python
# CORRECTED CODE:
try:
    if self.redis_client:
        logger.info("Closing Redis connection...")
        await self.redis_client.close()  # PROPER INDENTATION
        logger.info("Redis connection closed")
except Exception as e:
    logger.error(f"Error closing Redis connection: {e}")
```

**Validation Process**:
```bash
# 1. Test fix locally
python -m py_compile src/database.py

# 2. Deploy with monitoring
gcloud run deploy mcp-service --source . --region=africa-south1

# 3. Monitor deployment
watch -n 5 'gcloud run services describe mcp-service --region=africa-south1 --format="value(status.conditions[0].status,status.conditions[0].message)"'
```

### Category 3: Health Check Failures
**Characteristics**: Container starts but fails health checks
**Common Causes**: Slow AI model loading, incorrect port configuration, resource exhaustion
**Detection**: Health check probe failures in logs

#### AI-Specific Health Check Configuration

**Challenge**: AI services often have long startup times due to model loading

```yaml
# Cloud Run service configuration
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: ai-service
spec:
  template:
    metadata:
      annotations:
        # CRITICAL: Extended timeout for AI model loading
        run.googleapis.com/timeout: "900"  # 15 minutes
        run.googleapis.com/startup-cpu-boost: "true"
    spec:
      containers:
      - image: gcr.io/project/ai-service
        ports:
        - containerPort: 8080
        # AI-specific resource requirements
        resources:
          limits:
            cpu: "4"
            memory: "8Gi"
          requests:
            cpu: "2"
            memory: "4Gi"
        # Health check configuration for AI services
        startupProbe:
          httpGet:
            path: /health/startup
            port: 8080
          initialDelaySeconds: 60    # Allow time for AI model loading
          timeoutSeconds: 30
          periodSeconds: 10
          failureThreshold: 18       # 3 minutes total (18 * 10s)
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 5
          timeoutSeconds: 5
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 120   # Wait for full startup
          timeoutSeconds: 10
          periodSeconds: 30
```

#### Implementing AI-Aware Health Checks

```python
class AIServiceHealthCheck:
    def __init__(self, ai_model_manager):
        self.ai_model_manager = ai_model_manager
        self.startup_complete = False
        
    async def startup_health_check(self):
        """Health check for AI service startup phase."""
        health_status = {
            "status": "healthy",
            "startup_complete": self.startup_complete,
            "components": {}
        }
        
        try:
            # Check basic container health
            health_status["components"]["container"] = {"status": "healthy"}
            
            # Check database connections
            db_health = await self._check_database_health()
            health_status["components"]["database"] = db_health
            
            if not db_health["healthy"]:
                health_status["status"] = "unhealthy"
                return health_status
            
            # Check AI model loading (most time-consuming)
            model_health = await self._check_ai_model_health()
            health_status["components"]["ai_models"] = model_health
            
            if model_health["healthy"]:
                self.startup_complete = True
                health_status["startup_complete"] = True
            else:
                health_status["status"] = "starting"  # Still loading
            
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "startup_complete": False
            }
    
    async def _check_ai_model_health(self):
        """Check if AI models are loaded and ready."""
        try:
            # Test model loading
            model_status = await self.ai_model_manager.health_check()
            
            if model_status.get("loaded"):
                # Quick inference test
                test_result = await self.ai_model_manager.quick_test()
                return {
                    "healthy": test_result.get("success", False),
                    "models_loaded": model_status.get("model_count", 0),
                    "last_test": test_result.get("timestamp"),
                    "inference_time_ms": test_result.get("duration_ms", 0)
                }
            else:
                return {
                    "healthy": False,
                    "status": "loading",
                    "progress": model_status.get("loading_progress", 0)
                }
                
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def readiness_health_check(self):
        """Health check for service readiness to accept traffic."""
        if not self.startup_complete:
            return {"status": "not_ready", "reason": "startup_not_complete"}
        
        # Quick checks for ongoing readiness
        checks = [
            self._check_memory_usage(),
            self._check_ai_model_availability(),
            self._check_external_dependencies()
        ]
        
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        all_healthy = all(r.get("healthy", False) for r in results if isinstance(r, dict))
        
        return {
            "status": "ready" if all_healthy else "not_ready",
            "component_checks": results
        }
```

## Cloud Run Resource Configuration for AI Workloads

### Memory and CPU Optimization

**AI Service Resource Patterns**:
```python
def calculate_ai_service_resources(model_type, expected_concurrency):
    """Calculate appropriate resources for AI service."""
    
    base_requirements = {
        "llm_small": {"cpu": 1, "memory": "2Gi", "startup_time": 30},
        "llm_medium": {"cpu": 2, "memory": "4Gi", "startup_time": 60},
        "llm_large": {"cpu": 4, "memory": "8Gi", "startup_time": 120},
        "multimodal": {"cpu": 4, "memory": "16Gi", "startup_time": 180}
    }
    
    base = base_requirements.get(model_type, base_requirements["llm_medium"])
    
    # Scale for concurrency
    cpu_scaling = min(expected_concurrency, 4)  # Cloud Run CPU limit
    memory_scaling = expected_concurrency * 0.5  # Memory per concurrent request
    
    return {
        "cpu": str(min(base["cpu"] * cpu_scaling, 8)),
        "memory": f"{int(base['memory'].rstrip('Gi')) + memory_scaling}Gi",
        "startup_timeout": base["startup_time"] + (expected_concurrency * 5),
        "request_timeout": 900  # 15 minutes for AI processing
    }
```

### Cold Start Optimization

**Problem**: AI services have significant cold start times due to model loading

**Solution Strategies**:

#### 1. Startup CPU Boost
```yaml
annotations:
  run.googleapis.com/startup-cpu-boost: "true"  # Extra CPU during startup
  run.googleapis.com/execution-environment: gen2  # Better performance
```

#### 2. Minimum Instance Configuration
```yaml
annotations:
  run.googleapis.com/min-instances: "1"  # Keep at least one instance warm
  run.googleapis.com/max-instances: "10"  # Scale up to 10 instances
```

#### 3. Model Loading Optimization
```python
class OptimizedAIModelLoader:
    def __init__(self):
        self.models = {}
        self.loading_started = False
        
    async def start_background_loading(self):
        """Start model loading in background during container startup."""
        if not self.loading_started:
            self.loading_started = True
            # Start loading immediately, don't wait for first request
            asyncio.create_task(self._load_all_models())
    
    async def _load_all_models(self):
        """Load AI models in parallel where possible."""
        loading_tasks = [
            self._load_model("text_generation"),
            self._load_model("text_analysis"),
            # Load independent models in parallel
        ]
        
        await asyncio.gather(*loading_tasks, return_exceptions=True)
        
    async def _load_model(self, model_type):
        """Load individual model with progress tracking."""
        try:
            start_time = time.time()
            logger.info(f"Starting {model_type} model loading...")
            
            # Actual model loading logic here
            model = await self._load_model_implementation(model_type)
            
            load_time = time.time() - start_time
            logger.info(f"{model_type} model loaded in {load_time:.2f}s")
            
            self.models[model_type] = model
            return model
            
        except Exception as e:
            logger.error(f"Failed to load {model_type} model: {e}")
            raise
```

## Deployment Monitoring and Alerting

### Real-Time Deployment Monitoring

```python
class CloudRunDeploymentMonitor:
    def __init__(self, project_id, region, service_name):
        self.project_id = project_id
        self.region = region
        self.service_name = service_name
        
    async def monitor_deployment(self, timeout_minutes=15):
        """Monitor deployment progress with real-time status updates."""
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while (time.time() - start_time) < timeout_seconds:
            status = await self._get_service_status()
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Deployment Status: {status['state']}")
            
            if status["state"] == "READY":
                print("✅ Deployment successful!")
                return {"success": True, "duration": time.time() - start_time}
            elif status["state"] == "FAILED":
                print("❌ Deployment failed!")
                error_details = await self._get_failure_details()
                return {"success": False, "error": error_details}
            
            # Show progress indicators
            if status.get("conditions"):
                for condition in status["conditions"]:
                    if condition.get("message"):
                        print(f"   📋 {condition['type']}: {condition['message']}")
            
            await asyncio.sleep(10)  # Check every 10 seconds
        
        return {"success": False, "error": "Deployment timeout"}
    
    async def _get_service_status(self):
        """Get current Cloud Run service status."""
        # Implementation would use Cloud Run API or gcloud CLI
        import subprocess
        
        cmd = [
            "gcloud", "run", "services", "describe", self.service_name,
            "--region", self.region,
            "--format", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            service_data = json.loads(result.stdout)
            return {
                "state": service_data["status"]["conditions"][0]["status"],
                "conditions": service_data["status"]["conditions"]
            }
        else:
            return {"state": "UNKNOWN", "error": result.stderr}
```

### Automated Rollback Detection

```python
class DeploymentHealthValidator:
    def __init__(self, service_url, health_endpoints):
        self.service_url = service_url
        self.health_endpoints = health_endpoints
        
    async def validate_deployment_health(self, validation_duration_minutes=10):
        """Validate deployment health over time to detect issues."""
        
        validation_results = {
            "start_time": datetime.utcnow(),
            "duration_minutes": validation_duration_minutes,
            "health_checks": [],
            "overall_health": True,
            "issues_detected": []
        }
        
        start_time = time.time()
        validation_duration = validation_duration_minutes * 60
        
        while (time.time() - start_time) < validation_duration:
            health_result = await self._perform_health_check()
            validation_results["health_checks"].append(health_result)
            
            # Check for concerning patterns
            recent_checks = validation_results["health_checks"][-5:]  # Last 5 checks
            
            if len(recent_checks) >= 3:
                failure_rate = sum(1 for check in recent_checks if not check["healthy"]) / len(recent_checks)
                
                if failure_rate > 0.4:  # 40% failure rate
                    validation_results["overall_health"] = False
                    validation_results["issues_detected"].append({
                        "type": "high_failure_rate",
                        "failure_rate": failure_rate,
                        "timestamp": datetime.utcnow()
                    })
                    break
            
            await asyncio.sleep(30)  # Check every 30 seconds
        
        return validation_results
    
    async def _perform_health_check(self):
        """Perform comprehensive health check."""
        check_result = {
            "timestamp": datetime.utcnow(),
            "healthy": True,
            "endpoint_results": {},
            "response_times": {}
        }
        
        for endpoint_name, endpoint_path in self.health_endpoints.items():
            try:
                start_time = time.time()
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.service_url}{endpoint_path}",
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response_time = (time.time() - start_time) * 1000
                        
                        check_result["response_times"][endpoint_name] = response_time
                        
                        if response.status == 200:
                            check_result["endpoint_results"][endpoint_name] = "healthy"
                        else:
                            check_result["endpoint_results"][endpoint_name] = f"unhealthy_{response.status}"
                            check_result["healthy"] = False
                            
            except Exception as e:
                check_result["endpoint_results"][endpoint_name] = f"error_{str(e)}"
                check_result["healthy"] = False
        
        return check_result
```

## Debugging Command Toolkit

### Essential Cloud Run Debugging Commands

```bash
#!/bin/bash
# Cloud Run AI Service Debugging Toolkit

# 1. Quick Status Check
function cr_status() {
    local service=$1
    local region=${2:-"us-central1"}
    
    gcloud run services describe $service --region=$region \
        --format="table(metadata.name,status.conditions[0].type,status.conditions[0].status,status.conditions[0].message)"
}

# 2. Get Recent Logs
function cr_logs() {
    local service=$1
    local region=${2:-"us-central1"}
    local hours=${3:-"1"}
    
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$service" \
        --limit=100 \
        --freshness="${hours}h" \
        --format="table(timestamp,severity,textPayload)" \
        --sort-by="timestamp"
}

# 3. Monitor Deployment
function cr_deploy_monitor() {
    local service=$1
    local region=${2:-"us-central1"}
    
    echo "Monitoring deployment of $service..."
    
    while true; do
        status=$(gcloud run services describe $service --region=$region --format="value(status.conditions[0].status)")
        message=$(gcloud run services describe $service --region=$region --format="value(status.conditions[0].message)")
        
        echo "[$(date +'%H:%M:%S')] Status: $status - $message"
        
        if [[ "$status" == "True" ]]; then
            echo "✅ Deployment successful!"
            break
        elif [[ "$status" == "False" ]]; then
            echo "❌ Deployment failed!"
            break
        fi
        
        sleep 10
    done
}

# 4. Health Check Testing
function cr_health_test() {
    local service_url=$1
    local endpoint=${2:-"/health"}
    
    echo "Testing health endpoint: $service_url$endpoint"
    
    for i in {1..5}; do
        echo "Test $i:"
        curl -w "Response Time: %{time_total}s\nHTTP Code: %{http_code}\n" \
             -s -o /dev/null \
             "$service_url$endpoint"
        echo "---"
        sleep 2
    done
}

# 5. Resource Usage Analysis
function cr_metrics() {
    local service=$1
    local region=${2:-"us-central1"}
    
    echo "Recent resource usage for $service:"
    
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$service" \
        --filter="jsonPayload.message:\"memory\" OR jsonPayload.message:\"cpu\"" \
        --limit=20 \
        --format="table(timestamp,jsonPayload.message)"
}
```

### Troubleshooting Decision Tree

```python
class CloudRunTroubleshooter:
    def __init__(self, service_name, region):
        self.service_name = service_name
        self.region = region
        
    async def diagnose_deployment_issue(self):
        """Systematic diagnosis of Cloud Run deployment issues."""
        
        diagnosis = {
            "service": self.service_name,
            "region": self.region,
            "timestamp": datetime.utcnow(),
            "issue_category": None,
            "root_cause": None,
            "recommended_actions": []
        }
        
        # Step 1: Check if service exists and get basic status
        service_status = await self._get_service_status()
        
        if not service_status["exists"]:
            diagnosis["issue_category"] = "service_not_found"
            diagnosis["recommended_actions"] = ["Verify service name and region", "Check deployment logs"]
            return diagnosis
        
        # Step 2: Analyze current condition
        if service_status["ready"]:
            diagnosis["issue_category"] = "service_healthy"
            diagnosis["recommended_actions"] = ["No issues detected"]
            return diagnosis
        
        # Step 3: Get detailed error information
        error_details = await self._analyze_error_conditions(service_status)
        
        # Step 4: Categorize the issue
        if "ContainerStarting" in error_details["condition_types"]:
            diagnosis.update(await self._diagnose_startup_issues())
        elif "RevisionFailed" in error_details["condition_types"]:
            diagnosis.update(await self._diagnose_revision_issues())
        elif "ConfigurationReady" in error_details["condition_types"]:
            diagnosis.update(await self._diagnose_configuration_issues())
        else:
            diagnosis["issue_category"] = "unknown"
            diagnosis["recommended_actions"] = ["Check Cloud Run documentation", "Contact support"]
        
        return diagnosis
    
    async def _diagnose_startup_issues(self):
        """Diagnose container startup problems."""
        
        # Get startup logs
        startup_logs = await self._get_startup_logs()
        
        issue_patterns = {
            "syntax_error": {
                "patterns": ["SyntaxError", "IndentationError", "invalid syntax"],
                "category": "application_code_error",
                "actions": ["Fix Python syntax errors", "Test code locally", "Review recent changes"]
            },
            "import_error": {
                "patterns": ["ImportError", "ModuleNotFoundError", "No module named"],
                "category": "dependency_error", 
                "actions": ["Check requirements.txt", "Verify dependencies are installed", "Check Python path"]
            },
            "connection_error": {
                "patterns": ["Connection refused", "timeout", "Unable to connect"],
                "category": "external_dependency_error",
                "actions": ["Check database connections", "Verify API endpoints", "Check network configuration"]
            },
            "memory_error": {
                "patterns": ["MemoryError", "out of memory", "OOM"],
                "category": "resource_constraint",
                "actions": ["Increase memory allocation", "Optimize memory usage", "Check for memory leaks"]
            }
        }
        
        for error_type, config in issue_patterns.items():
            if any(pattern in startup_logs for pattern in config["patterns"]):
                return {
                    "issue_category": config["category"],
                    "root_cause": error_type,
                    "recommended_actions": config["actions"]
                }
        
        return {
            "issue_category": "startup_failure",
            "root_cause": "unknown_startup_error",
            "recommended_actions": ["Review startup logs", "Check application initialization"]
        }
```

## Best Practices for AI Service Deployment

### 1. Pre-Deployment Validation Checklist

```python
class AIServiceDeploymentValidator:
    def __init__(self):
        self.validation_checks = [
            self._validate_python_syntax,
            self._validate_dependencies,
            self._validate_environment_config,
            self._validate_resource_requirements,
            self._validate_health_endpoints,
            self._validate_ai_model_accessibility
        ]
    
    async def validate_pre_deployment(self, source_path):
        """Run all pre-deployment validations."""
        
        validation_results = {
            "overall_status": "PASS",
            "check_results": {},
            "blocking_issues": [],
            "warnings": []
        }
        
        for check in self.validation_checks:
            check_name = check.__name__
            try:
                result = await check(source_path)
                validation_results["check_results"][check_name] = result
                
                if not result["passed"]:
                    validation_results["overall_status"] = "FAIL"
                    validation_results["blocking_issues"].extend(result.get("errors", []))
                
                validation_results["warnings"].extend(result.get("warnings", []))
                
            except Exception as e:
                validation_results["check_results"][check_name] = {
                    "passed": False,
                    "error": str(e)
                }
                validation_results["overall_status"] = "FAIL"
                validation_results["blocking_issues"].append(f"{check_name} validation failed: {e}")
        
        return validation_results
    
    async def _validate_python_syntax(self, source_path):
        """Validate Python syntax in all source files."""
        import ast
        import os
        
        result = {"passed": True, "errors": [], "warnings": []}
        
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                        
                        # Check syntax
                        ast.parse(content)
                        
                        # Check for common issues
                        if 'await ' in content and 'async def' not in content:
                            result["warnings"].append(f"{file_path}: await used outside async function")
                        
                    except SyntaxError as e:
                        result["passed"] = False
                        result["errors"].append(f"{file_path}:{e.lineno}: {e.msg}")
                    except Exception as e:
                        result["warnings"].append(f"{file_path}: Could not validate - {e}")
        
        return result
```

### 2. Deployment Pipeline Integration

```yaml
# .github/workflows/ai-service-deploy.yml
name: AI Service Deployment

on:
  push:
    branches: [main]

jobs:
  validate-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    # AI-specific validation steps
    - name: Validate Python syntax
      run: |
        python -m py_compile $(find src -name "*.py")
    
    - name: Test AI dependencies
      run: |
        pip install -r requirements.txt
        python -c "import torch; import transformers; print('AI dependencies OK')"
    
    - name: Run AI service tests
      run: |
        python -m pytest tests/ -v --tb=short
    
    # Cloud Run deployment
    - name: Deploy to Cloud Run
      run: |
        gcloud run deploy ai-service \
          --source . \
          --region=us-central1 \
          --platform=managed \
          --memory=8Gi \
          --cpu=4 \
          --timeout=900 \
          --max-instances=10 \
          --min-instances=1
    
    # Post-deployment validation
    - name: Validate deployment
      run: |
        # Wait for deployment to stabilize
        sleep 60
        
        # Test health endpoints
        SERVICE_URL=$(gcloud run services describe ai-service --region=us-central1 --format="value(status.url)")
        curl -f $SERVICE_URL/health || exit 1
        curl -f $SERVICE_URL/health/ai || exit 1
```

This comprehensive guide provides the foundation for debugging and deploying AI services on Cloud Run, addressing the unique challenges these systems present in containerized cloud environments.
