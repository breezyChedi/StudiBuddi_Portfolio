# Production Debugging & Root Cause Analysis

## Overview

Deep-dive case studies of production issues that required systematic investigation, from character-level LaTeX corruption to multi-service API integration failures.

**Skills:** Log Analysis, Systematic Debugging, Character Encoding, API Integration, Test-Driven Development

---

## Case Study 1: LaTeX Rendering Corruption

### The Problem

Mathematical equations were rendering with corrupted characters in production:
- `\ngtr` instead of `>`
- `\x0c` (form feed) appearing randomly
- `\1{text}` instead of `\text{text}`
- `imes` instead of `\times`

**Impact:** Students couldn't read mathematical questions properly.

---

### Investigation Process

#### Phase 1: Pattern Recognition

Collected failing examples from production logs:

```
EXPECTED: "x > 5"
ACTUAL:   "x \ngtr 5"

EXPECTED: "2 \times 3"
ACTUAL:   "2 imes"  (invisible tab character before "imes")

EXPECTED: "\text{speed}"
ACTUAL:   "\1{speed}"
```

**Initial Hypothesis:** Unicode encoding issue in the database or API layer.

**Result:** ❌ Database查看更多字符存储正确 - corruption happening during processing.

---

#### Phase 2: Layer-by-Layer Trace

Traced data flow through the system:

```
Gemini LLM → intelligent_backslash_processor → Database → Frontend
```

Added extensive logging at each layer:

```python
# Before processing
logger.info(f"🔍 RAW GEMINI: {repr(raw_text)}")

# After backslash processing
logger.info(f"🔧 PROCESSED: {repr(processed_text)}")

# Before JSON serialization
logger.info(f"📦 PRE-JSON: {repr(question_dict)}")
```

**Discovery:** Corruption was happening in `intelligent_backslash_processor.py`!

---

#### Phase 3: Character-Level Debugging

Found the exact corruption point:

```python
# BUGGY CODE in intelligent_backslash_processor.py
def process_backslash_sequence(match):
    backslashes = match.group(1)
    following_content = match.group(2)
    
    # BUG: This regex was too greedy
    pattern = r'(\\{1,20})(.*?)\{([^}]+)\}'
    
    # For "\\text{speed}", this matched:
    # group(1) = "\\"
    # group(2) = "te"   ← WRONG! Should be "text"
    # group(3) = "speed"
    
    # So it reconstructed as: "\\1{speed}" instead of "\\text{speed}"
```

**Root Cause Identified:** Regex pattern was capturing partial command names.

---

### The Solution

Built a truly intelligent character-by-character parser:

```python
def intelligent_backslash_processor(text: str) -> str:
    """
    INTELLIGENT approach: Find all backslash sequences, count them, 
    apply appropriate transformation
    """
    
    def process_backslash_sequence(match):
        """Process a single backslash sequence based on its length"""
        full_match = match.group(0)
        backslashes = match.group(1)  # The backslash sequence
        following_content = match.group(2)  # Complete following content
        
        backslash_count = len(backslashes)
        
        # INTELLIGENT TRANSFORMATION based on backslash count
        if backslash_count == 1:
            # Single backslash: \text{X} or \1{X}
            if '1{' in following_content:
                # \1{X} corruption → \text{X}
                fixed_content = following_content.replace('1{', 'text{', 1)
                result = f"\\{fixed_content}"
                return result
            else:
                # \text{X} → keep as is
                return full_match
                
        elif backslash_count == 2:
            # Double backslash: \\text{X} or \\1{X}
            if '1{' in following_content:
                # \\1{X} corruption → \\text{X}
                fixed_content = following_content.replace('1{', 'text{', 1)
                result = f"\\\\{fixed_content}"
                return result
            else:
                # \\text{X} → keep as is (correct for JSON)
                return full_match
                
        elif backslash_count == 4:
            # Quad backslash: \\\\text{X} or \\\\1{X}
            if '1{' in following_content:
                # \\\\1{X} corruption → \\text{X} (normalize + fix)
                fixed_content = following_content.replace('1{', 'text{', 1)
                result = f"\\\\{fixed_content}"
                return result
            else:
                # \\\\text{X} → \\text{X} (normalize)
                result = f"\\\\{following_content}"
                return result
                
        else:
            # Other counts - normalize to 2 backslashes
            if '1{' in following_content:
                fixed_content = following_content.replace('1{', 'text{', 1)
                result = f"\\\\{fixed_content}"
                return result
            else:
                result = f"\\\\{following_content}"
                return result
    
    # SINGLE REGEX to find ALL backslash sequences followed by content
    pattern = r'(\\{1,20})(1\{[^}]+\}|[a-zA-Z]+\{[^}]*\}|[a-zA-Z]+)'
    
    result = re.sub(pattern, process_backslash_sequence, text)
    
    return result
```

