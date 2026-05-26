"""
data/data_quality_layer.py — Production-Grade Data Quality & Integrity Layer (GAP 3)

Features:
  - Schema validation (Pydantic)
  - Data completeness checks
  - Outlier detection (Z-score, IQR)
  - Corporate action adjustments
  - Data lineage tracking
  - Quality scoring
"""

import hashlib
import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import pydantic
from pydantic import BaseModel, Field, field_validator


class QualityLevel(Enum):
    """Data quality levels."""
    CRITICAL = "critical"      # Missing/broken data
    LOW = "low"                # Many issues
    MEDIUM = "medium"          # Some issues
    HIGH = "high"              # Minor issues
    EXCELLENT = "excellent"    # No issues


class DataType(Enum):
    """Supported data types."""
    TICK = "tick"
    OHLCV = "ohlcv"
    ORDER_BOOK = "order_book"
    TRADE = "trade"
    CORPORATE_ACTION = "corporate_action"


class DataQualityIssue(BaseModel):
    """Single data quality issue."""
    issue_type: str
    severity: QualityLevel
    field: str
    value: Any
    expected: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""


class DataQualityReport(BaseModel):
    """Complete data quality report."""
    dataset_id: str
    data_type: DataType
    record_count: int
    quality_score: float  # 0-100
    level: QualityLevel
    issues: List[DataQualityIssue] = []
    checks_passed: Dict[str, bool] = {}
    lineage_hash: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SchemaValidator(BaseModel):
    """Pydantic-based schema validator for market data."""
    symbol: str = Field(..., min_length=1, max_length=20)
    timestamp: datetime
    price: float = Field(..., gt=0)
    volume: float = Field(default=0.0, ge=0)
    
    # Optional fields
    bid: Optional[float] = None
    ask: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    
    @field_validator('price')
    @classmethod
    def price_not_nan(cls, v):
        if v != v:  # NaN check
            raise ValueError('Price cannot be NaN')
        return v
    
    @field_validator('timestamp')
    @classmethod
    def timestamp_not_future(cls, v):
        # Handle both offset-naive and offset-aware datetimes
        now = datetime.now(timezone.utc)
        # If timestamp is naive, assume it's UTC
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v > now:
            raise ValueError('Timestamp cannot be in the future')
        return v


