yesusr/bin/env python3
"""
AI System Testing Framework

A comprehensive, reusable framework for testing AI systems with focus on:
- Statistical validation of non-deterministic outputs
- Production environment replication
- Model comparison and analysis
- Real failure case reproduction

Generalized from production AI educational platform debugging experience.
"""

import asyncio
import json
import time
import hashlib
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod

class TestType(Enum):
    """Types of AI system tests."""
    UNIT = "unit"
    INTEGRATION = "integration"
    PRODUCTION_REPRODUCTION = "production_reproduction"
    MODEL_COMPARISON = "model_comparison"
    STATISTICAL_VALIDATION = "statistical_validation"

@dataclass
class AIModelConfiguration:
    """Configuration for AI model testing."""
    model_id: str
    model_version: str
    temperature: float = 0.3
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    max_output_tokens: int = 3000
    system_instruction: Optional[str] = None
    response_format: str = "text"
    response_schema: Optional[Dict] = None

    def get_config_hash(self) -> str:
        """Generate hash for configuration tracking."""
        config_string = json.dumps(asdict(self), sort_keys=True)
        return hashlib.md5(config_string.encode()).hexdigest()[:8]

@dataclass
class TestCase:
    """Individual test case for AI system."""
    id: str
    name: str
    input_data: Any
    expected_output_pattern: Optional[str] = None
    expected_output_type: str = "any"
    validation_function: Optional[Callable] = None
    difficulty_level: str = "medium"
    category: str = "general"
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class TestResult:
    """Result of a single test execution."""
    test_case_id: str
    model_config_hash: str
    execution_timestamp: str
    success: bool
    output: Any
    execution_time_ms: float
    error_message: Optional[str] = None
    quality_score: Optional[float] = None
    validation_details: Dict = None

    def __post_init__(self):
        if self.validation_details is None:
            self.validation_details = {}

class AISystemInterface(ABC):
    """Abstract interface for AI systems to be tested."""
    
    @abstractmethod
    async def call_ai_system(self, config: AIModelConfiguration, input_data: Any) -> Dict[str, Any]:
        """Call the AI system with given configuration and input."""
        pass
    
    @abstractmethod
    def validate_output(self, output: Any, test_case: TestCase) -> Dict[str, Any]:
        """Validate AI system output against test case expectations."""
        pass

class ProductionAISystem(AISystemInterface):
    """Example implementation for production AI system."""
    
    def __init__(self, api_endpoint: str, api_key: str):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.session = None
    
    async def call_ai_system(self, config: AIModelConfiguration, input_data: Any) -> Dict[str, Any]:
        """Call production AI system."""
        import aiohttp
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Construct request payload
        payload = {
            "model": config.model_id,
            "input": input_data,
            "temperature": config.temperature,
            "max_tokens": config.max_output_tokens
        }
        
        if config.top_k is not None:
            payload["top_k"] = config.top_k
        if config.top_p is not None:
            payload["top_p"] = config.top_p
        if config.system_instruction:
            payload["system_instruction"] = config.system_instruction
        if config.response_format == "json":
            payload["response_format"] = {"type": "json_object"}
            if config.response_schema:
                payload["response_schema"] = config.response_schema
        
        try:
            async with self.session.post(self.api_endpoint, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "output": result.get("output", ""),
                        "raw_response": result
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}"
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def validate_output(self, output: Any, test_case: TestCase) -> Dict[str, Any]:
        """Validate output against test case expectations."""
        validation_result = {
            "valid": True,
            "issues": [],
            "quality_score": 1.0
        }
        
        # Basic type validation
        if test_case.expected_output_type != "any":
            if test_case.expected_output_type == "json":
                try:
                    json.loads(str(output))
                except (json.JSONDecodeError, TypeError):
                    validation_result["valid"] = False
                    validation_result["issues"].append("Output is not valid JSON")
                    validation_result["quality_score"] *= 0.5
            elif test_case.expected_output_type == "numeric":
                try:
                    float(str(output).strip())
                except (ValueError, TypeError):
                    validation_result["valid"] = False
                    validation_result["issues"].append("Output is not numeric")
                    validation_result["quality_score"] *= 0.5
        
        # Pattern validation
        if test_case.expected_output_pattern:
            import re
            if not re.search(test_case.expected_output_pattern, str(output)):
                validation_result["valid"] = False
                validation_result["issues"].append(f"Output does not match pattern: {test_case.expected_output_pattern}")
                validation_result["quality_score"] *= 0.7
        
        # Custom validation function
        if test_case.validation_function:
            try:
                custom_result = test_case.validation_function(output, test_case)
                if isinstance(custom_result, dict):
                    if not custom_result.get("valid", True):
                        validation_result["valid"] = False
                        validation_result["issues"].extend(custom_result.get("issues", []))
                    validation_result["quality_score"] *= custom_result.get("quality_multiplier", 1.0)
                elif not custom_result:
                    validation_result["valid"] = False
                    validation_result["issues"].append("Custom validation failed")
                    validation_result["quality_score"] *= 0.3
            except Exception as e:
                validation_result["issues"].append(f"Validation function error: {str(e)}")
                validation_result["quality_score"] *= 0.8
        
        return validation_result

