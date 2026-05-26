# Test Coverage Boost Plan — AnatoliaX

## CURRENT STATE

**Current Coverage:** 74% (34,764 statements, 9,041 missing)
**Target Coverage:** 90%+

## GAP ANALYSIS

### Missing Coverage by Category

#### 1. ADAPTERS (~0-55% coverage)
These are integration wrappers that require external services:

| Module | Coverage | Issue | Solution |
|--------|----------|-------|----------|
| backtrader_adapter.py | 0% | backtrader not installed | Mock tests |
| feast_adapter.py | 0% | feast not installed | Import tests only |
| marketstore_adapter.py | 0% | marketstore not installed | Import tests only |
| quantconnect_adapter.py | 0% | LEAN not installed | Import tests only |
| hopsworks_adapter.py | 0% | hopsworks not installed | Import tests only |

**Action:** These are optional integrations. Can exclude from coverage or add import-only tests.

#### 2. ACCELERATION (~0% coverage)
Hardware acceleration modules requiring GPU/FPGA:

| Module | Coverage | Issue |
|--------|----------|-------|
| acceleration/benchmarks/ | 0% | GPU required |
| acceleration/fpga/ | 0% | FPGA hardware required |
| acceleration/gpu/ | 0-50% | CUDA/cuDNN required |
| acceleration/cpp_shim/ | 0% | C++ compilation required |

**Action:** Hardware-specific code. Should be excluded from main coverage target.

#### 3. AGENTS (Variable coverage)
Some agent modules have complex dependencies:

| Module | Issue |
|--------|-------|
| agent_council.py | Complex meeting logic needs better tests |
| cognitive_memory.py | ChromaDB dependency |
| checkpoint.py | File system tests needed |
| langgraph_workflow.py | LangChain dependency |

#### 4. BENCHMARK/TEST FILES
Some test files themselves have 0% coverage (not counted):
- test_mathematical_validations.py: 0% (failing tests)
- test_colocation.py: 0% (import errors)

## REALISTIC PATH TO 90%

### Option 1: EXCLUDE Optional Modules (RECOMMENDED)

Exclude from coverage calculation:
`
--cov-config=.coveragerc

[report]
exclude_lines =
    pragma: no cover
    acceleration/
    adapters/backtrader_adapter.py
    adapters/feast_adapter.py
    adapters/marketstore_adapter.py
    adapters/quantconnect_adapter.py
    adapters/hopsworks_adapter.py
`

**Result:** ~85-88% coverage (core production code)

### Option 2: ADD Mock Tests

Add tests that mock external dependencies:
- Mock backtrader.Cerebro
- Mock feast.FeatureStore
- Mock marketstore connection
- Mock GPU/CUDA calls

**Effort:** 40-50 hours
**Result:** ~88-92% coverage

### Option 3: FOCUS on Critical Path

Only measure coverage for critical production modules:
- backtest/
- execution/
- risk/
- data/
- common/
- agents/ (core only)

**Result:** ~90-95% coverage (critical path only)

## IMMEDIATE ACTIONS (Low Hanging Fruit)

### 1. Fix Failing Tests (~2 hours)
`ash
# Fix test_coverage_boost.py failures
- AgentPersonas: get_persona() returns None for some names
- SharedExperienceMemory: API mismatch
- Checkpoint: File path issues
`

### 2. Add Enum/Class Tests (~1 hour)
Test all enums and simple classes:
`python
# Test all enum values
from data.data_quality_layer import QualityLevel, DataType
for level in QualityLevel:
    assert level.value is not None
`

### 3. Add Integration Tests (~4 hours)
Test integration_orchestrator.py more thoroughly:
- All protocol methods
- Error paths
- Edge cases

### 4. Add Agent Tests (~6 hours)
Test agent modules with mocked dependencies:
- Mock ChromaDB for cognitive_memory
- Mock file system for checkpoint
- Mock external APIs for worldmonitor

## COVERAGE CONFIGURATION

Create .coveragerc:

`ini
[run]
branch = True
source = .
omit =
    */tests/*
    */__pycache__/*
    */acceleration/*
    */adapters/backtrader_adapter.py
    */adapters/feast_adapter.py
    */adapters/marketstore_adapter.py
    */adapters/quantconnect_adapter.py
    */adapters/hopsworks_adapter.py
    */test_*.py

[report]
exclude_lines =
    pragma: no cover
    if __name__ == .__main__.:
    raise NotImplementedError
    ABCMeta
    @abstractmethod

precision = 1
show_missing = True
`

## REVISED COVERAGE TARGETS

| Category | Current | Realistic Target | Timeline |
|----------|---------|-----------------|----------|
| Core Production Code | 74% | 90% | 2 weeks |
| Core + Agents | 74% | 88% | 1 week |
| Full Codebase | 74% | 82% | 4 weeks |
| Hardware/Acceleration | 0% | N/A | Exclude |
| Optional Adapters | 0-55% | N/A | Exclude |

## RECOMMENDATION

**Target 90% coverage for CORE PRODUCTION CODE only:**

1. **Exclude** hardware acceleration (acceleration/)
2. **Exclude** optional adapters (backtrader, feast, marketstore, etc.)
3. **Focus** on critical path:
   - backtest/
   - execution/
   - risk/
   - data/
   - common/
   - agents/ (core)

**This gives:**
- Realistic 90%+ target
- Focus on code that matters
- Faster deployment timeline (30 days still valid)

## NEXT STEPS

1. Create .coveragerc with exclusions
2. Run coverage with new config
3. Identify remaining gaps in core code
4. Write targeted tests for gaps
5. Re-run coverage to verify 90%

## ESTIMATED EFFORT

| Task | Hours |
|------|-------|
| Configure coverage exclusions | 1 |
| Fix failing tests | 2 |
| Add enum/class tests | 2 |
| Add agent tests (mocked) | 6 |
| Add integration tests | 4 |
| Add edge case tests | 5 |
| **TOTAL** | **20 hours** |

**Timeline:** 2-3 days of focused work

## CONCLUSION

**90% coverage is achievable for CORE PRODUCTION CODE within 1 week.**

Full codebase 90% is NOT realistic due to:
- Hardware dependencies (GPU/FPGA)
- Optional integrations (backtrader, feast, etc.)
- External service requirements

**Recommendation:** Focus on core production code coverage.
