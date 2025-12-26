"""
Analytics computation engine - pure logic, no DB writes or file I/O
Combines existing attention metrics with engagement timeline analysis
"""
import numpy as np
import statistics
from datetime import datetime
from typing import List, Dict, Any, Optional


# ========== EXISTING FUNCTIONS (YOUR ORIGINAL CODE) ==========

def calculate_attention_score(points: List[Dict]) -> int:
    """
    Convert engagement data to single 0-100 score.
    
    Mapping:
    - 0.8-1.0 = 100 (Excellent)
    - 0.6-0.8 = 75 (Good)
    - 0.4-0.6 = 50 (Fair)
    - 0.0-0.4 = 25 (Poor)
    """
    if not points:
        return 0
    
    scores = [p.get("score", 0) for p in points if "score" in p]
    if not scores:
        return 0
    
    avg = sum(scores) / len(scores)
    
    if avg >= 0.8:
        return 100
    elif avg >= 0.6:
        return 75
    elif avg >= 0.4:
        return 50
    else:
        return 25


def calculate_focus_time_percentage(points: List[Dict]) -> float:
    """
    Percentage of time with engagement > 0.7 (focused).
    
    Returns: 0-100 percentage
    """
    if not points:
        return 0.0
    
    scores = [p.get("score", 0) for p in points if "score" in p]
    if not scores:
        return 0.0
    
    focused_count = sum(1 for s in scores if s > 0.7)
    return round((focused_count / len(scores)) * 100, 1)


def detect_distraction_spikes(points: List[Dict], threshold: float = 0.3) -> List[Dict]:
    """
    Find sudden drops in engagement (distraction events).
    
    Returns list of spike events with timing and magnitude.
    """
    if len(points) < 2:
        return []
    
    spikes = []
    
    for i in range(1, len(points)):
        current_score = points[i].get("score", 0)
        previous_score = points[i-1].get("score", 0)
        
        drop = previous_score - current_score
        
        # Flag significant drops
        if drop >= threshold:
            severity = "high" if drop >= 0.5 else "medium"
            
            spikes.append({
                "timestamp": points[i].get("timestamp", ""),
                "drop": round(drop, 2),
                "severity": severity,
                "from_score": round(previous_score, 2),
                "to_score": round(current_score, 2),
            })
    
    return spikes


def calculate_volatility(points: List[Dict]) -> float:
    """
    Standard deviation of engagement scores.
    
    High volatility = Inconsistent attention
    Low volatility = Stable attention
    
    Returns: 0-1 float (std deviation)
    """
    if len(points) < 2:
        return 0.0
    
    scores = [p.get("score", 0) for p in points if "score" in p]
    if len(scores) < 2:
        return 0.0
    
    std_dev = statistics.stdev(scores)
    return round(std_dev, 3)


def find_sustained_periods(points: List[Dict], min_duration_sec: int = 60) -> List[Dict]:
    """
    Find periods of sustained high/low engagement.
    
    Returns periods with start time, duration, avg engagement.
    """
    if len(points) < 2:
        return []
    
    periods = []
    current_period = None
    period_scores = []
    
    for i, point in enumerate(points):
        score = point.get("score", 0)
        timestamp = point.get("timestamp", "")
        
        # Classify as high (>0.7) or low (<=0.7)
        is_high = score > 0.7
        
        if current_period is None:
            # Start new period
            current_period = {
                "type": "high" if is_high else "low",
                "start": timestamp,
                "start_index": i,
            }
            period_scores = [score]
        elif (is_high and current_period["type"] == "high") or (not is_high and current_period["type"] == "low"):
            # Continue current period
            period_scores.append(score)
        else:
            # Period changed, save current and start new
            if current_period and period_scores:
                try:
                    start_time = datetime.fromisoformat(current_period["start"])
                    end_time = datetime.fromisoformat(points[i-1].get("timestamp", ""))
                    duration = int((end_time - start_time).total_seconds())
                    
                    if duration >= min_duration_sec:
                        periods.append({
                            "type": current_period["type"],
                            "start": current_period["start"],
                            "duration_sec": duration,
                            "avg_engagement": round(sum(period_scores) / len(period_scores), 2),
                            "points_count": len(period_scores),
                        })
                except Exception as e:
                    print(f"⚠️ Period parsing error: {e}")
            
            # Start new period
            current_period = {
                "type": "high" if is_high else "low",
                "start": timestamp,
                "start_index": i,
            }
            period_scores = [score]
    
    # Don't forget the last period
    if current_period and period_scores:
        try:
            start_time = datetime.fromisoformat(current_period["start"])
            end_time = datetime.fromisoformat(points[-1].get("timestamp", ""))
            duration = int((end_time - start_time).total_seconds())
            
            if duration >= min_duration_sec:
                periods.append({
                    "type": current_period["type"],
                    "start": current_period["start"],
                    "duration_sec": duration,
                    "avg_engagement": round(sum(period_scores) / len(period_scores), 2),
                    "points_count": len(period_scores),
                })
        except Exception as e:
            print(f"⚠️ Last period parsing error: {e}")
    
    return periods