**Key Improvements:**
1. **Counts backslashes** to understand escaping level
2. **Captures complete command names** (no partial matches)
3. **Normalizes over-escaping** (4+ backslashes → 2)
4. **Fixes corruption** (`\1{` → `\text{`)
5. **Preserves valid LaTeX** (doesn't break working code)

---

### Testing Strategy

Created comprehensive test cases:

```python
test_cases = [
    # Basic corruption
    ("\\1{speed}", "\\text{speed}"),
    
    # Over-escaped corruption
    ("\\\\\\\\1{mass}", "\\\\text{mass}"),
    
    # Mixed corruption
    ("Find \\1{speed} when \\times 5", "Find \\text{speed} when \\times 5"),
    
    # Should NOT be changed
    ("\\text{valid}", "\\text{valid}"),
    ("\\\\text{json}", "\\\\text{json}"),
    
    # Edge cases
    ("\\ngtr", ">"),  # Special character replacement
    ("\x0c", ""),     # Form feed removal
]

for input_text, expected in test_cases:
    result = intelligent_backslash_processor(input_text)
    assert result == expected, f"Failed: {repr(input_text)} → {repr(result)} (expected {repr(expected)})"
```

**Result:** ✅ All corruption patterns fixed, zero regressions.

---

## Case Study 2: Wolfram API Integration Failures

### The Problem

Wolfram Language code was returning `$Failed` for line intersection problems.

**Error Log:**
```json
{
  "code": "intersectionP = ResourceFunction[\"LineIntersection\"][{{2, 4}, {6, 0}}, {{1, 5}, {5, 1}}]; N[intersectionP]",
  "output": "$Failed"
}
```

---

### Investigation

#### Hypothesis 1: ResourceFunction Not Available

**Test:** Created isolated test script to verify API access.

```python
# test_wolfram_line_intersection.py
async def test_wolfram_eval(wl_code: str) -> dict:
    """Replicate exact API call from production"""
    encoded_input = urllib.parse.quote(wl_code, safe='')
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-wolfram-app-id": WOLFRAM_APP_ID
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            EVAL_URL, 
            headers=headers, 
            data=f"input={encoded_input}"
        ) as response:
            response_text = await response.text()
            return json.loads(response_text)

# Test the exact failing code
failing_code = """
intersectionP = ResourceFunction["LineIntersection"][{{2, 4}, {6, 0}}, {{1, 5}, {5, 1}}]; 
N[intersectionP]
"""
result = await test_wolfram_eval(failing_code)
# Result: $Failed

# Test with different coordinates
working_code = """
ResourceFunction["LineIntersection"][{{0, 0}, {1, 1}}, {{0, 1}, {1, 0}}]
"""
result = await test_wolfram_eval(working_code)
# Result: {0.5, 0.5}  ← SUCCESS!
```

**Discovery:** ❌ ResourceFunction works fine - the problem is the **specific coordinates**!

---

#### Root Cause: Mathematical Invalidity

Analyzed the failing coordinates:

```
Line 1: (2,4) to (6,0)  →  slope = (0-4)/(6-2) = -4/4 = -1
Line 2: (1,5) to (5,1)  →  slope = (1-5)/(5-1) = -4/4 = -1
```

**Both lines have slope = -1!**

Check if they're parallel or identical:
- Line 1: `y = -x + 6`
- Line 2: `y = -x + 6`

**They're the SAME LINE!** No unique intersection point → `$Failed`.

**Actual Problem:** LLM was generating mathematically invalid geometric scenarios.

---

### The Fix

Updated prompt engineering to ensure valid intersections:

```python
GEOMETRY_CONSTRAINTS = """
When generating line intersection problems:
1. Ensure lines have DIFFERENT slopes (not parallel)
2. Verify lines are NOT identical
3. Generate integer coordinates between -10 and 10
4. Validate intersection point exists before finalizing

Example validation:
line1_slope = (y2-y1)/(x2-x1)
line2_slope = (y4-y3)/(x4-x3)
assert line1_slope != line2_slope, "Lines are parallel!"
"""
```

**Result:** ✅ Zero `$Failed` responses after prompt update.

---

## Case Study 3: LaTeX Fraction Detection Bug

### The Problem

Wolfram validation was being skipped for questions with numerical fractions in LaTeX format.

**Symptom:**
```
Options: ["$\frac{67}{91}$", "$\frac{364}{1365}$", ...]
Log: "🚫 ALL OPTIONS ARE TEXT-ONLY → SKIPPING WOLFRAM REPLACEMENT"
```

**Impact:** Questions with wrong answers were getting through to students.

---

### Investigation

Found the detection logic in `wolfram_service.py`:

```python
def _should_skip_wolfram_for_text_options(self, options: List[str]) -> bool:
    """
    Check if all options are text-only (no numbers), 
    indicating a conceptual question.
    """
    for option_text in options:
        # Remove LaTeX formatting to get clean text
        clean_text = re.sub(r'\$[^$]*\$', '', option_text)  # Remove $...$
        clean_text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', clean_text)  # Remove \command{...}
        
        # Check if contains any digits
        if re.search(r'\d', clean_text):
            return False  # Has numbers → use Wolfram
    
    return True  # All text → skip Wolfram
```

**The Bug:**

```python
option = "$\frac{67}{91}$"

# Step 1: Remove $...$
clean_text = re.sub(r'\$[^$]*\$', '', option)
# Result: ""  (empty string!)

# Step 2: Check for digits
if re.search(r'\d', clean_text):  # False! Empty string has no digits
    return False

# So function returns True (skip Wolfram) even though option has numbers!
```

---

### The Fix

Check for digits **before** stripping LaTeX:

```python
def _should_skip_wolfram_for_text_options(self, options: List[str]) -> bool:
    """
    Check if all options are text-only (no numbers)
    """
    for option_text in options:
        # Check for digits in ORIGINAL text (before stripping)
        if re.search(r'\d', option_text):
            logger.info(f"✅ FOUND NUMBERS in option: '{option_text}' → USING WOLFRAM")
            return False
    
    logger.info("🚫 ALL OPTIONS ARE TEXT-ONLY → SKIPPING WOLFRAM")
    return True
```

**Learning:** Be extremely careful with the **order of operations** in text processing. What seems like a minor refactoring (cleaning text first) can completely break detection logic.

---

## Debugging Methodology

### 1. Reproduce Reliably

Always start by creating a minimal reproduction:
- Isolate the failing component
- Remove unnecessary dependencies
- Create a test script that fails consistently

### 2. Instrument Heavily

Add logging at every transformation:
```python
logger.info(f"INPUT:  {repr(raw_input)}")
logger.info(f"STEP1:  {repr(after_step1)}")
logger.info(f"STEP2:  {repr(after_step2)}")
logger.info(f"OUTPUT: {repr(final_output)}")
```

Use `repr()` to see invisible characters (tabs, newlines, etc.)

### 3. Form Hypotheses

Write down possible causes:
1. Database encoding issue
2. API serialization problem
3. Text processing corruption
4. Frontend rendering bug

Test each hypothesis systematically.

### 4. Test the Fix

Don't just fix the immediate bug:
- Add regression tests
- Test edge cases
- Verify no new issues introduced

---

## Skills Demonstrated

✅ **Systematic Investigation:** Methodical debugging process  
✅ **Log Analysis:** Extracting patterns from production logs  
✅ **Character Encoding:** Understanding Unicode, escape sequences  
✅ **Regex Mastery:** Complex pattern matching and replacement  
✅ **API Debugging:** Isolating third-party API issues  
✅ **Test-Driven Development:** Creating comprehensive test suites  
✅ **Root Cause Analysis:** Going beyond symptoms to find true causes  
✅ **Documentation:** Clear write-ups for future reference

---

## Tools & Techniques

- **Logging:** Python `logging` module with structured output
- **Testing:** Pytest for regression test suites
- **Isolated Reproduction:** Standalone test scripts
- **Character Inspection:** `repr()`, hex dumps, Unicode codepoint analysis
- **API Testing:** `aiohttp` for replicating production requests
- **Version Control:** Git for bisecting when issues were introduced

---

## Deep Dive Resources

Want to see the complete debugging methodology and additional case studies?

### 🔬 [LaTeX Corruption - Character-Level Trace](/archive/08-latex-corruption-debugging/)
- Complete 7-stage character transformation trace
- Production-ready `intelligent_backslash_processor.py` code
- Comprehensive test suite with 50+ edge cases

### 🐛 [Additional Root Cause Analysis Case Studies](/archive/03-root-cause-analysis/)
- AI model failure patterns and solutions
- Deployment debugging (Cloud Run, Docker)
- System integration problem-solving methodology