class AISystemTester:
    """Comprehensive testing framework for AI systems."""
    
    def __init__(self, ai_system: AISystemInterface):
        self.ai_system = ai_system
        self.test_results: List[TestResult] = []
        self.configurations: List[AIModelConfiguration] = []
        self.test_cases: List[TestCase] = []
        
    def add_configuration(self, config: AIModelConfiguration):
        """Add AI model configuration to test."""
        self.configurations.append(config)
    
    def add_test_case(self, test_case: TestCase):
        """Add test case to the test suite."""
        self.test_cases.append(test_case)
    
    def load_test_cases_from_json(self, json_file_path: str):
        """Load test cases from JSON file."""
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        for case_data in data.get("test_cases", []):
            test_case = TestCase(
                id=case_data["id"],
                name=case_data["name"],
                input_data=case_data["input_data"],
                expected_output_pattern=case_data.get("expected_output_pattern"),
                expected_output_type=case_data.get("expected_output_type", "any"),
                difficulty_level=case_data.get("difficulty_level", "medium"),
                category=case_data.get("category", "general"),
                metadata=case_data.get("metadata", {})
            )
            self.add_test_case(test_case)
    
    async def run_single_test(self, config: AIModelConfiguration, test_case: TestCase) -> TestResult:
        """Execute a single test case with given configuration."""
        start_time = time.time()
        
        try:
            # Call AI system
            ai_response = await self.ai_system.call_ai_system(config, test_case.input_data)
            
            execution_time = (time.time() - start_time) * 1000
            
            if ai_response.get("success"):
                # Validate output
                validation_result = self.ai_system.validate_output(
                    ai_response["output"], 
                    test_case
                )
                
                return TestResult(
                    test_case_id=test_case.id,
                    model_config_hash=config.get_config_hash(),
                    execution_timestamp=datetime.utcnow().isoformat(),
                    success=validation_result["valid"],
                    output=ai_response["output"],
                    execution_time_ms=execution_time,
                    quality_score=validation_result.get("quality_score"),
                    validation_details=validation_result
                )
            else:
                return TestResult(
                    test_case_id=test_case.id,
                    model_config_hash=config.get_config_hash(),
                    execution_timestamp=datetime.utcnow().isoformat(),
                    success=False,
                    output=None,
                    execution_time_ms=execution_time,
                    error_message=ai_response.get("error", "Unknown error")
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return TestResult(
                test_case_id=test_case.id,
                model_config_hash=config.get_config_hash(),
                execution_timestamp=datetime.utcnow().isoformat(),
                success=False,
                output=None,
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    async def run_statistical_validation(self, config: AIModelConfiguration, test_case: TestCase, num_runs: int = 10) -> Dict[str, Any]:
        """Run statistical validation with multiple executions."""
        print(f"  📊 Running statistical validation: {num_runs} runs for {test_case.name}")
        
        results = []
        for run in range(num_runs):
            result = await self.run_single_test(config, test_case)
            results.append(result)
            
            # Rate limiting between calls
            await asyncio.sleep(1)
        
        # Statistical analysis
        success_rate = sum(1 for r in results if r.success) / len(results)
        execution_times = [r.execution_time_ms for r in results]
        quality_scores = [r.quality_score for r in results if r.quality_score is not None]
        
        unique_outputs = set(str(r.output) for r in results if r.output is not None)
        consistency_score = 1.0 / len(unique_outputs) if unique_outputs else 0.0
        
        return {
            "test_case_id": test_case.id,
            "config_hash": config.get_config_hash(),
            "num_runs": num_runs,
            "success_rate": success_rate,
            "avg_execution_time_ms": statistics.mean(execution_times) if execution_times else 0,
            "execution_time_std": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
            "avg_quality_score": statistics.mean(quality_scores) if quality_scores else 0,
            "quality_score_std": statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0,
            "consistency_score": consistency_score,
            "unique_outputs": len(unique_outputs),
            "individual_results": results
        }
    
    async def run_comprehensive_test_suite(self, statistical_runs: int = 5) -> Dict[str, Any]:
        """Run comprehensive test suite across all configurations and test cases."""
        print("🧪 Starting Comprehensive AI System Test Suite")
        print("=" * 60)
        
        test_suite_results = {
            "test_metadata": {
                "start_time": datetime.utcnow().isoformat(),
                "configurations_tested": len(self.configurations),
                "test_cases": len(self.test_cases),
                "statistical_runs_per_test": statistical_runs
            },
            "configuration_results": {},
            "test_case_analysis": {},
            "model_comparison": {},
            "summary_statistics": {}
        }
        
        # Test each configuration
        for config in self.configurations:
            print(f"\n🤖 Testing Configuration: {config.model_id} ({config.get_config_hash()})")
            print(f"   Parameters: temp={config.temperature}, top_k={config.top_k}, top_p={config.top_p}")
            
            config_results = {
                "configuration": asdict(config),
                "test_case_results": {},
                "overall_metrics": {}
            }
            
            # Test each test case with this configuration
            for test_case in self.test_cases:
                print(f"  📝 Testing: {test_case.name} ({test_case.category})")
                
                if statistical_runs > 1:
                    # Statistical validation
                    statistical_result = await self.run_statistical_validation(
                        config, test_case, statistical_runs
                    )
                    config_results["test_case_results"][test_case.id] = statistical_result
                else:
                    # Single run
                    single_result = await self.run_single_test(config, test_case)
                    self.test_results.append(single_result)
                    config_results["test_case_results"][test_case.id] = {
                        "success_rate": 1.0 if single_result.success else 0.0,
                        "individual_results": [single_result]
                    }
            
            # Calculate overall metrics for this configuration
            test_results = config_results["test_case_results"]
            overall_success_rate = statistics.mean([r["success_rate"] for r in test_results.values()])
            
            config_results["overall_metrics"] = {
                "overall_success_rate": overall_success_rate,
                "tests_passed": sum(1 for r in test_results.values() if r["success_rate"] >= 0.8),
                "tests_failed": sum(1 for r in test_results.values() if r["success_rate"] < 0.8),
                "avg_consistency": statistics.mean([
                    r.get("consistency_score", 0) for r in test_results.values()
                ])
            }
            
            test_suite_results["configuration_results"][config.get_config_hash()] = config_results
        
        # Cross-configuration analysis
        test_suite_results["model_comparison"] = self._analyze_model_comparison(test_suite_results)
        test_suite_results["test_case_analysis"] = self._analyze_test_case_difficulty(test_suite_results)
        test_suite_results["summary_statistics"] = self._calculate_summary_statistics(test_suite_results)
        
        test_suite_results["test_metadata"]["end_time"] = datetime.utcnow().isoformat()
        
        return test_suite_results
    
    def _analyze_model_comparison(self, test_suite_results: Dict) -> Dict:
        """Analyze performance differences between model configurations."""
        config_results = test_suite_results["configuration_results"]
        
        comparison = {
            "best_overall_configuration": None,
            "configuration_rankings": [],
            "performance_insights": []
        }
        
        # Rank configurations by overall success rate
        config_performance = []
        for config_hash, results in config_results.items():
            config_performance.append({
                "config_hash": config_hash,
                "model_id": results["configuration"]["model_id"],
                "overall_success_rate": results["overall_metrics"]["overall_success_rate"],
                "avg_consistency": results["overall_metrics"]["avg_consistency"],
                "tests_passed": results["overall_metrics"]["tests_passed"]
            })
        
        # Sort by success rate
        config_performance.sort(key=lambda x: x["overall_success_rate"], reverse=True)
        comparison["configuration_rankings"] = config_performance
        
        if config_performance:
            comparison["best_overall_configuration"] = config_performance[0]
            
            # Generate insights
            best_rate = config_performance[0]["overall_success_rate"]
            worst_rate = config_performance[-1]["overall_success_rate"]
            
            if best_rate - worst_rate > 0.2:
                comparison["performance_insights"].append(
                    f"Significant performance difference: {best_rate:.1%} vs {worst_rate:.1%}"
                )
            
            # Consistency analysis
            consistency_scores = [c["avg_consistency"] for c in config_performance]
            if max(consistency_scores) - min(consistency_scores) > 0.3:
                comparison["performance_insights"].append(
                    "Large consistency variations between configurations"
                )
        
        return comparison
    
    def _analyze_test_case_difficulty(self, test_suite_results: Dict) -> Dict:
        """Analyze which test cases are consistently difficult across configurations."""
        config_results = test_suite_results["configuration_results"]
        
        # Aggregate results by test case
        test_case_performance = {}
        for config_hash, results in config_results.items():
            for test_case_id, test_result in results["test_case_results"].items():
                if test_case_id not in test_case_performance:
                    test_case_performance[test_case_id] = []
                test_case_performance[test_case_id].append(test_result["success_rate"])
        
        # Analyze difficulty
        difficulty_analysis = {}
        for test_case_id, success_rates in test_case_performance.items():
            avg_success_rate = statistics.mean(success_rates)
            consistency = 1.0 - statistics.stdev(success_rates) if len(success_rates) > 1 else 1.0
            
            difficulty_level = "easy" if avg_success_rate > 0.8 else "medium" if avg_success_rate > 0.5 else "hard"
            
            difficulty_analysis[test_case_id] = {
                "avg_success_rate": avg_success_rate,
                "consistency_across_models": consistency,
                "difficulty_assessment": difficulty_level,
                "success_rates_by_config": success_rates
            }
        
        return difficulty_analysis
    
    def _calculate_summary_statistics(self, test_suite_results: Dict) -> Dict:
        """Calculate overall summary statistics."""
        config_results = test_suite_results["configuration_results"]
        
        all_success_rates = []
        all_consistency_scores = []
        
        for results in config_results.values():
            all_success_rates.append(results["overall_metrics"]["overall_success_rate"])
            all_consistency_scores.append(results["overall_metrics"]["avg_consistency"])
        
        return {
            "overall_avg_success_rate": statistics.mean(all_success_rates) if all_success_rates else 0,
            "success_rate_std": statistics.stdev(all_success_rates) if len(all_success_rates) > 1 else 0,
            "overall_avg_consistency": statistics.mean(all_consistency_scores) if all_consistency_scores else 0,
            "consistency_std": statistics.stdev(all_consistency_scores) if len(all_consistency_scores) > 1 else 0,
            "total_tests_executed": sum(
                len(results["test_case_results"]) for results in config_results.values()
            ),
            "configurations_tested": len(config_results)
        }
    
    def generate_test_report(self, test_suite_results: Dict, output_file: str = None) -> str:
        """Generate comprehensive test report."""
        report_lines = []
        
        # Header
        report_lines.append("🧪 AI SYSTEM TESTING REPORT")
        report_lines.append("=" * 50)
        report_lines.append("")
        
        # Summary
        metadata = test_suite_results["test_metadata"]
        summary = test_suite_results["summary_statistics"]
        
        report_lines.append("📊 SUMMARY STATISTICS")
        report_lines.append(f"Test Duration: {metadata['start_time']} to {metadata['end_time']}")
        report_lines.append(f"Configurations Tested: {summary['configurations_tested']}")
        report_lines.append(f"Total Tests Executed: {summary['total_tests_executed']}")
        report_lines.append(f"Overall Success Rate: {summary['overall_avg_success_rate']:.1%}")
        report_lines.append(f"Average Consistency: {summary['overall_avg_consistency']:.1%}")
        report_lines.append("")
        
        # Model comparison
        comparison = test_suite_results["model_comparison"]
        report_lines.append("🏆 MODEL COMPARISON RESULTS")
        
        for i, config in enumerate(comparison["configuration_rankings"]):
            rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            report_lines.append(
                f"{rank_emoji} {config['model_id']} ({config['config_hash']}): "
                f"{config['overall_success_rate']:.1%} success, "
                f"{config['avg_consistency']:.1%} consistency"
            )
        
        report_lines.append("")
        
        # Performance insights
        if comparison["performance_insights"]:
            report_lines.append("💡 KEY INSIGHTS")
            for insight in comparison["performance_insights"]:
                report_lines.append(f"• {insight}")
            report_lines.append("")
        
        # Test case difficulty analysis
        difficulty = test_suite_results["test_case_analysis"]
        report_lines.append("📈 TEST CASE DIFFICULTY ANALYSIS")
        
        easy_tests = [tid for tid, data in difficulty.items() if data["difficulty_assessment"] == "easy"]
        medium_tests = [tid for tid, data in difficulty.items() if data["difficulty_assessment"] == "medium"]
        hard_tests = [tid for tid, data in difficulty.items() if data["difficulty_assessment"] == "hard"]
        
        report_lines.append(f"✅ Easy Tests ({len(easy_tests)}): {', '.join(easy_tests[:3])}{'...' if len(easy_tests) > 3 else ''}")
        report_lines.append(f"⚠️  Medium Tests ({len(medium_tests)}): {', '.join(medium_tests[:3])}{'...' if len(medium_tests) > 3 else ''}")
        report_lines.append(f"❌ Hard Tests ({len(hard_tests)}): {', '.join(hard_tests[:3])}{'...' if len(hard_tests) > 3 else ''}")
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_content)
        
        return report_content

# Example usage and test cases
if __name__ == "__main__":
    # Example: Setting up a test framework for AI mathematical content generation
    
    # Custom validation function for mathematical outputs
    def validate_mathematical_output(output: Any, test_case: TestCase) -> Dict[str, Any]:
        """Validate mathematical output quality."""
        output_str = str(output)
        issues = []
        quality_multiplier = 1.0
        
        # Check for mathematical syntax issues
        if "x /. First[" in output_str:
            issues.append("Contains unevaluated Wolfram expressions")
            quality_multiplier *= 0.5
        
        # Check for numeric result
        try:
            # Try to extract a number from the output
            import re
            numbers = re.findall(r'-?\d+\.?\d*', output_str)
            if not numbers:
                issues.append("No numeric values found in output")
                quality_multiplier *= 0.7
        except:
            pass
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "quality_multiplier": quality_multiplier
        }
    
    # Sample test cases (anonymized from production failures)
    sample_test_cases = [
        TestCase(
            id="mathematical_distance",
            name="Distance Calculation", 
            input_data="Calculate distance between points A(2,3) and B(8,7)",
            expected_output_type="numeric",
            expected_output_pattern=r'\d+\.?\d*',
            validation_function=validate_mathematical_output,
            category="geometry"
        ),
        TestCase(
            id="quadratic_optimization",
            name="Quadratic Function Maximum",
            input_data="Find maximum value of f(x) = -x² + 6x + 2",
            expected_output_type="numeric", 
            validation_function=validate_mathematical_output,
            category="calculus"
        ),
        TestCase(
            id="equation_solving",
            name="Linear Equation System",
            input_data="Solve: 2x + 3y = 7 and x - y = 1",
            expected_output_pattern=r'\{.*\}',
            validation_function=validate_mathematical_output,
            category="algebra"
        )
    ]
    
    # Sample configurations to test
    sample_configurations = [
        AIModelConfiguration(
            model_id="ai-model-pro",
            model_version="v1.0",
            temperature=0.3,
            top_k=40,
            top_p=0.95
        ),
        AIModelConfiguration(
            model_id="ai-model-flash",
            model_version="v1.0", 
            temperature=0.3,
            top_k=40,
            top_p=0.95
        ),
        AIModelConfiguration(
            model_id="ai-model-flash-lite",
            model_version="preview-06-17",
            temperature=0.3,
            top_k=40,
            top_p=0.95
        )
    ]
    
    print("🔧 AI System Testing Framework")
    print("This framework provides comprehensive testing capabilities for AI systems.")
    print("Key features:")
    print("• Statistical validation with multiple test runs")
    print("• Model comparison and ranking")
    print("• Production environment replication")
    print("• Detailed reporting and analysis")
    print("\nTo use this framework:")
    print("1. Implement AISystemInterface for your AI system")
    print("2. Define test cases with validation functions")
    print("3. Configure AI model parameters to test")
    print("4. Run comprehensive test suite")
    print("5. Analyze results and generate reports")