# ========== NEW FUNCTIONS (FOR TIMELINE ANALYSIS) ==========

def calculate_basic_stats(points: List[Dict]) -> Dict[str, float]:
    """Calculate mean, std, min, max of engagement scores."""
    if not points:
        return {
            'avg_score': 0.0,
            'std_score': 0.0,
            'min_score': 0.0,
            'max_score': 0.0,
        }
    
    scores = [p.get('score', 0) for p in points if 'score' in p]
    if not scores:
        return {
            'avg_score': 0.0,
            'std_score': 0.0,
            'min_score': 0.0,
            'max_score': 0.0,
        }
    
    return {
        'avg_score': float(np.mean(scores)),
        'std_score': float(np.std(scores)),
        'min_score': float(np.min(scores)),
        'max_score': float(np.max(scores)),
    }


def detect_dropoffs(points: List[Dict], threshold: float = 0.3) -> List[Dict]:
    """
    Find moments where engagement dropped significantly.
    (Similar to detect_distraction_spikes but more detailed)
    
    Args:
        points: List of {timestamp, score} dicts
        threshold: Minimum drop to be considered (default 0.3)
    
    Returns:
        List of dropoff events
    """
    if len(points) < 2:
        return []
    
    dropoffs = []
    for i in range(1, len(points)):
        prev_score = points[i-1].get('score', 0)
        curr_score = points[i].get('score', 0)
        
        drop = prev_score - curr_score
        if drop > threshold:
            dropoffs.append({
                'timestamp': points[i].get('timestamp', ''),
                'from_score': round(prev_score, 3),
                'to_score': round(curr_score, 3),
                'drop': round(drop, 3)
            })
    
    return sorted(dropoffs, key=lambda x: x['drop'], reverse=True)


def find_peak_periods(points: List[Dict], window: int = 5) -> List[Dict]:
    """
    Find periods of high engagement.
    
    Args:
        points: List of {timestamp, score} dicts
        window: Window size for averaging (default 5 points)
    
    Returns:
        List of peak periods
    """
    if len(points) < window:
        return []
    
    scores = np.array([p.get('score', 0) for p in points if 'score' in p])
    if len(scores) < window:
        return []
    
    peaks = []
    
    for i in range(len(scores) - window):
        window_avg = np.mean(scores[i:i+window])
        if window_avg > 0.75:  # High engagement threshold
            peaks.append({
                'start_idx': i,
                'end_idx': i + window,
                'avg_engagement': round(float(window_avg), 3),
                'start_time': points[i].get('timestamp', ''),
                'end_time': points[i+window-1].get('timestamp', ''),
            })
    
    return sorted(peaks, key=lambda x: x['avg_engagement'], reverse=True)


def calculate_engagement_distribution(points: List[Dict]) -> Dict[str, float]:
    """
    Calculate percentage of time in each engagement level.
    
    Levels:
        - Low: < 0.33
        - Medium: 0.33 - 0.67
        - High: >= 0.67
    """
    if not points:
        return {
            'low_engagement': 0.0,
            'medium_engagement': 0.0,
            'high_engagement': 0.0,
        }
    
    scores = [p.get('score', 0) for p in points if 'score' in p]
    if not scores:
        return {
            'low_engagement': 0.0,
            'medium_engagement': 0.0,
            'high_engagement': 0.0,
        }
    
    total = len(scores)
    
    low = sum(1 for s in scores if s < 0.33) / total
    medium = sum(1 for s in scores if 0.33 <= s < 0.67) / total
    high = sum(1 for s in scores if s >= 0.67) / total
    
    return {
        'low_engagement': round(low, 3),
        'medium_engagement': round(medium, 3),
        'high_engagement': round(high, 3),
    }


