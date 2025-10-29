# Open Interest Multiple Timeframes - Tests Summary

## Overview
Comprehensive test suite for Open Interest monitoring across multiple timeframes with specific threshold ranges for different trading signals.

## Timeframes Configuration

### 1. 1-Minute Timeframe (5-8%)
**Purpose:** Big liquidations detection  
**Threshold:** 5.0% - 8.0%  
**Use Case:** Identifies sudden large liquidation events
- 5.26% = Minimum big liquidation
- 6.38% = Medium liquidation  
- 8.11% = Maximum liquidation
- >9% = Extreme/suspicious movement

### 2. 5-Minute Timeframe (2%)
**Purpose:** Fast movements detection  
**Threshold:** ≥2.0%  
**Use Case:** Captures rapid market movements
- 2.04% = Fast movement detected
- 2.56% = Significant fast movement
- <2% = Normal market activity

### 3. 15-Minute Timeframe (3%)
**Purpose:** Short-term trends  
**Threshold:** ≥3.0%  
**Use Case:** Identifies emerging short-term trends
- 3.09% = Short trend forming
- 3.63% = Strong short trend
- <3% = No clear trend

### 4. 30-Minute Timeframe (4-5%)
**Purpose:** Middle-term trends  
**Threshold:** 4.0% - 5.5%  
**Use Case:** Confirms medium-term market direction
- 4.17% = Middle trend starting
- 4.71% = Established middle trend
- 5.04% = Strong middle trend
- >5.5% = Transitioning to longer trend

### 5. 60-Minute Timeframe (6-8%)
**Purpose:** Big trends confirmation  
**Threshold:** 6.0% - 9.0%  
**Use Case:** Validates major market trends
- 6.38% = Big trend detected
- 7.53% = Strong big trend
- 8.11% = Very strong trend
- >9% = Extreme market condition

## Test Suite Structure

### Test File: `tests/test_openinterest.py`

Total Tests: **10**

1. **test_timeframe_configuration**
   - Validates all 5 timeframe configurations
   - Ensures thresholds are properly set

2. **test_1min_big_liquidations_5_to_8_percent**
   - Tests 1-minute liquidation detection
   - Validates 5-8% range

3. **test_5min_fast_movements_2_percent**
   - Tests 5-minute fast movement detection
   - Validates ≥2% threshold

4. **test_15min_short_trends_3_percent**
   - Tests 15-minute short trend detection
   - Validates ≥3% threshold

5. **test_30min_middle_trends_4_to_5_percent**
   - Tests 30-minute middle trend detection
   - Validates 4-5.5% range

6. **test_60min_big_trends_6_to_8_percent**
   - Tests 60-minute big trend detection
   - Validates 6-9% range

7. **test_all_timeframes_integration**
   - Integration test for all timeframes
   - Validates concurrent monitoring

8. **test_negative_changes**
   - Tests OI decreases (falling markets)
   - Validates absolute value calculations

9. **test_boundary_conditions**
   - Tests edge cases for all timeframes
   - Ensures precise threshold behavior

10. **test_zero_and_null_handling**
    - Tests error conditions
    - Validates division by zero protection

## Code Updates

### Modified Files

1. **services/monitoring_service.py**
   - Updated timeframes array with 5 timeframes
   - Added threshold comments for clarity
   - Updated timeframe display names mapping

2. **tests/test_openinterest.py** (NEW)
   - 246 lines of comprehensive tests
   - Mock-based testing approach
   - Full coverage of all timeframes

## Test Results

```
============================= 56 passed in 14.06s ==============================
```

### Breakdown:
- Security tests: 11/11 ✅
- Database tests: 11/11 ✅
- WebSocket tests: 24/24 ✅
- **Open Interest tests: 10/10 ✅**

Total: **56 tests passing**

## Usage Example

### In Code:
```python
# Configure user settings with multiple timeframes
settings = {
    'oi_threshold_1min': 5.0,   # Big liquidations
    'oi_threshold_5min': 2.0,   # Fast movements
    'oi_threshold_15min': 3.0,  # Short trends
    'oi_threshold_30min': 4.0,  # Middle trends
    'oi_threshold_60min': 6.0,  # Big trends
}

# Monitor will check all timeframes
alerts = await monitoring_service.check_open_interest_changes(coins, settings)
```

### Alert Messages:
```
📈 BTC OI increase
⏱ Период: 1 минута
Change: +6.54%
Current: 106,540
Previous: 100,000
```

## Running Tests

```bash
# Run only Open Interest tests
pytest tests/test_openinterest.py -v

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/test_openinterest.py --cov=services --cov-report=html
```

## Benefits

1. **Multi-Timeframe Analysis**
   - Captures signals from micro (1min) to macro (60min)
   - Different thresholds for different purposes

2. **False Positive Reduction**
   - 1min requires 5-8% (filters noise)
   - Longer timeframes require smaller % (confirmed trends)

3. **Comprehensive Testing**
   - 10 dedicated tests
   - Edge cases covered
   - Integration tested

4. **Production Ready**
   - All tests passing
   - Error handling validated
   - Boundary conditions tested

## Technical Details

### Threshold Logic
```python
# Example: 1-minute timeframe
if 5.0 <= abs(change_percent) < 9.0:
    # Alert: Big liquidation detected
```

### Calculation
```python
change_percent = ((current_oi - previous_oi) / previous_oi) * 100
```

### Safety Checks
- Division by zero protection
- Null value handling
- Range validation
- Symbol sanitization

## Next Steps

1. ✅ Tests created and passing
2. ✅ Service updated with all timeframes
3. 🔄 Deploy to production
4. 📊 Monitor real-world performance
5. 🎯 Fine-tune thresholds based on data

---

**Date:** October 29, 2025  
**Status:** ✅ Complete  
**Tests:** 10/10 Passing  
**Coverage:** Multiple timeframes with specific thresholds
