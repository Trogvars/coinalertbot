# Open Interest Multiple Timeframes - Quick Reference

## Timeframe Thresholds

| Timeframe | Threshold | Purpose | Alert Type |
|-----------|-----------|---------|------------|
| 1 min | 5-8% | Big liquidations | 🔴 Critical |
| 5 min | ≥2% | Fast movements | ⚡ High |
| 15 min | ≥3% | Short trends | 📊 Medium |
| 30 min | 4-5% | Middle trends | 📈 Medium |
| 60 min | 6-8% | Big trends | 🎯 Confirmation |

## Configuration

```python
settings = {
    'oi_threshold_1min': 5.0,
    'oi_threshold_5min': 2.0,
    'oi_threshold_15min': 3.0,
    'oi_threshold_30min': 4.0,
    'oi_threshold_60min': 6.0,
}
```

## Test Commands

```bash
# Run OI tests only
pytest tests/test_openinterest.py -v

# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=services --cov-report=html
```

## Files Modified

1. `services/monitoring_service.py` - Added 5 timeframes
2. `tests/test_openinterest.py` - New test file (10 tests)
3. `OPENINTEREST_TESTS_SUMMARY.md` - Documentation

## Test Results

✅ **56/56 tests passing**
- Security: 11
- Database: 11  
- WebSocket: 24
- **Open Interest: 10** ← NEW

## Trading Logic

### 1-Minute (5-8%)
- **Signal:** Big liquidation event
- **Action:** Immediate attention required
- **Example:** OI drops 6.5% in 1 minute → Large position liquidated

### 5-Minute (≥2%)
- **Signal:** Fast market movement
- **Action:** Quick reaction opportunity
- **Example:** OI rises 2.5% in 5 minutes → Money flowing in

### 15-Minute (≥3%)
- **Signal:** Short-term trend forming
- **Action:** Position entry consideration
- **Example:** OI up 3.2% in 15 minutes → Trend starting

### 30-Minute (4-5%)
- **Signal:** Medium-term trend
- **Action:** Trend confirmation
- **Example:** OI up 4.5% in 30 minutes → Established move

### 60-Minute (6-8%)
- **Signal:** Big trend confirmation
- **Action:** High-confidence signal
- **Example:** OI up 7% in 1 hour → Major trend confirmed

---
**Status:** Production Ready ✅