def calculate_duration(points: List[Dict]) -> Dict[str, Any]:
    """Calculate session duration from first and last timestamp."""
    if not points:
        return {
            'duration_seconds': 0,
            'duration_minutes': 0,
            'duration_formatted': '0m 0s'
        }
    
    try:
        start = datetime.fromisoformat(points[0].get('timestamp', ''))
        end = datetime.fromisoformat(points[-1].get('timestamp', ''))
        
        duration_sec = int((end - start).total_seconds())
        duration_min = duration_sec // 60
        duration_sec_remainder = duration_sec % 60
        
        return {
            'duration_seconds': duration_sec,
            'duration_minutes': duration_min,
            'duration_formatted': f'{duration_min}m {duration_sec_remainder}s'
        }
    except Exception as e:
        print(f"❌ Duration calculation error: {e}")
        return {
            'duration_seconds': 0,
            'duration_minutes': 0,
            'duration_formatted': '0m 0s'
        }


# ========== MAIN ENTRY POINTS ==========

def get_all_advanced_analytics(points: List[Dict]) -> Dict:
    """
    Calculate all advanced analytics in one call.
    
    Uses EXISTING functions for backward compatibility.
    Returns the format you're already using.
    """
    return {
        "attention_score": calculate_attention_score(points),
        "focus_time_percentage": calculate_focus_time_percentage(points),
        "distraction_spikes": detect_distraction_spikes(points),
        "volatility": calculate_volatility(points),
        "sustained_periods": find_sustained_periods(points),
    }


def get_comprehensive_analytics(points_data: List[Dict]) -> Dict[str, Any]:
    """
    Generate comprehensive analytics summary.
    
    This is a NEW entry point that uses BOTH old and new analytics.
    
    Returns:
        Complete analytics dict with timeline analysis + attention metrics
    """
    # Basic stats (new)
    basic = calculate_basic_stats(points_data)
    
    # Timeline analysis (new)
    dropoffs = detect_dropoffs(points_data)
    peaks = find_peak_periods(points_data)
    distribution = calculate_engagement_distribution(points_data)
    duration = calculate_duration(points_data)
    
    # Attention metrics (existing)
    attention = calculate_attention_score(points_data)
    focus_pct = calculate_focus_time_percentage(points_data)
    volatility = calculate_volatility(points_data)
    sustained = find_sustained_periods(points_data)
    distraction_spikes = detect_distraction_spikes(points_data)
    
    return {
        'summary': {
            **basic,
            'total_points': len(points_data),
            **duration,
            'attention_score': attention,
            'focus_time_percentage': focus_pct,
            'volatility': volatility,
        },
        'distribution': distribution,
        'critical_moments': {
            'dropoffs': dropoffs[:5],  # Top 5 dropoffs
            'peak_periods': peaks[:3],  # Top 3 peaks
            'distraction_spikes': distraction_spikes[:5],  # Top 5 spikes
            'total_dropoffs': len(dropoffs),
            'total_peaks': len(peaks),
            'total_spikes': len(distraction_spikes),
        },
        'sustained_engagement': {
            'sustained_periods': sustained,
            'high_focus_segments': [p for p in sustained if p['type'] == 'high'],
            'low_attention_segments': [p for p in sustained if p['type'] == 'low'],
        },
        'timeline': points_data,
        'computed_at': datetime.utcnow().isoformat()
    }


def generate_summary_report(analytics: Dict[str, Any]) -> str:
    """
    Generate human-readable summary report.
    
    Used for WhatsApp messages and text displays.
    """
    summary = analytics.get('summary', {})
    dist = analytics.get('distribution', {})
    critical = analytics.get('critical_moments', {})
    
    report = f"""
📊 **SESSION ENGAGEMENT REPORT**

✅ **Key Statistics:**
• Average Engagement: {summary.get('avg_score', 0):.1%}
• Attention Score: {summary.get('attention_score', 0)}/100
• Focus Time: {summary.get('focus_time_percentage', 0):.1f}%
• Peak Engagement: {summary.get('max_score', 0):.1%}
• Lowest Engagement: {summary.get('min_score', 0):.1%}
• Volatility: {summary.get('volatility', 0):.3f} (consistency metric)
• Session Duration: {summary.get('duration_formatted', '0m 0s')}

📈 **Engagement Breakdown:**
• High Engagement (>67%): {dist.get('high_engagement', 0):.1%}
• Medium Engagement (33-67%): {dist.get('medium_engagement', 0):.1%}
• Low Engagement (<33%): {dist.get('low_engagement', 0):.1%}

⚠️ **Attention Issues:**
• Total Distraction Spikes: {critical.get('total_spikes', 0)}
• Engagement Dropoffs: {critical.get('total_dropoffs', 0)}

🎯 **Focus Performance:**
• Sustained High Focus Periods: {len(analytics.get('sustained_engagement', {}).get('high_focus_segments', []))}
• Low Attention Segments: {len(analytics.get('sustained_engagement', {}).get('low_attention_segments', []))}

Generated: {analytics.get('computed_at', datetime.utcnow().isoformat())}
"""
    return report.strip()