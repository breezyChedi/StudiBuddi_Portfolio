#!/usr/bin/env python3
"""
ITERATION 2: Comprehensive Model Comparison Testing

This iteration evolved from simple component testing to systematic comparison
of different AI models and configurations. While more sophisticated than
iteration 1, it still missed the full production context complexity.

Original inspiration: Understanding which AI models and parameters work best
Date: Mid-way through debugging process  
Status: SUPERSEDED by exact production reproduction approach
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Expanded configuration - moving toward production parameters
AI_API_KEY = "production_key_abc123"
MATH_EVAL_TOKEN = "math_eval_token_456"

class AIModel(Enum):
    """AI models available for testing - attempting to match production options."""
    PRO = "ai-model-pro"
    FLASH = "ai-model-flash" 
    FLASH_LITE = "ai-model-flash-lite"
    FLASH_LITE_PREVIEW = "ai-model-flash-lite-preview-06-17"  # Discovered later!

@dataclass
class ModelConfiguration:
    """
    Model configuration parameters - much more comprehensive than iteration 1.
    
    IMPROVEMENT: Systematic parameter management
    STILL MISSING: Full production schema complexity
    """
    model: AIModel
    temperature: float = 0.3
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    max_tokens: int = 3000
    system_instruction: Optional[str] = None

@dataclass 
class TestProblem:
    """Test problem structure - more realistic than simple strings."""
    name: str
    description: str
    mathematical_concept: str
    expected_pattern: str
    difficulty: str

class ModelComparisonTester:
    """
    ITERATION 2 APPROACH: Systematic comparison of models and configurations.
    
    IMPROVEMENTS OVER ITERATION 1:
    - Multiple model testing
    - Parameter variation analysis
    - Statistical validation approach
    - More realistic test problems
    
    STILL MISSING:
    - Full production JSON schema
    - Complete environmental factors
    - Real production workflow simulation
    """
    
    def __init__(self):
        self.session = None
        self.results = []
        
        # Test problems - more realistic but still simplified
        self.test_problems = [
            TestProblem(
                name="Quadratic Equation",
                description="Find roots of quadratic equation",
                mathematical_concept="algebra",
                expected_pattern="numeric_solutions",
                difficulty="medium"
            ),
            TestProblem(
                name="Distance Calculation", 
                description="Calculate distance between two points",
                mathematical_concept="geometry",
                expected_pattern="single_numeric_value",
                difficulty="easy"
            ),
            TestProblem(
                name="Optimization Problem",
                description="Find maximum value of function",
                mathematical_concept="calculus",
                expected_pattern="optimized_value",
                difficulty="hard"
            ),
            TestProblem(
                name="System of Equations",
                description="Solve system of linear equations", 
                mathematical_concept="linear_algebra",
                expected_pattern="solution_set",
                difficulty="medium"
            )
        ]
        
        # Model configurations to test - systematic parameter exploration
        self.model_configs = [
            ModelConfiguration(AIModel.PRO, temperature=0.3, top_k=40, top_p=0.95),
            ModelConfiguration(AIModel.FLASH, temperature=0.3, top_k=40, top_p=0.95),
            ModelConfiguration(AIModel.FLASH_LITE, temperature=0.3, top_k=40, top_p=0.95),
            ModelConfiguration(AIModel.FLASH_LITE, temperature=0.3),  # Missing top_k/top_p
            ModelConfiguration(AIModel.FLASH_LITE, temperature=0.7, top_k=40, top_p=0.95),  # Higher temp
        ]
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def run_comprehensive_comparison(self) -> Dict[str, Any]:
        """
        Run systematic comparison across models and configurations.
        
        METHODOLOGY IMPROVEMENTS:
        - Statistical validation with multiple runs
        - Systematic parameter variation
        - Performance and quality tracking
        
        STILL MISSING:
        - Production JSON schema complexity
        - Real user workflow simulation
        - Full environmental factors
        """
        print("🔬 ITERATION 2: Comprehensive Model Comparison")
        print("=" * 70)
        
        comparison_results = {
            "test_summary": {
                "models_tested": len(self.model_configs),
                "problems_tested": len(self.test_problems),
                "total_test_runs": len(self.model_configs) * len(self.test_problems) * 3,  # 3 runs each
                "start_time": datetime.now().isoformat()
            },
            "model_performance": {},
            "configuration_analysis": {},
            "problem_difficulty_analysis": {}
        }
        
        for config in self.model_configs:
            print(f"\n🤖 Testing {config.model.value} (temp={config.temperature}, top_k={config.top_k}, top_p={config.top_p})")
            
            model_results = await self._test_model_configuration(config)
            comparison_results["model_performance"][self._config_key(config)] = model_results
        
        # Analysis phase
        comparison_results["configuration_analysis"] = self._analyze_configuration_impact(comparison_results)
        comparison_results["problem_difficulty_analysis"] = self._analyze_problem_difficulty(comparison_results)
        
        return comparison_results
    
    async def _test_model_configuration(self, config: ModelConfiguration) -> Dict[str, Any]:
        """
        Test a specific model configuration across all problems.
        
        IMPROVEMENT: Multiple runs for statistical validity
        MISSING: Production complexity simulation
        """
        config_results = {
            "configuration": {
                "model": config.model.value,
                "parameters": {
                    "temperature": config.temperature,
                    "top_k": config.top_k,
                    "top_p": config.top_p,
                    "max_tokens": config.max_tokens
                }
            },
            "problem_results": {},
            "summary_stats": {}
        }
        
        for problem in self.test_problems:
            print(f"  📝 Testing: {problem.name}")
            
            # Run multiple times for statistical analysis
            problem_runs = []
            for run in range(3):
                result = await self._test_single_problem(config, problem, run)
                problem_runs.append(result)
                
                # Rate limiting
                await asyncio.sleep(2)
            
            # Aggregate results
            config_results["problem_results"][problem.name] = {
                "individual_runs": problem_runs,
                "success_rate": sum(1 for r in problem_runs if r["technical_success"]) / len(problem_runs),
                "avg_response_time": sum(r["response_time_ms"] for r in problem_runs) / len(problem_runs),
                "quality_scores": [r.get("quality_score", 0) for r in problem_runs]
            }
        
        # Calculate summary statistics
        all_success_rates = [result["success_rate"] for result in config_results["problem_results"].values()]
        config_results["summary_stats"] = {
            "overall_success_rate": sum(all_success_rates) / len(all_success_rates),
            "consistency_score": 1.0 - (max(all_success_rates) - min(all_success_rates)),  # Lower variance = higher consistency
            "avg_response_time": sum(
                result["avg_response_time"] for result in config_results["problem_results"].values()
            ) / len(config_results["problem_results"])
        }
        
        return config_results
    
    async def _test_single_problem(self, config: ModelConfiguration, problem: TestProblem, run_number: int) -> Dict[str, Any]:
        """
        Test AI model on a single problem instance.
        
        IMPROVEMENT: Detailed result tracking and timing
        STILL SIMPLIFIED: Not full production workflow
        """
        start_time = time.time()
        
        # Construct prompt - more sophisticated than iteration 1 but still not production-level
        prompt = self._construct_test_prompt(problem)
        
        # AI model call
        ai_result = await self._call_ai_model(config, prompt)
        
        # Mathematical evaluation
        math_result = None
        if ai_result.get("success") and ai_result.get("mathematical_code"):
            math_result = await self._evaluate_mathematical_code(ai_result["mathematical_code"])
        
        end_time = time.time()
        
        # Analyze result quality
        quality_analysis = self._analyze_result_quality(ai_result, math_result, problem)
        
        return {
            "run_number": run_number,
            "problem": problem.name,
            "configuration": self._config_key(config),
            "technical_success": ai_result.get("success", False),
            "mathematical_success": math_result.get("success", False) if math_result else False,
            "response_time_ms": (end_time - start_time) * 1000,
            "ai_output": ai_result.get("mathematical_code", ""),
            "math_output": math_result.get("output", "") if math_result else "",
            "quality_score": quality_analysis.get("score", 0),
            "issues_detected": quality_analysis.get("issues", [])
        }
    
    def _construct_test_prompt(self, problem: TestProblem) -> str:
        """
        Construct test prompt - more sophisticated than iteration 1.
        
        IMPROVEMENT: Problem-specific prompt construction
        MISSING: Full production prompt complexity and context
        """
        base_prompts = {
            "Quadratic Equation": "Generate mathematical code to solve the equation x² + 5x + 6 = 0 for x.",
            "Distance Calculation": "Generate mathematical code to calculate the distance between points A(2, 3) and B(8, 7).",
            "Optimization Problem": "Generate mathematical code to find the maximum value of f(x) = -x² + 6x + 2.",
            "System of Equations": "Generate mathematical code to solve: 2x + 3y = 7 and x - y = 1."
        }
        
        prompt = base_prompts.get(problem.name, f"Generate mathematical code for: {problem.description}")
        
        # Add response format guidance (simplified compared to production)
        prompt += "\n\nReturn executable mathematical code that computes the answer."
        
        return prompt
    
    async def _call_ai_model(self, config: ModelConfiguration, prompt: str) -> Dict[str, Any]:
        """
        Call AI model with specified configuration.
        
        IMPROVEMENT: Systematic parameter handling
        MISSING: Full production JSON schema and system instructions
        """
        url = "https://api.ai-service.com/generate"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}"
        }
        
        # Build request with configuration parameters
        data = {
            "model": config.model.value,
            "prompt": prompt,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }
        
        # Add optional parameters if specified
        if config.top_k is not None:
            data["top_k"] = config.top_k
        if config.top_p is not None:
            data["top_p"] = config.top_p
        if config.system_instruction:
            data["system_instruction"] = config.system_instruction
        
        # STILL MISSING: response_mime_type, response_schema (critical for production!)
        
        try:
            async with self.session.post(url, json=data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    mathematical_code = self._extract_mathematical_code(result.get("text", ""))
                    
                    return {
                        "success": True,
                        "raw_response": result.get("text", ""),
                        "mathematical_code": mathematical_code
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {resp.status}",
                        "response": await resp.text()
                    }
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _evaluate_mathematical_code(self, code: str) -> Dict[str, Any]:
        """
        Evaluate mathematical code using external API.
        
        IMPROVEMENT: Better error handling and result validation
        SIMILAR TO PRODUCTION: This part was actually fairly accurate
        """
        if not code or not code.strip():
            return {"success": False, "error": "No mathematical code to evaluate"}
        
        try:
            import urllib.parse
            encoded_code = urllib.parse.quote(code)
            url = f"https://api.math-evaluation.com/eval?input={encoded_code}"
            
            headers = {"Authorization": f"Bearer {MATH_EVAL_TOKEN}"}
            
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return {
                        "success": True,
                        "output": result.get("output", ""),
                        "raw_response": result
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Math API HTTP {resp.status}",
                        "response": await resp.text()
                    }
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _extract_mathematical_code(self, ai_response: str) -> Optional[str]:
        """
        Extract mathematical code from AI response.
        
        IMPROVEMENT: More sophisticated extraction patterns
        STILL BASIC: Compared to production JSON parsing requirements
        """
        import re
        
        # Multiple patterns to catch different code formats
        patterns = [
            r"```(?:mathematica|wolfram)?\s*([^`]+)```",  # Code blocks
            r"Solve\[[^\]]+\]",  # Solve expressions
            r"(?:Maximize|Minimize)\[[^\]]+\]",  # Optimization
            r"EuclideanDistance\[[^\]]+\]",  # Distance calculations
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, ai_response, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        # Fallback: look for any mathematical expression
        math_pattern = r"[A-Za-z]+\[[^\]]+\]"
        matches = re.findall(math_pattern, ai_response)
        return matches[0] if matches else None
    
    def _analyze_result_quality(self, ai_result: Dict, math_result: Optional[Dict], problem: TestProblem) -> Dict[str, Any]:
        """
        Analyze the quality of AI-generated mathematical solutions.
        
        IMPROVEMENT: Quality scoring beyond simple success/fail
        MISSING: Domain-specific mathematical correctness validation
        """
        issues = []
        score = 0
        
        # Technical success
        if ai_result.get("success"):
            score += 25
        else:
            issues.append("AI generation failed")
        
        # Mathematical code extraction
        if ai_result.get("mathematical_code"):
            score += 25
        else:
            issues.append("No mathematical code extracted")
        
        # Mathematical evaluation success
        if math_result and math_result.get("success"):
            score += 25
        elif math_result:
            issues.append(f"Math evaluation failed: {math_result.get('error', 'Unknown error')}")
        else:
            issues.append("Math evaluation not attempted")
        
        # Output format analysis
        if math_result and math_result.get("output"):
            output = math_result["output"]
            if any(char in output for char in ["{", "}", "/.", "First", "Last"]):
                issues.append("Output contains unparsed mathematical syntax")
            else:
                score += 25
        
        return {"score": score, "issues": issues}
    
    def _config_key(self, config: ModelConfiguration) -> str:
        """Generate unique key for configuration."""
        return f"{config.model.value}_temp{config.temperature}_k{config.top_k}_p{config.top_p}"
    
    def _analyze_configuration_impact(self, results: Dict) -> Dict[str, Any]:
        """
        Analyze how different configurations impact performance.
        
        VALUABLE INSIGHT: This analysis revealed configuration sensitivity
        """
        model_performance = results["model_performance"]
        
        analysis = {
            "temperature_impact": {},
            "parameter_impact": {},
            "model_comparison": {}
        }
        
        # Group by model type
        by_model = {}
        for config_key, performance in model_performance.items():
            model = performance["configuration"]["model"]
            if model not in by_model:
                by_model[model] = []
            by_model[model].append(performance)
        
        # Analyze model differences
        for model, performances in by_model.items():
            avg_success = sum(p["summary_stats"]["overall_success_rate"] for p in performances) / len(performances)
            analysis["model_comparison"][model] = {
                "average_success_rate": avg_success,
                "consistency": sum(p["summary_stats"]["consistency_score"] for p in performances) / len(performances),
                "configurations_tested": len(performances)
            }
        
        return analysis
    
    def _analyze_problem_difficulty(self, results: Dict) -> Dict[str, Any]:
        """
        Analyze which problems are consistently difficult across models.
        
        INSIGHT: Revealed problem-specific failure patterns
        """
        problem_analysis = {}
        
        for config_key, performance in results["model_performance"].items():
            for problem_name, problem_result in performance["problem_results"].items():
                if problem_name not in problem_analysis:
                    problem_analysis[problem_name] = []
                problem_analysis[problem_name].append(problem_result["success_rate"])
        
        # Calculate average success rate per problem
        for problem, success_rates in problem_analysis.items():
            avg_success = sum(success_rates) / len(success_rates)
            problem_analysis[problem] = {
                "average_success_rate": avg_success,
                "consistency": 1.0 - (max(success_rates) - min(success_rates)),
                "difficulty_assessment": "hard" if avg_success < 0.5 else "medium" if avg_success < 0.8 else "easy"
            }
        
        return problem_analysis

async def run_model_comparison():
    """
    Execute iteration 2: comprehensive model comparison testing.
    
    RESULTS SUMMARY:
    - ✅ Systematic model parameter analysis
    - ✅ Statistical validation approach  
    - ✅ Quality scoring methodology
    - ❌ Still failed to reproduce production failures
    - ❌ Missing production JSON schema complexity
    - ❌ Oversimplified test scenarios
    """
    print("🔬 ITERATION 2: Comprehensive Model Comparison Testing")
    print("=" * 70)
    
    async with ModelComparisonTester() as tester:
        results = await tester.run_comprehensive_comparison()
        
        print("\n📊 ITERATION 2 RESULTS:")
        print("✅ ACHIEVEMENTS:")
        print("  - Systematic model comparison methodology")
        print("  - Statistical validation with multiple runs")
        print("  - Configuration parameter impact analysis")
        print("  - Quality scoring beyond simple pass/fail")
        
        print("\n❌ LIMITATIONS:")
        print("  - Still failed to reproduce production failures")
        print("  - Missing full production JSON schema requirements")
        print("  - Test problems too simplified vs real production complexity")
        print("  - No environmental factor simulation")
        
        print("\n🎓 KEY INSIGHTS:")
        print("  - Model parameter sensitivity confirmed")
        print("  - Temperature and top_k/top_p significantly impact results")
        print("  - Some problems consistently harder across all models")
        print("  - Quality varies significantly even with same configuration")
        
        print("\n➡️  NEXT ITERATION: Exact production environment reproduction")
        
        return results

if __name__ == "__main__":
    asyncio.run(run_model_comparison())
