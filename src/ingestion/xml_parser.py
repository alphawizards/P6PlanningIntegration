#!/usr/bin/env python3
"""
XML Parser
Unified parser for P6 XML and MS Project XML files.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime

from src.ingestion.base import ScheduleParser
from src.utils import logger


class UnifiedXMLParser(ScheduleParser):
    """
    Unified parser for XML schedule files.
    
    Supports:
    - Primavera P6 XML (Oracle schema)
    - Microsoft Project XML (MSP schema)
    
    VERIFICATION POINT 3: XML Types
    Distinguishes between P6 and MS Project XML formats.
    """
    
    def __init__(self, filepath: str, encoding: Optional[str] = None):
        """
        Initialize XML parser.
        
        Args:
            filepath: Path to XML file
            encoding: File encoding (default: auto-detect)
        """
        super().__init__(filepath, encoding)
        self.xml_type = None  # Will be detected during parsing
    
    def parse(self) -> Dict[str, pd.DataFrame]:
        """
        Parse XML file into standardized DataFrames.
        
        VERIFICATION POINT 3: XML Types
        Detects format and routes to appropriate parser.
        
        Returns:
            Dict with 'projects' and 'activities' DataFrames
        """
        try:
            logger.info(f"Parsing XML file: {self.filepath}")
            
            # Read and parse XML
            content = self._read_file_with_encoding()
            root = ET.fromstring(content)
            
            # VERIFICATION POINT 3: Detect XML type
            self.xml_type = self._detect_xml_type(root)
            logger.info(f"Detected XML type: {self.xml_type}")
            
            # Route to appropriate parser
            if self.xml_type == 'P6':
                result = self._parse_p6_xml(root)
            elif self.xml_type == 'MSP':
                result = self._parse_msp_xml(root)
            else:
                raise ValueError(f"Unknown XML type: {self.xml_type}")
            
            self.validate_result(result)
            
            logger.info(f"✓ XML parsing complete: {len(result['projects'])} projects, {len(result['activities'])} activities")
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse XML file: {e}")
            raise RuntimeError(f"XML parsing failed: {e}") from e
    
    def _detect_xml_type(self, root: ET.Element) -> str:
        """
        Detect XML format type.
        
        VERIFICATION POINT 3: XML Types
        Checks root tag and namespaces to identify format.
        
        Args:
            root: XML root element
            
        Returns:
            str: 'P6' or 'MSP'
        """
        # Check root tag
        root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        
        # P6 XML indicators
        if root_tag in ['APIBusinessObjects', 'P6Project', 'ProjectData']:
            return 'P6'
        
        # MS Project XML indicators
        if root_tag == 'Project':
            # Check for MS Project namespace
            if 'microsoft' in root.tag.lower() or any('microsoft' in str(ns).lower() for ns in root.attrib.values()):
                return 'MSP'
            # Check for typical MS Project elements
            if root.find('.//Task') is not None or root.find('.//Tasks') is not None:
                return 'MSP'
        
        # Default to P6 if unclear
        logger.warning(f"Could not definitively detect XML type from root tag: {root_tag}, defaulting to P6")
        return 'P6'
    
    def _parse_p6_xml(self, root: ET.Element) -> Dict[str, pd.DataFrame]:
        """
        Parse Primavera P6 XML.
        
        VERIFICATION POINT 1: Schema Alignment
        Maps P6 XML elements to standard schema.
        
        Args:
            root: XML root element
            
        Returns:
            Dict with 'projects' and 'activities' DataFrames
        """
        # Find project elements
        projects_data = []
        activities_data = []
        relationships_data = []
        
        # P6 XML can have different structures
        # Try common paths
        project_elements = (
            root.findall('.//Project') or
            root.findall('.//P6Project') or
            root.findall('.//APIBusinessObjects/Project')
        )
        
        for project_elem in project_elements:
            # Extract project data
            project_data = {
                'ObjectId': self._get_text(project_elem, 'ObjectId'),
                'Id': self._get_text(project_elem, 'Id') or self._get_text(project_elem, 'ProjectId'),
                'Name': self._get_text(project_elem, 'Name') or self._get_text(project_elem, 'ProjectName'),
                'Status': self._get_text(project_elem, 'Status'),
                'PlanStartDate': self._parse_date(self._get_text(project_elem, 'PlannedStartDate')),
            }
            projects_data.append(project_data)
            
            # Find activities within this project
            activity_elements = (
                project_elem.findall('.//Activity') or
                project_elem.findall('.//WBS/Activity') or
                []
            )
            
            for activity_elem in activity_elements:
                activity_data = {
                    'ObjectId': self._get_text(activity_elem, 'ObjectId'),
                    'Id': self._get_text(activity_elem, 'Id') or self._get_text(activity_elem, 'ActivityId'),
                    'Name': self._get_text(activity_elem, 'Name') or self._get_text(activity_elem, 'ActivityName'),
                    'Status': self._get_text(activity_elem, 'Status'),
                    'PlannedDuration': self._parse_duration(self._get_text(activity_elem, 'PlannedDuration')),
                    'StartDate': self._parse_date(self._get_text(activity_elem, 'StartDate') or self._get_text(activity_elem, 'PlannedStartDate')),
                    'FinishDate': self._parse_date(self._get_text(activity_elem, 'FinishDate') or self._get_text(activity_elem, 'PlannedFinishDate')),
                }
                activities_data.append(activity_data)
        
        # Find relationship elements
        relationship_elements = (
            root.findall('.//Relationship') or
            root.findall('.//ActivityRelationship') or
            []
        )
        
        for rel_elem in relationship_elements:
            relationship_data = {
                'ObjectId': self._get_text(rel_elem, 'ObjectId'),
                'PredecessorObjectId': self._get_text(rel_elem, 'PredecessorActivityObjectId') or self._get_text(rel_elem, 'PredecessorId'),
                'SuccessorObjectId': self._get_text(rel_elem, 'SuccessorActivityObjectId') or self._get_text(rel_elem, 'SuccessorId'),
                'Type': self._get_text(rel_elem, 'Type') or self._get_text(rel_elem, 'RelationshipType'),
                'Lag': self._parse_duration(self._get_text(rel_elem, 'Lag')),
            }
            relationships_data.append(relationship_data)
        
        # Create DataFrames
        projects_df = pd.DataFrame(projects_data) if projects_data else pd.DataFrame(columns=['ObjectId', 'Id', 'Name', 'Status', 'PlanStartDate'])
        activities_df = pd.DataFrame(activities_data) if activities_data else pd.DataFrame(columns=['ObjectId', 'Id', 'Name', 'Status', 'PlannedDuration', 'StartDate', 'FinishDate'])
        relationships_df = pd.DataFrame(relationships_data) if relationships_data else pd.DataFrame(columns=['ObjectId', 'PredecessorObjectId', 'SuccessorObjectId', 'Type', 'Lag'])
        
        logger.info(f"Parsed P6 XML: {len(projects_df)} projects, {len(activities_df)} activities, {len(relationships_df)} relationships")
        
        return {
            'projects': projects_df,
            'activities': activities_df,
            'relationships': relationships_df
        }
    
    def _parse_msp_xml(self, root: ET.Element) -> Dict[str, pd.DataFrame]:
        """
        Parse Microsoft Project XML.
        
        VERIFICATION POINT 1: Schema Alignment
        Maps MS Project XML elements to standard schema.
        
        Args:
            root: XML root element
            
        Returns:
            Dict with 'projects' and 'activities' DataFrames
        """
        # Extract project data
        project_data = {
            'ObjectId': 1,  # MSP XML typically has one project
            'Id': self._get_text(root, 'UID') or '1',
            'Name': self._get_text(root, 'Name') or self._get_text(root, 'Title'),
            'Status': 'Active',  # MSP doesn't have explicit status
            'PlanStartDate': self._parse_date(self._get_text(root, 'StartDate')),
        }
        
        projects_df = pd.DataFrame([project_data])
        
        # Extract tasks (activities)
        activities_data = []
        
        # Find all Task elements
        task_elements = root.findall('.//Task')
        
        for task_elem in task_elements:
            # Skip summary tasks (UID 0 is project summary)
            uid = self._get_text(task_elem, 'UID')
            if uid == '0':
                continue
            
            # Extract task data
            activity_data = {
                'ObjectId': uid,
                'Id': self._get_text(task_elem, 'WBS') or uid,
                'Name': self._get_text(task_elem, 'Name'),
                'Status': self._map_msp_status(
                    self._get_text(task_elem, 'PercentComplete'),
                    self._get_text(task_elem, 'ActualStart')
                ),
                'PlannedDuration': self._parse_msp_duration(self._get_text(task_elem, 'Duration')),
                'StartDate': self._parse_date(self._get_text(task_elem, 'Start')),
                'FinishDate': self._parse_date(self._get_text(task_elem, 'Finish')),
            }
            activities_data.append(activity_data)
        
        activities_df = pd.DataFrame(activities_data) if activities_data else pd.DataFrame(columns=['ObjectId', 'Id', 'Name', 'Status', 'PlannedDuration', 'StartDate', 'FinishDate'])
        
        # Parse relationships (PredecessorLink)
        relationships_data = []
        predecessor_links = root.findall('.//PredecessorLink') or []
        
        for link_elem in predecessor_links:
            relationship_data = {
                'ObjectId': None,  # MS Project doesn't have relationship IDs
                'PredecessorObjectId': self._get_text(link_elem, 'PredecessorUID'),
                'SuccessorObjectId': self._get_text(link_elem, 'SuccessorUID') or self._get_text(link_elem, '../UID'),
                'Type': self._map_msp_link_type(self._get_text(link_elem, 'Type')),
                'Lag': self._parse_msp_duration(self._get_text(link_elem, 'LinkLag')),
            }
            relationships_data.append(relationship_data)
        
        relationships_df = pd.DataFrame(relationships_data) if relationships_data else pd.DataFrame(columns=['ObjectId', 'PredecessorObjectId', 'SuccessorObjectId', 'Type', 'Lag'])
        
        logger.info(f"Parsed MS Project XML: {len(projects_df)} projects, {len(activities_df)} activities, {len(relationships_df)} relationships")
        
        return {
            'projects': projects_df,
            'activities': activities_df,
            'relationships': relationships_df
        }
    
    def _get_text(self, element: ET.Element, tag: str) -> Optional[str]:
        """
        Get text content of child element.
        
        Args:
            element: Parent element
            tag: Child tag name
            
        Returns:
            str or None: Text content
        """
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse date string to datetime.
        
        Args:
            date_str: Date string
            
        Returns:
            datetime or None
        """
        if not date_str:
            return None
        
        try:
            # Try ISO format first
            return pd.to_datetime(date_str)
        except Exception:
            return None
    
    def _parse_duration(self, duration_str: Optional[str]) -> Optional[float]:
        """
        Parse P6 duration string to hours.
        
        Args:
            duration_str: Duration string (e.g., "8h", "1d")
            
        Returns:
            float or None: Duration in hours
        """
        if not duration_str:
            return None
        
        try:
            # Simple numeric conversion
            return float(duration_str)
        except ValueError:
            # Try to extract numeric part
            import re
            match = re.search(r'(\d+\.?\d*)', duration_str)
            if match:
                return float(match.group(1))
            return None
    
    def _parse_msp_duration(self, duration_str: Optional[str]) -> Optional[float]:
        """
        Parse MS Project duration to hours.
        
        MS Project stores duration in format: PT8H0M0S (8 hours)
        
        Args:
            duration_str: Duration string
            
        Returns:
            float or None: Duration in hours
        """
        if not duration_str:
            return None
        
        try:
            # MS Project ISO 8601 duration format: PT8H0M0S
            if duration_str.startswith('PT'):
                import re
                hours = 0
                
                # Extract hours
                h_match = re.search(r'(\d+)H', duration_str)
                if h_match:
                    hours += int(h_match.group(1))
                
                # Extract minutes (convert to hours)
                m_match = re.search(r'(\d+)M', duration_str)
                if m_match:
                    hours += int(m_match.group(1)) / 60
                
                return hours if hours > 0 else None
            
            # Try simple numeric
            return float(duration_str)
        except Exception:
            return None
    
    def _map_msp_status(self, percent_complete: Optional[str], actual_start: Optional[str]) -> str:
        """
        Map MS Project task state to standard status.
        
        Args:
            percent_complete: Percent complete (0-100)
            actual_start: Actual start date
            
        Returns:
            str: Status ('Not Started', 'In Progress', 'Completed')
        """
        try:
            if percent_complete:
                pct = int(percent_complete)
                if pct == 0:
                    return 'Not Started'
                elif pct == 100:
                    return 'Completed'
                else:
                    return 'In Progress'
            
            # If no percent, check if started
            if actual_start:
                return 'In Progress'
            
            return 'Not Started'
        except Exception:
            return 'Not Started'

    def _map_msp_link_type(self, link_type: Optional[str]) -> str:
        """
        Map MS Project link type to standard relationship type.
        
        MS Project link types:
        - 0 or FF: Finish-to-Finish
        - 1 or FS: Finish-to-Start (default)
        - 2 or SF: Start-to-Finish
        - 3 or SS: Start-to-Start
        
        Args:
            link_type: MS Project link type code or string
            
        Returns:
            str: Standard type ('FS', 'SS', 'FF', 'SF')
        """
        if not link_type:
            return 'FS'  # Default
        
        type_map = {
            '0': 'FF',
            '1': 'FS',
            '2': 'SF',
            '3': 'SS',
            'FF': 'FF',
            'FS': 'FS',
            'SF': 'SF',
            'SS': 'SS',
        }
        
        return type_map.get(str(link_type).strip(), 'FS')
