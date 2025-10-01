#!/usr/bin/env python3
"""
ITERATION 1: Simple Component Testing

This represents the initial approach to testing AI system components in isolation.
While this approach was insufficient for reproducing production failures, it 
provided valuable baseline validation of individual components.

Original inspiration: Basic validation that AI components work individually
Date: Early in debugging process
Status: SUPERSEDED by more comprehensive approaches
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional

# Basic configuration - initially thought to be sufficient
BASIC_AI_MODEL = "llm-model-basic"  # Not production model
MATH_EVAL_API = "https://api.math-evaluation.com/eval"
TEST_API_KEY = "test_key_123"

class SimpleAITester:
    """
    Initial testing approach: Test individual components with simple inputs.
    
    LESSONS LEARNED:
    - Component isolation testing insufficient for AI systems
    - Simple test cases don't capture production complexity
    - Missing environmental factors and configuration nuances
    """
    
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_basic_llm_generation(self) -> Dict[str, Any]:
        """
        Test basic LLM mathematical code generation.
        
        ASSUMPTION (WRONG): If LLM works for simple cases, it works for complex ones.
        REALITY: AI performance highly dependent on prompt complexity and context.
        """
        simple_prompt = "Generate mathematical code to solve: x^2 + 5x + 6 = 0"
        
        # Basic LLM call - missing many production parameters
        response = await self._call_llm_basic(simple_prompt)
        
        # Simple validation - not sufficient for production quality
        success = (
            "Solve[" in response.get("content", "") and
            "x^2 + 5x + 6 == 0" in response.get("content", "")
        )
        
        return {
            "test_name": "basic_llm_generation",
            "success": success,
            "response": response.get("content", ""),
            "lessons": [
                "Simple prompts don't reflect production complexity",
                "Basic success criteria miss quality nuances",
                "Missing production model configuration"
            ]
        }
    
    async def test_math_api_basic_call(self) -> Dict[str, Any]:
        """
        Test mathematical evaluation API with known-good input.
        
        ASSUMPTION (PARTIALLY CORRECT): API issues should be observable with direct calls.
        REALITY: Some API issues only manifest with AI-generated inputs.
        """
        test_expression = "Solve[x^2 + 5x + 6 == 0, x]"
        
        try:
            result = await self._call_math_eval_api(test_expression)
            
            # Basic validation - missed edge cases
            success = result.get("status") == "success" and "x" in result.get("output", "")
            
            return {
                "test_name": "math_api_basic",
                "success": success,
                "result": result,
                "lessons": [
                    "Known-good inputs work, but AI-generated inputs may fail",
                    "API can return valid-looking but incorrect results",
                    "Need to test with realistic AI-generated inputs"
                ]
            }
            
        except Exception as e:
            return {
                "test_name": "math_api_basic",
                "success": False,
                "error": str(e),
                "lessons": ["API connectivity issues need investigation"]
            }
    
    async def test_simple_integration(self) -> Dict[str, Any]:
        """
        Test basic integration: LLM generates code, API evaluates it.
        
        ASSUMPTION (WRONG): Simple integration test captures production behavior.
        REALITY: Production integration much more complex with multiple failure modes.
        """
        # Step 1: Generate mathematical code
        prompt = "Create mathematical expression to find roots of x^2 + 3x + 2 = 0"
        llm_response = await self._call_llm_basic(prompt)
        
        if not llm_response.get("success"):
            return {"test_name": "simple_integration", "success": False, "stage": "llm_generation"}
        
        # Step 2: Extract mathematical code (simplified extraction)
        code = self._extract_math_code_simple(llm_response.get("content", ""))
        
        if not code:
            return {"test_name": "simple_integration", "success": False, "stage": "code_extraction"}
        
        # Step 3: Evaluate mathematical code
        eval_result = await self._call_math_eval_api(code)
        
        success = eval_result.get("status") == "success"
        
        return {
            "test_name": "simple_integration",
            "success": success,
            "llm_code": code,
            "eval_result": eval_result,
            "lessons": [
                "Simple integration misses production complexity",
                "No testing of error handling or edge cases",
                "Missing realistic data flow and validation steps"
            ]
        }
    
    async def _call_llm_basic(self, prompt: str) -> Dict[str, Any]:
        """
        Basic LLM API call - missing many production parameters.
        
        MISSING CRITICAL ELEMENTS:
        - Production model version
        - Temperature, top-k, top-p parameters  
        - System instructions
        - Response format specifications
        - Complex JSON schema requirements
        """
        url = "https://api.ai-service.com/generate"
        
        data = {
            "model": BASIC_AI_MODEL,  # Wrong model!
            "prompt": prompt,
            "max_tokens": 500  # Too small for production
            # Missing: temperature, top_k, top_p, system_instruction, response_schema
        }
        
        try:
            async with self.session.post(url, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return {"success": True, "content": result.get("text", "")}
                else:
                    return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _call_math_eval_api(self, expression: str) -> Dict[str, Any]:
        """
        Mathematical evaluation API call - basic implementation.
        
        MISSING ELEMENTS:
        - Production timeout settings
        - Retry logic
        - Error classification
        - Response validation
        """
        try:
            encoded_expr = expression.replace(" ", "%20")
            url = f"{MATH_EVAL_API}?input={encoded_expr}"
            
            async with self.session.get(url, headers={"Authorization": f"Bearer {TEST_API_KEY}"}) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return {"status": "success", "output": result.get("output", "")}
                else:
                    return {"status": "error", "message": f"HTTP {resp.status}"}
                    
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _extract_math_code_simple(self, llm_response: str) -> Optional[str]:
        """
        Simple mathematical code extraction - insufficient for production.
        
        PROBLEMS:
        - Basic regex patterns miss complex expressions
        - No handling of multiple code blocks
        - No validation of extracted code
        """
        import re
        
        # Simple pattern - misses many valid expressions
        pattern = r"Solve\[[^\]]+\]"
        matches = re.findall(pattern, llm_response)
        
        return matches[0] if matches else None

async def run_simple_tests():
    """
    Run the initial simple testing approach.
    
    RESULTS SUMMARY:
    - Basic component functionality: ✅ PASS
    - Production failure reproduction: ❌ FAIL  
    - Complex integration testing: ❌ FAIL
    
    CONCLUSION: Simple testing insufficient for AI system debugging.
    """
    print("🧪 ITERATION 1: Simple Component Testing")
    print("=" * 60)
    
    async with SimpleAITester() as tester:
        # Test 1: Basic LLM generation
        llm_test = await tester.test_basic_llm_generation()
        print(f"LLM Basic Test: {'✅ PASS' if llm_test['success'] else '❌ FAIL'}")
        
        # Test 2: Math API basic call
        api_test = await tester.test_math_api_basic_call()
        print(f"Math API Test: {'✅ PASS' if api_test['success'] else '❌ FAIL'}")
        
        # Test 3: Simple integration
        integration_test = await tester.test_simple_integration()
        print(f"Integration Test: {'✅ PASS' if integration_test['success'] else '❌ FAIL'}")
        
        print("\n📊 ITERATION 1 RESULTS:")
        print("- ✅ Confirmed basic component functionality")
        print("- ❌ Failed to reproduce production failures")
        print("- ❌ Missed environmental configuration differences")
        print("- ❌ Oversimplified integration complexity")
        
        print("\n🎓 LESSONS LEARNED:")
        print("1. AI systems require more than component-level testing")
        print("2. Production environment factors critically important")
        print("3. Simple test cases don't capture AI behavior complexity")
        print("4. Need systematic approach to configuration management")
        
        print("\n➡️  NEXT ITERATION: Model comparison and configuration testing")

if __name__ == "__main__":
    asyncio.run(run_simple_tests())
