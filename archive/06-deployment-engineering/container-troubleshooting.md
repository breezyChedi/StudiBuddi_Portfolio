# Container Troubleshooting for AI Systems

## Overview

This document provides comprehensive guidance for troubleshooting containerized AI applications, based on real-world experience debugging production deployment failures. AI systems present unique containerization challenges due to large dependencies, complex runtime requirements, and resource-intensive operations.

## Container Failure Categories for AI Systems

### Category 1: Image Build Failures

#### Large Dependency Resolution Issues
**Problem**: AI libraries (PyTorch, TensorFlow, etc.) are large and often have complex dependency trees
**Symptoms**: Build timeouts, dependency conflicts, out-of-space errors during build

```dockerfile
# PROBLEMATIC: Can cause build failures
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt  # May timeout or run out of space

# OPTIMIZED: Multi-stage build with dependency management
FROM python:3.11-slim as base

# Install system dependencies first
RUN apt-get update && apt-get install -y \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

FROM base as dependencies
COPY requirements.txt .

# Install dependencies with proper caching and optimization
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

FROM base as runtime
# Copy only the installed packages, not the build artifacts
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
WORKDIR /app

# Set proper Python path and environment
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

# Health check for container readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "src/main.py"]
```

#### Platform-Specific AI Library Issues
```dockerfile
# ISSUE: AI libraries often built for specific platforms
FROM python:3.11-slim

# PROBLEMATIC: May install wrong architecture binaries
RUN pip install torch torchvision

# SOLUTION: Explicit platform targeting
FROM python:3.11-slim

# Install with explicit platform specification
RUN pip install torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu \
    --platform linux_x86_64 \
    --only-binary=all

# Alternative: Use official AI-optimized base images
# FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime
```

### Category 2: Runtime Startup Failures

#### Python Syntax Errors Preventing Container Start
**Real-world Example from Production**:

**Symptom**:
```
Container failed to start and listen on the port defined by the PORT environment variable
Default STARTUP TCP probe failed 1 time consecutively
```

**Investigation Process**:
```bash
# 1. Build container locally to test
docker build -t ai-service-debug .

# 2. Run container with debugging
docker run -it --rm -p 8080:8080 ai-service-debug

# Output showed:
# File "/app/src/database.py", line 192
#     await self.redis_client.close()
#         ^^^^^
# SyntaxError: expected 'except' or 'finally' block
```

**Root Cause Analysis**:
```python
# PROBLEMATIC CODE in src/database.py:
try:
    if self.redis_client:
        logger.info("Closing Redis connection...")
await self.redis_client.close()  # WRONG INDENTATION - outside try block!
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

**Container Validation Process**:
```bash
# Create validation script
cat > validate_container.sh << 'EOF'
#!/bin/bash
set -e

echo "🔍 Validating container build and startup..."

# 1. Syntax validation during build
echo "Step 1: Building container with syntax validation..."
docker build --target syntax-check -t ai-service-syntax-check . || {
    echo "❌ Syntax validation failed during build"
    exit 1
}

# 2. Full container build
echo "Step 2: Building full container..."
docker build -t ai-service-test . || {
    echo "❌ Container build failed"
    exit 1
}

# 3. Test container startup
echo "Step 3: Testing container startup..."
timeout 60s docker run --rm -d --name ai-service-test-instance \
    -p 8080:8080 \
    -e PORT=8080 \
    ai-service-test || {
    echo "❌ Container startup failed"
    docker logs ai-service-test-instance 2>/dev/null || true
    exit 1
}

# 4. Wait for service to be ready
echo "Step 4: Waiting for service readiness..."
for i in {1..30}; do
    if curl -sf http://localhost:8080/health >/dev/null 2>&1; then
        echo "✅ Service is ready!"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo "❌ Service failed to become ready"
        docker logs ai-service-test-instance
        docker stop ai-service-test-instance
        exit 1
    fi
    
    sleep 2
