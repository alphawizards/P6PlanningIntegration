#!/usr/bin/env python3
"""
Context Generators
Generates AI-consumable summaries and reports from P6 data.
"""

from typing import Optional
import pandas as pd
from datetime import datetime

from src.utils import logger


class ContextGenerator:
    """
    Generate AI-consumable context from P6 data.
    
    Produces:
    - Markdown summaries for LLM consumption
    - Filtered DataFrames for critical path analysis
    - Token-budget-aware exports
    """
    
    def __init__(self, max_activities_for_ai: int = 100):
        """
        Initialize ContextGenerator.
        
        VERIFICATION POINT 3: Context Limits
        Sets default maximum activities to prevent token budget overflow.
        
        Args:
            max_activities_for_ai: Maximum activities to include in AI context (default: 100)
        """
        self.max_activities_for_ai = max_activities_for_ai
        logger.info(f"ContextGenerator initialized (max_activities: {max_activities_for_ai})")
    
    def generate_project_summary(
        self,
        project_df: pd.DataFrame,
        activity_df: Optional[pd.DataFrame] = None
    ) -> str:
        """
        Generate Markdown summary of project for AI consumption.
        
        Args:
            project_df: DataFrame with project data (single row expected)
            activity_df: Optional DataFrame with activity data for statistics
            
        Returns:
            str: Markdown-formatted project summary
        """
        try:
            logger.info("Generating project summary for AI context")
            
            if project_df.empty:
                return "# Project Summary\n\nNo project data available."
            
            # Get project details (first row if multiple)
            project = project_df.iloc[0]
            
            # Build Markdown summary
            summary = []
            summary.append("# Project Summary")
            summary.append("")
            summary.append(f"**Project ID:** {project.get('Id', 'N/A')}")
            summary.append(f"**Project Name:** {project.get('Name', 'N/A')}")
            summary.append(f"**Status:** {project.get('Status', 'N/A')}")
            
            # Add dates if available
            if 'PlanStartDate' in project and pd.notna(project['PlanStartDate']):
                start_date = project['PlanStartDate']
                if isinstance(start_date, datetime):
                    summary.append(f"**Planned Start:** {start_date.strftime('%Y-%m-%d')}")
                else:
                    summary.append(f"**Planned Start:** {start_date}")
            
            if 'PlanFinishDate' in project and pd.notna(project['PlanFinishDate']):
                finish_date = project['PlanFinishDate']
                if isinstance(finish_date, datetime):
                    summary.append(f"**Planned Finish:** {finish_date.strftime('%Y-%m-%d')}")
                else:
                    summary.append(f"**Planned Finish:** {finish_date}")
            
            # Add activity statistics if provided
            if activity_df is not None and not activity_df.empty:
                summary.append("")
                summary.append("## Activity Statistics")
                summary.append(f"- **Total Activities:** {len(activity_df)}")
                
                if 'Status' in activity_df.columns:
                    status_counts = activity_df['Status'].value_counts()
                    summary.append("- **By Status:**")
                    for status, count in status_counts.items():
                        summary.append(f"  - {status}: {count}")
                
                if 'PlannedDuration' in activity_df.columns:
                    total_duration = activity_df['PlannedDuration'].sum()
                    summary.append(f"- **Total Planned Duration:** {total_duration} hours")
            
            summary.append("")
            result = "\n".join(summary)
            
            logger.info("✓ Generated project summary")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate project summary: {e}")
            return f"# Project Summary\n\nError generating summary: {e}"
    
    def generate_critical_path_report(
        self,
        activity_df: pd.DataFrame,
        float_threshold: float = 0.0
    ) -> pd.DataFrame:
        """
        Generate critical path report for AI analysis.
        
        VERIFICATION POINT 3: Context Limits
        Filters and limits activities to prevent token budget overflow.
        
        Args:
            activity_df: DataFrame with activity data
            float_threshold: Total float threshold for critical path (default: 0.0)
            
        Returns:
            pd.DataFrame: Simplified DataFrame with critical path activities
        """
        try:
            logger.info("Generating critical path report for AI context")
            
            if activity_df.empty:
                logger.warning("No activities provided for critical path report")
                return pd.DataFrame()
            
            # Filter for critical path activities
            # Note: TotalFloat may not be in ACTIVITY_FIELDS from Phase 1.5
            # This is a placeholder for when it's added
            if 'TotalFloat' in activity_df.columns:
                critical_activities = activity_df[
                    activity_df['TotalFloat'] <= float_threshold
                ].copy()
                logger.info(f"Found {len(critical_activities)} critical path activities")
            else:
                logger.warning("TotalFloat field not available, using all activities")
                critical_activities = activity_df.copy()
            
            # VERIFICATION POINT 3: Context Limits
            # Limit to max_activities_for_ai to prevent token overflow
            if len(critical_activities) > self.max_activities_for_ai:
                logger.warning(
                    f"Limiting critical path report from {len(critical_activities)} "
                    f"to {self.max_activities_for_ai} activities for AI context"
                )
                # Sort by finish date (most urgent first) and take top N
                if 'FinishDate' in critical_activities.columns:
                    critical_activities = critical_activities.sort_values('FinishDate')
                critical_activities = critical_activities.head(self.max_activities_for_ai)
            
            # Select relevant columns for AI analysis
            columns_to_keep = []
            for col in ['Id', 'Name', 'Status', 'StartDate', 'FinishDate', 'PlannedDuration']:
                if col in critical_activities.columns:
                    columns_to_keep.append(col)
            
            if 'TotalFloat' in critical_activities.columns:
                columns_to_keep.append('TotalFloat')
            
            simplified = critical_activities[columns_to_keep].copy()
            
            logger.info(f"✓ Generated critical path report with {len(simplified)} activities")
            return simplified
            
        except Exception as e:
            logger.error(f"Failed to generate critical path report: {e}")
            return pd.DataFrame()
    
    def generate_activity_summary_markdown(
        self,
        activity_df: pd.DataFrame,
        max_activities: Optional[int] = None
    ) -> str:
        """
        Generate Markdown summary of activities for AI consumption.
        
        VERIFICATION POINT 3: Context Limits
        Limits activities to prevent token overflow.
        
        Args:
            activity_df: DataFrame with activity data
            max_activities: Optional override for max activities (uses instance default if None)
            
        Returns:
            str: Markdown-formatted activity summary
        """
        try:
            logger.info("Generating activity summary for AI context")
            
            if activity_df.empty:
                return "# Activity Summary\n\nNo activities available."
            
            # VERIFICATION POINT 3: Context Limits
            max_rows = max_activities or self.max_activities_for_ai
            
            if len(activity_df) > max_rows:
                logger.warning(f"Limiting activity summary from {len(activity_df)} to {max_rows} rows")
                activity_df = activity_df.head(max_rows)
            
            # Build Markdown summary
            summary = []
            summary.append("# Activity Summary")
            summary.append("")
            summary.append(f"**Total Activities:** {len(activity_df)}")
            summary.append("")
            
            # Status breakdown
            if 'Status' in activity_df.columns:
                summary.append("## Status Breakdown")
                status_counts = activity_df['Status'].value_counts()
                for status, count in status_counts.items():
                    summary.append(f"- **{status}:** {count}")
                summary.append("")
            
            # Activity list
            summary.append("## Activities")
            summary.append("")
            
            for idx, row in activity_df.iterrows():
                activity_id = row.get('Id', 'N/A')
                activity_name = row.get('Name', 'N/A')
                status = row.get('Status', 'N/A')
                
                summary.append(f"### {activity_id}: {activity_name}")
                summary.append(f"- **Status:** {status}")
                
                if 'StartDate' in row and pd.notna(row['StartDate']):
                    start = row['StartDate']
                    if isinstance(start, datetime):
                        summary.append(f"- **Start:** {start.strftime('%Y-%m-%d')}")
                
                if 'FinishDate' in row and pd.notna(row['FinishDate']):
                    finish = row['FinishDate']
                    if isinstance(finish, datetime):
                        summary.append(f"- **Finish:** {finish.strftime('%Y-%m-%d')}")
                
                if 'PlannedDuration' in row and pd.notna(row['PlannedDuration']):
                    summary.append(f"- **Duration:** {row['PlannedDuration']} hours")
                
                summary.append("")
            
            result = "\n".join(summary)
            
            logger.info("✓ Generated activity summary")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate activity summary: {e}")
            return f"# Activity Summary\n\nError generating summary: {e}"
    
    def generate_combined_context(
        self,
        project_df: pd.DataFrame,
        activity_df: pd.DataFrame,
        include_critical_path: bool = True
    ) -> str:
        """
        Generate combined context for AI analysis.
        
        Combines project summary, activity statistics, and critical path.
        
        Args:
            project_df: DataFrame with project data
            activity_df: DataFrame with activity data
            include_critical_path: Whether to include critical path analysis
            
        Returns:
            str: Markdown-formatted combined context
        """
        try:
            logger.info("Generating combined AI context")
            
            sections = []
            
            # Project summary
            project_summary = self.generate_project_summary(project_df, activity_df)
            sections.append(project_summary)
            
            # Critical path report (if requested and TotalFloat available)
            if include_critical_path and 'TotalFloat' in activity_df.columns:
                critical_df = self.generate_critical_path_report(activity_df)
                if not critical_df.empty:
                    sections.append("\n---\n")
                    sections.append("## Critical Path Activities")
                    sections.append("")
                    sections.append(critical_df.to_markdown(index=False))
            
            result = "\n".join(sections)
            
            logger.info("✓ Generated combined AI context")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate combined context: {e}")
            return f"# Combined Context\n\nError generating context: {e}"