class DataQualityLayer:
    """
    Production-grade data quality and integrity layer.
    
    Features:
      - Schema validation (Pydantic)
      - Data completeness checks
      - Outlier detection (Z-score, IQR)
      - Corporate action adjustments
      - Data lineage tracking
      - Quality scoring
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._lineage_log: List[Dict] = []
        self._quality_cache: Dict[str, DataQualityReport] = {}

    def validate_schema(self, data: Dict[str, Any], data_type: DataType) -> Tuple[bool, List[str]]:
        """
        Validate data against schema.
        
        Args:
            data: Data dict to validate
            data_type: Type of data (tick, ohlcv, etc.)
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            if data_type == DataType.TICK:
                SchemaValidator(**data)
            elif data_type == DataType.OHLCV:
                # OHLCV specific validation
                required = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
                for field in required:
                    if field not in data:
                        errors.append(f"Missing required field: {field}")
                
                if not errors:
                    # OHLCV consistency checks
                    if data['high'] < data['low']:
                        errors.append("High < Low")
                    if data['high'] < data['open'] or data['high'] < data['close']:
                        errors.append("High < Open or Close")
                    if data['low'] > data['open'] or data['low'] > data['close']:
                        errors.append("Low > Open or Close")
            else:
                # Generic validation
                if 'symbol' not in data:
                    errors.append("Missing symbol")
                if 'timestamp' not in data:
                    errors.append("Missing timestamp")
        except pydantic.ValidationError as e:
            errors.extend([err['msg'] for err in e.errors()])
        
        return len(errors) == 0, errors

    def check_completeness(self, data: List[Dict], expected_fields: List[str]) -> Tuple[float, List[str]]:
        """
        Check data completeness.
        
        Args:
            data: List of data records
            expected_fields: List of expected field names
        
        Returns:
            (completeness_score 0-1, list_of_missing_fields)
        """
        if not data:
            return 0.0, ["No data records"]
        
        missing_counts = {field: 0 for field in expected_fields}
        
        for record in data:
            for field in expected_fields:
                if field not in record or record[field] is None:
                    missing_counts[field] += 1
        
        total_records = len(data)
        completeness_scores = [1 - (missing_counts[f] / total_records) for f in expected_fields]
        avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0
        
        missing_fields = [f for f, count in missing_counts.items() if count > 0]
        
        return avg_completeness, missing_fields

    def detect_outliers_zscore(self, values: List[float], threshold: float = 3.0) -> List[int]:
        """
        Detect outliers using Z-score method.
        
        Args:
            values: List of numeric values
            threshold: Z-score threshold (default 3.0)
        
        Returns:
            List of outlier indices
        """
        if len(values) < 3:
            return []
        
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0
        
        if stdev == 0:
            return []
        
        outliers = []
        for i, v in enumerate(values):
            z_score = abs((v - mean) / stdev)
            if z_score > threshold:
                outliers.append(i)
        
        return outliers

    def detect_outliers_iqr(self, values: List[float], multiplier: float = 1.5) -> List[int]:
        """
        Detect outliers using IQR method.
        
        Args:
            values: List of numeric values
            multiplier: IQR multiplier (default 1.5)
        
        Returns:
            List of outlier indices
        """
        if len(values) < 4:
            return []
        
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[(3 * n) // 4]
        iqr = q3 - q1
        
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        outliers = []
        for i, v in enumerate(values):
            if v < lower_bound or v > upper_bound:
                outliers.append(i)
        
        return outliers

    def compute_quality_score(
        self,
        data: List[Dict],
        schema_valid: bool,
        completeness: float,
        outlier_ratio: float,
    ) -> Tuple[float, QualityLevel]:
        """
        Compute overall quality score (0-100) and level.
        
        Args:
            data: Data records
            schema_valid: Whether schema validation passed
            completeness: Completeness score (0-1)
            outlier_ratio: Ratio of outliers (0-1)
        
        Returns:
            (quality_score, quality_level)
        """
        # Weighted scoring
        schema_weight = 0.4
        completeness_weight = 0.3
        outlier_weight = 0.3
        
        schema_score = 100.0 if schema_valid else 0.0
        completeness_score = completeness * 100.0
        outlier_score = (1 - outlier_ratio) * 100.0
        
        quality_score = (
            schema_weight * schema_score +
            completeness_weight * completeness_score +
            outlier_weight * outlier_score
        )
        
        # Determine level
        if quality_score >= 95:
            level = QualityLevel.EXCELLENT
        elif quality_score >= 80:
            level = QualityLevel.HIGH
        elif quality_score >= 60:
            level = QualityLevel.MEDIUM
        elif quality_score >= 40:
            level = QualityLevel.LOW
        else:
            level = QualityLevel.CRITICAL
        
        return quality_score, level

    def compute_lineage_hash(self, data: List[Dict]) -> str:
        """
        Compute cryptographic hash for data lineage tracking.
        
        Args:
            data: Data records
        
        Returns:
            SHA-256 hash hex string
        """
        # Serialize deterministically
        serialized = json.dumps(data, sort_keys=True, default=str).encode('utf-8')
        return hashlib.sha256(serialized).hexdigest()

    def validate_dataset(
        self,
        data: List[Dict],
        data_type: DataType,
        dataset_id: str,
        expected_fields: List[str] = None,
    ) -> DataQualityReport:
        """
        Complete dataset validation.
        
        Args:
            data: List of data records
            data_type: Type of data
            dataset_id: Unique dataset identifier
            expected_fields: List of expected field names
        
        Returns:
            DataQualityReport
        """
        issues = []
        checks_passed = {}
        
        # 1. Schema validation
        schema_valid = True
        for i, record in enumerate(data[:100]):  # Sample first 100
            valid, errors = self.validate_schema(record, data_type)
            if not valid:
                schema_valid = False
                for err in errors[:5]:  # Limit errors per record
                    issues.append(DataQualityIssue(
                        issue_type="schema_violation",
                        severity=QualityLevel.HIGH,
                        field="multiple",
                        value=record.get("symbol", "unknown"),
                        expected="valid schema",
                        description=f"Record {i}: {err}"
                    ))
        
        checks_passed["schema_valid"] = schema_valid
        
        # 2. Completeness check
        if expected_fields:
            completeness, missing = self.check_completeness(data, expected_fields)
            checks_passed["completeness"] = completeness >= 0.95
            if completeness < 0.95:
                for field in missing:
                    issues.append(DataQualityIssue(
                        issue_type="missing_field",
                        severity=QualityLevel.MEDIUM,
                        field=field,
                        value=None,
                        expected="present in all records"
                    ))
        else:
            completeness = 1.0
        
        # 3. Outlier detection
        prices = [r.get('price', r.get('close', 0)) for r in data if r.get('price') or r.get('close')]
        if prices:
            outlier_indices = self.detect_outliers_zscore(prices, threshold=3.0)
            outlier_ratio = len(outlier_indices) / len(prices)
            checks_passed["outlier_check"] = outlier_ratio < 0.05
            
            if outlier_ratio >= 0.05:
                issues.append(DataQualityIssue(
                    issue_type="outliers_detected",
                    severity=QualityLevel.MEDIUM,
                    field="price",
                    value=f"{len(outlier_indices)} outliers",
                    expected="< 5% outliers",
                    description=f"Z-score > 3.0 for {len(outlier_indices)} records"
                ))
        else:
            outlier_ratio = 0.0
        
        # 4. Compute quality score
        quality_score, quality_level = self.compute_quality_score(
            data, schema_valid, completeness, outlier_ratio
        )
        
        # 5. Compute lineage hash
        lineage_hash = self.compute_lineage_hash(data)
        
        # 6. Create report
        report = DataQualityReport(
            dataset_id=dataset_id,
            data_type=data_type,
            record_count=len(data),
            quality_score=quality_score,
            level=quality_level,
            issues=issues[:50],  # Limit issues
            checks_passed=checks_passed,
            lineage_hash=lineage_hash,
        )
        
        # Cache report
        self._quality_cache[dataset_id] = report
        
        # Log lineage
        self._lineage_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset_id": dataset_id,
            "quality_score": quality_score,
            "lineage_hash": lineage_hash,
        })
        
        return report

    def get_quality_report(self, dataset_id: str) -> Optional[DataQualityReport]:
        """Get cached quality report."""
        return self._quality_cache.get(dataset_id)

    def get_lineage_history(self, dataset_id: Optional[str] = None) -> List[Dict]:
        """Get lineage history."""
        if dataset_id:
            return [log for log in self._lineage_log if log.get("dataset_id") == dataset_id]
        return self._lineage_log

    def adjust_for_corporate_action(
        self,
        data: List[Dict],
        action_type: str,
        ratio: float,
        adjustment_date: datetime,
    ) -> List[Dict]:
        """
        Adjust historical data for corporate actions (splits, dividends).
        
        Args:
            data: Historical price data
            action_type: "split", "reverse_split", "dividend"
            ratio: Adjustment ratio (e.g., 2.0 for 2:1 split)
            adjustment_date: Date of corporate action
        
        Returns:
            Adjusted data
        """
        adjusted = []
        
        for record in data:
            record_ts = record.get("timestamp")
            if isinstance(record_ts, str):
                record_ts = datetime.fromisoformat(record_ts.replace("Z", "+00:00"))
            
            # Only adjust records before corporate action
            if record_ts and record_ts < adjustment_date:
                adjusted_record = record.copy()
                
                if action_type in ["split", "reverse_split"]:
                    # Adjust prices
                    for price_field in ['open', 'high', 'low', 'close', 'price']:
                        if price_field in adjusted_record and adjusted_record[price_field]:
                            adjusted_record[price_field] = adjusted_record[price_field] / ratio
                    
                    # Adjust volume (inverse for splits)
                    if 'volume' in adjusted_record:
                        adjusted_record['volume'] = adjusted_record['volume'] * ratio
                
                elif action_type == "dividend":
                    # Subtract dividend from price
                    for price_field in ['open', 'high', 'low', 'close', 'price']:
                        if price_field in adjusted_record and adjusted_record[price_field]:
                            adjusted_record[price_field] = adjusted_record[price_field] - ratio
                
                adjusted.append(adjusted_record)
            else:
                adjusted.append(record)
        
        return adjusted