done

# Cleanup
docker stop ai-service-test-instance
echo "✅ Container validation successful!"
EOF

chmod +x validate_container.sh
```

#### Enhanced Dockerfile with Validation Stages
```dockerfile
# Multi-stage Dockerfile with validation
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Syntax validation stage
FROM base as syntax-check
COPY src/ ./src/
# Validate Python syntax during build
RUN python -m py_compile $(find src -name "*.py") || \
    (echo "❌ Python syntax errors found!" && exit 1)

# Dependencies stage
FROM base as dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Import test stage
FROM dependencies as import-test
COPY src/ ./src/
# Test that all imports work
RUN python -c "
import sys
sys.path.insert(0, './src')
try:
    import main
    import database
    import services.wolfram_service
    print('✅ All imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

# Final runtime stage
FROM dependencies as runtime
COPY src/ ./src/
WORKDIR /app

# Environment configuration
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE ${PORT}

CMD ["python", "src/main.py"]
```

### Category 3: Runtime Configuration Issues

#### Environment Variable and Secrets Management
```python
class ContainerEnvironmentValidator:
    """Validate container environment configuration for AI services."""
    
    def __init__(self):
        self.required_vars = [
            "PORT", "REDIS_URL", "SUPABASE_URL", "SUPABASE_ANON_KEY",
            "GEMINI_API_KEY", "WOLFRAM_APP_ID"
        ]
        self.optional_vars = {
            "LOG_LEVEL": "INFO",
            "MAX_WORKERS": "4",
            "REQUEST_TIMEOUT": "300"
        }
    
    def validate_environment(self):
        """Validate all required environment variables are present."""
        validation_result = {
            "valid": True,
            "missing_required": [],
            "missing_optional": [],
            "configuration_issues": []
        }
        
        # Check required variables
        for var in self.required_vars:
            value = os.getenv(var)
            if not value:
                validation_result["valid"] = False
                validation_result["missing_required"].append(var)
            else:
                # Validate specific formats
                issue = self._validate_variable_format(var, value)
                if issue:
                    validation_result["configuration_issues"].append(issue)
        
        # Check optional variables
        for var, default in self.optional_vars.items():
            if not os.getenv(var):
                validation_result["missing_optional"].append(f"{var} (using default: {default})")
        
        return validation_result
    
    def _validate_variable_format(self, var_name, value):
        """Validate specific environment variable formats."""
        
        if var_name == "PORT":
            try:
                port = int(value)
                if not (1 <= port <= 65535):
                    return f"PORT {port} is not in valid range (1-65535)"
            except ValueError:
                return f"PORT '{value}' is not a valid integer"
        
        elif var_name in ["REDIS_URL", "SUPABASE_URL"]:
            if not value.startswith(("http://", "https://", "redis://", "rediss://")):
                return f"{var_name} '{value}' does not appear to be a valid URL"
        
        elif var_name.endswith("_API_KEY"):
            if len(value) < 10:  # Basic length check
                return f"{var_name} appears to be too short"
        
        return None

# Usage in container startup
def validate_container_environment():
    """Validate container environment on startup."""
    validator = ContainerEnvironmentValidator()
    result = validator.validate_environment()
    
    if not result["valid"]:
        logger.error("❌ Container environment validation failed!")
        for var in result["missing_required"]:
            logger.error(f"   Missing required variable: {var}")
        for issue in result["configuration_issues"]:
            logger.error(f"   Configuration issue: {issue}")
        
        sys.exit(1)
    
    if result["missing_optional"]:
        logger.warning("⚠️  Using default values for optional variables:")
        for var in result["missing_optional"]:
            logger.warning(f"   {var}")
    
    logger.info("✅ Container environment validation passed")
```

#### Database and External Service Connection Handling
```python
class ContainerConnectionManager:
    """Manage external connections with proper error handling for containers."""
    
    def __init__(self):
        self.redis_client = None
        self.supabase_client = None
        self.connection_health = {}
    
    async def initialize_connections(self, max_retries=5, retry_delay=10):
        """Initialize all external connections with retry logic."""
        
        connection_tasks = [
            ("redis", self._init_redis_connection),
            ("supabase", self._init_supabase_connection),
            ("ai_services", self._init_ai_service_connections)
        ]
        
        for service_name, init_func in connection_tasks:
            logger.info(f"Initializing {service_name} connection...")
            
            for attempt in range(max_retries):
                try:
                    await init_func()
                    self.connection_health[service_name] = "healthy"
                    logger.info(f"✅ {service_name} connection successful")
                    break
                    
                except Exception as e:
                    logger.warning(f"⚠️  {service_name} connection attempt {attempt + 1} failed: {e}")
                    
                    if attempt == max_retries - 1:
                        logger.error(f"❌ {service_name} connection failed after {max_retries} attempts")
                        self.connection_health[service_name] = "failed"
                        
                        # Decide if this is a fatal error
                        if service_name in ["redis", "supabase"]:  # Critical services
                            raise Exception(f"Critical service {service_name} unavailable")
                    else:
                        await asyncio.sleep(retry_delay)
    
    async def _init_redis_connection(self):
        """Initialize Redis connection with proper error handling."""
        import aioredis
        
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise ValueError("REDIS_URL environment variable not set")
        
        # Parse connection string and handle TLS
        if redis_url.startswith("rediss://"):
            # TLS connection
            self.redis_client = aioredis.from_url(
                redis_url,
                ssl_cert_reqs=None,  # For managed Redis services
                retry_on_timeout=True,
                health_check_interval=30
            )
        else:
            # Standard connection
            self.redis_client = aioredis.from_url(
                redis_url,
                retry_on_timeout=True,
                health_check_interval=30
            )
        
        # Test connection
        await self.redis_client.ping()
        logger.info("Redis connection established successfully")
    
    async def _init_supabase_connection(self):
        """Initialize Supabase connection."""
        from supabase import create_client
        
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY required")
        
        self.supabase_client = create_client(url, key)
        
        # Test connection with a simple query
        result = self.supabase_client.table("health_check").select("*").limit(1).execute()
        logger.info("Supabase connection established successfully")
    
    async def health_check(self):
        """Perform health check on all connections."""
        health_status = {
            "overall_healthy": True,
            "services": {}
        }
        
        # Check Redis
        try:
            if self.redis_client:
                await self.redis_client.ping()
                health_status["services"]["redis"] = "healthy"
            else:
                health_status["services"]["redis"] = "not_initialized"
                health_status["overall_healthy"] = False
        except Exception as e:
            health_status["services"]["redis"] = f"unhealthy: {str(e)}"
            health_status["overall_healthy"] = False
        
        # Check Supabase
        try:
            if self.supabase_client:
                # Simple health check query
                self.supabase_client.table("health_check").select("count").limit(1).execute()
                health_status["services"]["supabase"] = "healthy"
            else:
                health_status["services"]["supabase"] = "not_initialized"
                health_status["overall_healthy"] = False
        except Exception as e:
            health_status["services"]["supabase"] = f"unhealthy: {str(e)}"
            health_status["overall_healthy"] = False
        
        return health_status
```

### Category 4: Resource and Performance Issues

#### Memory Management for AI Workloads
```python
class AIWorkloadResourceManager:
    """Manage resources for AI workloads in containers."""
    
    def __init__(self):
        self.model_cache = {}
        self.memory_monitor = MemoryMonitor()
        
    async def load_ai_model_with_memory_management(self, model_type, model_config):
        """Load AI model with memory monitoring and management."""
        
        # Check available memory before loading
        memory_info = self.memory_monitor.get_memory_info()
        
        if memory_info["available_gb"] < 2.0:  # Less than 2GB available
            logger.warning("⚠️  Low memory available, clearing model cache")
            await self._clear_model_cache()
        
        model_key = f"{model_type}_{model_config['version']}"
        
        if model_key in self.model_cache:
            logger.info(f"Using cached model: {model_key}")
            return self.model_cache[model_key]
        
        logger.info(f"Loading model: {model_key}")
        memory_before = self.memory_monitor.get_memory_info()
        
        try:
            # Load model with timeout to prevent hanging
            model = await asyncio.wait_for(
                self._load_model_implementation(model_type, model_config),
                timeout=300  # 5 minutes timeout
            )
            
            memory_after = self.memory_monitor.get_memory_info()
            memory_used = memory_before["used_gb"] - memory_after["available_gb"]
            
            logger.info(f"Model {model_key} loaded successfully, memory used: {memory_used:.2f}GB")
            
            # Cache model if we have enough memory
            if memory_after["available_gb"] > 1.0:
                self.model_cache[model_key] = model
            else:
                logger.warning("Not caching model due to low memory")
            
            return model
            
        except asyncio.TimeoutError:
            logger.error(f"Model loading timeout for {model_key}")
            raise
        except Exception as e:
            logger.error(f"Failed to load model {model_key}: {e}")
            raise
    
    async def _clear_model_cache(self):
        """Clear model cache to free memory."""
        logger.info("Clearing AI model cache to free memory")
        
        for model_key, model in self.model_cache.items():
            try:
                # Properly cleanup model if it has a cleanup method
                if hasattr(model, 'cleanup'):
                    await model.cleanup()
                elif hasattr(model, 'close'):
                    model.close()
                
                logger.info(f"Cleared model from cache: {model_key}")
            except Exception as e:
                logger.warning(f"Error clearing model {model_key}: {e}")
        
        self.model_cache.clear()
        
        # Force garbage collection
        import gc
        gc.collect()

class MemoryMonitor:
    """Monitor container memory usage."""
    
    def get_memory_info(self):
        """Get current memory usage information."""
        import psutil
        
        memory = psutil.virtual_memory()
        
        return {
            "total_gb": memory.total / (1024**3),
            "available_gb": memory.available / (1024**3),
            "used_gb": memory.used / (1024**3),
            "percent_used": memory.percent
        }
    
    def log_memory_status(self):
        """Log current memory status."""
        info = self.get_memory_info()
        logger.info(
            f"Memory Status: {info['used_gb']:.2f}GB used / "
            f"{info['total_gb']:.2f}GB total ({info['percent_used']:.1f}% used)"
        )
        
        if info['percent_used'] > 85:
            logger.warning("⚠️  High memory usage detected!")
        
        return info
```

#### Container Health Monitoring
```python
class ContainerHealthMonitor:
    """Comprehensive health monitoring for AI service containers."""
    
    def __init__(self):
        self.health_checks = {
            "basic": self._basic_health_check,
            "memory": self._memory_health_check,
            "ai_models": self._ai_models_health_check,
            "external_deps": self._external_dependencies_health_check
        }
        self.health_history = []
    
    async def comprehensive_health_check(self):
        """Perform comprehensive health check."""
        
        health_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "checks": {},
            "issues": []
        }
        
        for check_name, check_func in self.health_checks.items():
            try:
                check_result = await check_func()
                health_result["checks"][check_name] = check_result
                
                if not check_result.get("healthy", False):
                    health_result["overall_status"] = "unhealthy"
                    if check_result.get("issues"):
                        health_result["issues"].extend(check_result["issues"])
                        
            except Exception as e:
                health_result["checks"][check_name] = {
                    "healthy": False,
                    "error": str(e)
                }
                health_result["overall_status"] = "unhealthy"
                health_result["issues"].append(f"{check_name} check failed: {e}")
        
        # Store health history (keep last 100 checks)
        self.health_history.append(health_result)
        if len(self.health_history) > 100:
            self.health_history.pop(0)
        
        return health_result
    
    async def _basic_health_check(self):
        """Basic container health check."""
        import psutil
        
        try:
            # Check if process is running normally
            process = psutil.Process()
            cpu_percent = process.cpu_percent()
            
            return {
                "healthy": True,
                "cpu_percent": cpu_percent,
                "status": process.status(),
                "threads": process.num_threads()
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    async def _memory_health_check(self):
        """Memory usage health check."""
        memory_monitor = MemoryMonitor()
        memory_info = memory_monitor.get_memory_info()
        
        # Consider unhealthy if memory usage > 90%
        healthy = memory_info["percent_used"] < 90
        
        result = {
            "healthy": healthy,
            "memory_info": memory_info
        }
        
        if not healthy:
            result["issues"] = [f"High memory usage: {memory_info['percent_used']:.1f}%"]
        
        return result
    
    async def _ai_models_health_check(self):
        """AI models health check."""
        # This would check if AI models are loaded and responsive
        try:
            # Mock AI model health check
            # In real implementation, this would test model inference
            return {
                "healthy": True,
                "models_loaded": ["text_generation", "analysis"],
                "last_inference_time": "2025-09-03T10:30:00Z"
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "issues": ["AI models not responding"]
            }
```

## Container Debugging Toolkit

### Essential Docker Commands for AI Services
```bash
#!/bin/bash
# AI Service Container Debugging Toolkit

# 1. Build and test container locally
function build_and_test() {
    local service_name=${1:-"ai-service"}
    
    echo "🔨 Building container..."
    docker build -t $service_name-test . || {
        echo "❌ Build failed"
        return 1
    }
    
    echo "🧪 Testing container startup..."
    docker run -d --name $service_name-test-instance \
        -p 8080:8080 \
        -e PORT=8080 \
        $service_name-test || {
        echo "❌ Container startup failed"
        return 1
    }
    
    # Wait for startup
    sleep 10
    
    # Test health endpoint
    if curl -f http://localhost:8080/health; then
        echo "✅ Container test successful"
    else
        echo "❌ Health check failed"
        docker logs $service_name-test-instance
    fi
    
    # Cleanup
    docker stop $service_name-test-instance
    docker rm $service_name-test-instance
}

# 2. Debug container with shell access
function debug_container() {
    local service_name=${1:-"ai-service"}
    
    echo "🐛 Starting debug container with shell access..."
    docker run -it --rm \
        --entrypoint /bin/bash \
        -v $(pwd):/workspace \
        $service_name-test
}

# 3. Monitor container resources
function monitor_container() {
    local container_name=$1
    
    if [ -z "$container_name" ]; then
        echo "Usage: monitor_container <container_name>"
        return 1
    fi
    
    echo "📊 Monitoring container resources for $container_name..."
    docker stats $container_name --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# 4. Extract and analyze container logs
function analyze_logs() {
    local container_name=$1
    local log_file=${2:-"container_logs.txt"}
    
    echo "📋 Extracting logs from $container_name..."
    docker logs $container_name > $log_file 2>&1
    
    echo "🔍 Analyzing logs for common issues..."
    
    # Check for common error patterns
    if grep -q "SyntaxError\|IndentationError" $log_file; then
        echo "❌ Python syntax errors found:"
        grep -n "SyntaxError\|IndentationError" $log_file
    fi
    
    if grep -q "ImportError\|ModuleNotFoundError" $log_file; then
        echo "❌ Import errors found:"
        grep -n "ImportError\|ModuleNotFoundError" $log_file
    fi
    
    if grep -q "ConnectionError\|timeout" $log_file; then
        echo "⚠️  Connection issues found:"
        grep -n "ConnectionError\|timeout" $log_file
    fi
    
    echo "📄 Full logs saved to: $log_file"
}
```

This comprehensive container troubleshooting guide provides the foundation for debugging AI service containers, addressing the unique challenges these systems present in containerized environments.
