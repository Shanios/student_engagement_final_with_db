"""
Report generation module - creates PNG graphs and exports for WhatsApp
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import io
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import numpy as np


def generate_engagement_graph(points_data: List[Dict]) -> Optional[str]:
    """
    Generate engagement vs time graph (PNG -> base64).
    
    Args:
        points_data: List of {timestamp, score} dicts
    
    Returns:
        Base64 encoded PNG image string, or None if failed
    """
    
    if not points_data:
        return None
    
    try:
        # Parse timestamps
        times = [datetime.fromisoformat(p['timestamp']) for p in points_data]
        scores = [p['score'] for p in points_data]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
        
        # Plot main line
        ax.plot(times, scores, linewidth=2.5, color='#3b82f6', marker='o', 
                markersize=4, label='Engagement Score', alpha=0.8)
        
        # Add average line
        avg = np.mean(scores)
        ax.axhline(y=avg, color='#ef4444', linestyle='--', linewidth=2, 
                   label=f'Average: {avg:.2f}', alpha=0.7)
        
        # Add threshold zones
        ax.axhspan(0.67, 1.0, alpha=0.1, color='green', label='High (>67%)')
        ax.axhspan(0.33, 0.67, alpha=0.1, color='yellow', label='Medium (33-67%)')
        ax.axhspan(0.0, 0.33, alpha=0.1, color='red', label='Low (<33%)')
        
        # Formatting
        ax.set_xlabel('Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('Engagement Score', fontsize=12, fontweight='bold')
        ax.set_title('📊 Student Engagement Over Time', fontsize=14, fontweight='bold')
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper right', fontsize=9)
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Convert to PNG (base64)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode()
        plt.close(fig)
        
        return img_base64
        
    except Exception as e:
        print(f"❌ Graph generation error: {e}")
        return None


def generate_engagement_distribution_chart(analytics: Dict[str, Any]) -> Optional[str]:
    """
    Generate pie chart of engagement distribution.
    
    Args:
        analytics: Analytics dict with 'distribution' key
    
    Returns:
        Base64 encoded PNG image string
    """
    
    try:
        dist = analytics.get('distribution', {})
        
        labels = ['High\n(>67%)', 'Medium\n(33-67%)', 'Low\n(<33%)']
        sizes = [
            dist.get('high_engagement', 0) * 100,
            dist.get('medium_engagement', 0) * 100,
            dist.get('low_engagement', 0) * 100
        ]
        colors = ['#10b981', '#f59e0b', '#ef4444']
        
        # Filter out zero values
        labels = [l for l, s in zip(labels, sizes) if s > 0]
        sizes = [s for s in sizes if s > 0]
        colors = colors[:len(sizes)]
        
        if not sizes:
            return None
        
        fig, ax = plt.subplots(figsize=(8, 6), facecolor='white')
        
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 11, 'fontweight': 'bold'}
        )
        
        ax.set_title('📈 Engagement Distribution', fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # Convert to PNG
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode()
        plt.close(fig)
        
        return img_base64
        
    except Exception as e:
        print(f"❌ Distribution chart error: {e}")
        return None


def generate_summary_text(analytics: Dict[str, Any]) -> str:
    """
    Generate text summary for WhatsApp message.
    Uses both old attention metrics and new timeline analysis.
    
    Args:
        analytics: Full analytics dictionary from get_comprehensive_analytics()
    
    Returns:
        Formatted text string ready for WhatsApp
    """
    summary = analytics.get('summary', {})
    dist = analytics.get('distribution', {})
    critical = analytics.get('critical_moments', {})
    sustained = analytics.get('sustained_engagement', {})
    
    text = f"""
📊 **SESSION ENGAGEMENT REPORT**

✅ **Performance Metrics:**
• Attention Score: {summary.get('attention_score', 0)}/100
• Average Engagement: {summary.get('avg_score', 0):.1%}
• Focus Time: {summary.get('focus_time_percentage', 0):.1f}%
• Volatility: {summary.get('volatility', 0):.3f} (lower = more stable)

📈 **Session Details:**
• Peak Engagement: {summary.get('max_score', 0):.1%}
• Lowest Engagement: {summary.get('min_score', 0):.1%}
• Total Data Points: {summary.get('total_points', 0)}
• Session Duration: {summary.get('duration_formatted', '0m 0s')}

📊 **Time Distribution:**
• High Engagement (>67%): {dist.get('high_engagement', 0):.1%}
• Medium Engagement (33-67%): {dist.get('medium_engagement', 0):.1%}
• Low Engagement (<33%): {dist.get('low_engagement', 0):.1%}

⚠️ **Attention Issues:**
• Distraction Spikes: {critical.get('total_spikes', 0)}
• Engagement Dropoffs: {critical.get('total_dropoffs', 0)}

🎯 **Focus Patterns:**
• High Focus Periods: {len(sustained.get('high_focus_segments', []))}
• Low Attention Periods: {len(sustained.get('low_attention_segments', []))}

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
    return text.strip()


def generate_dropoff_details(analytics: Dict[str, Any]) -> str:
    """
    Generate detailed dropoff information.
    
    Args:
        analytics: Full analytics dictionary
    
    Returns:
        Formatted text with dropoff details
    """
    dropoffs = analytics.get('critical_moments', {}).get('dropoffs', [])
    
    if not dropoffs:
        return "✅ No significant engagement dropoffs detected."
    
    text = "⚠️ **Engagement Dropoffs:**\n\n"
    
    for i, dropoff in enumerate(dropoffs[:5], 1):
        timestamp = dropoff.get('timestamp', 'Unknown')
        from_score = dropoff.get('from_score', 0)
        to_score = dropoff.get('to_score', 0)
        drop = dropoff.get('drop', 0)
        
        text += f"{i}. Time: {timestamp}\n"
        text += f"   Drop: {from_score:.1%} → {to_score:.1%} (↓{drop:.1%})\n\n"
    
    return text


def create_report_package(analytics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create complete report package with graphs and text.
    
    This is the main entry point for report generation.
    
    Args:
        analytics: Full analytics dictionary
    
    Returns:
        Dict with all report components
    """
    
    points_data = analytics.get('timeline', [])
    
    return {
        'summary_text': generate_summary_text(analytics),
        'dropoff_details': generate_dropoff_details(analytics),
        'engagement_graph': generate_engagement_graph(points_data),
        'distribution_chart': generate_engagement_distribution_chart(analytics),
        'generated_at': datetime.utcnow().isoformat(),
        'analytics': analytics
    }


def export_to_whatsapp_format(report_package: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format report for WhatsApp delivery.
    
    Args:
        report_package: Report package from create_report_package
    
    Returns:
        WhatsApp-ready format with message and media attachments
    """
    
    return {
        'message': report_package['summary_text'],
        'attachments': {
            'engagement_graph': report_package['engagement_graph'],
            'distribution_chart': report_package['distribution_chart'],
        },
        'details': report_package['dropoff_details'],
        'generated_at': report_package['generated_at']
    }