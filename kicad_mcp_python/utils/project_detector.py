"""
KiCad Project Detection and Management

This module provides utilities for detecting and managing KiCad projects
by scanning project directories rather than requiring individual file paths.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, NamedTuple
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class KiCadProjectFiles:
    """Represents all files in a KiCad project"""
    project_name: str
    project_dir: Path
    
    # Core project files
    project_file: Optional[Path] = None      # .kicad_pro
    schematic_file: Optional[Path] = None    # .kicad_sch  
    pcb_file: Optional[Path] = None          # .kicad_pcb
    project_local: Optional[Path] = None     # .kicad_prl
    
    # Support files
    fp_info_cache: Optional[Path] = None     # fp-info-cache
    backup_dir: Optional[Path] = None        # *-backups/
    
    # Lock files (indicate active editing)
    lock_files: List[Path] = None
    
    def __post_init__(self):
        if self.lock_files is None:
            self.lock_files = []
    
    @property
    def is_valid_project(self) -> bool:
        """Check if this represents a valid KiCad project"""
        return (self.project_file is not None and 
                self.project_file.exists())
    
    @property 
    def has_schematic(self) -> bool:
        """Check if project has schematic file"""
        return (self.schematic_file is not None and 
                self.schematic_file.exists())
    
    @property
    def has_pcb(self) -> bool:
        """Check if project has PCB file"""
        return (self.pcb_file is not None and 
                self.pcb_file.exists())
    
    @property
    def is_being_edited(self) -> bool:
        """Check if project is currently being edited (has lock files)"""
        return len(self.lock_files) > 0
    
    def get_file_by_type(self, file_type: str) -> Optional[Path]:
        """Get project file by type"""
        mapping = {
            'project': self.project_file,
            'schematic': self.schematic_file, 
            'pcb': self.pcb_file,
            'local': self.project_local,
            'cache': self.fp_info_cache
        }
        return mapping.get(file_type.lower())


class KiCadProjectDetector:
    """Detects and manages KiCad projects from directory paths"""
    
    def __init__(self):
        self.project_paths = self._load_project_paths()
        self.detected_projects: Dict[str, KiCadProjectFiles] = {}
        self._scan_all_projects()
    
    def _load_project_paths(self) -> List[Path]:
        """Load project paths from environment variables"""
        paths = []
        
        # Try new PROJECT_PATHS variable first
        project_paths = os.getenv('PROJECT_PATHS')
        if project_paths:
            for path_str in project_paths.split(','):
                path = Path(path_str.strip())
                if path.exists() and path.is_dir():
                    paths.append(path)
        
        # Fallback to PCB_PATHS for backward compatibility
        elif os.getenv('PCB_PATHS'):
            pcb_paths = os.getenv('PCB_PATHS')
            for path_str in pcb_paths.split(','):
                pcb_path = Path(path_str.strip())
                if pcb_path.exists():
                    # Get the parent directory of the PCB file
                    project_dir = pcb_path.parent
                    if project_dir not in paths:
                        paths.append(project_dir)
        
        return paths
    
    def _scan_all_projects(self):
        """Scan all project paths and detect KiCad projects"""
        self.detected_projects.clear()
        
        for project_path in self.project_paths:
            projects = self._scan_directory(project_path)
            for project in projects:
                self.detected_projects[project.project_name] = project
    
    def _scan_directory(self, directory: Path) -> List[KiCadProjectFiles]:
        """Scan a directory for KiCad projects"""
        projects = []
        
        if not directory.exists() or not directory.is_dir():
            return projects
        
        # Look for .kicad_pro files (main project files)
        for pro_file in directory.glob('*.kicad_pro'):
            project = self._analyze_project(pro_file)
            if project.is_valid_project:
                projects.append(project)
        
        return projects
    
    def _analyze_project(self, project_file: Path) -> KiCadProjectFiles:
        """Analyze a project file and detect all related files"""
        project_dir = project_file.parent
        project_name = project_file.stem  # filename without extension
        
        project = KiCadProjectFiles(
            project_name=project_name,
            project_dir=project_dir,
            project_file=project_file
        )
        
        # Look for related files with same base name
        base_path = project_dir / project_name
        
        # Core files
        sch_file = base_path.with_suffix('.kicad_sch')
        if sch_file.exists():
            project.schematic_file = sch_file
            
        pcb_file = base_path.with_suffix('.kicad_pcb')
        if pcb_file.exists():
            project.pcb_file = pcb_file
            
        prl_file = base_path.with_suffix('.kicad_prl')
        if prl_file.exists():
            project.project_local = prl_file
        
        # Support files
        fp_cache = project_dir / 'fp-info-cache'
        if fp_cache.exists():
            project.fp_info_cache = fp_cache
            
        backup_dir = project_dir / f'{project_name}-backups'
        if backup_dir.exists() and backup_dir.is_dir():
            project.backup_dir = backup_dir
        
        # Lock files
        for lock_file in project_dir.glob(f'~{project_name}.*.lck'):
            project.lock_files.append(lock_file)
        
        return project
    
    def get_project(self, project_name: str) -> Optional[KiCadProjectFiles]:
        """Get project by name"""
        return self.detected_projects.get(project_name)
    
    def get_all_projects(self) -> Dict[str, KiCadProjectFiles]:
        """Get all detected projects"""
        return self.detected_projects.copy()
    
    def get_project_names(self) -> List[str]:
        """Get list of all project names"""
        return list(self.detected_projects.keys())
    
    def get_projects_with_pcb(self) -> Dict[str, KiCadProjectFiles]:
        """Get all projects that have PCB files"""
        return {name: project for name, project in self.detected_projects.items() 
                if project.has_pcb}
    
    def get_projects_with_schematic(self) -> Dict[str, KiCadProjectFiles]:
        """Get all projects that have schematic files"""
        return {name: project for name, project in self.detected_projects.items() 
                if project.has_schematic}
    
    def find_pcb_path(self, board_name: str) -> Optional[Path]:
        """Find PCB file path by board name (for backward compatibility)"""
        # Try exact project name match first
        project = self.get_project(board_name.replace('.kicad_pcb', ''))
        if project and project.has_pcb:
            return project.pcb_file
        
        # Try filename matching
        for project in self.detected_projects.values():
            if project.pcb_file and project.pcb_file.name == board_name:
                return project.pcb_file
        
        return None
    
    def refresh_projects(self):
        """Refresh project detection (rescan directories)"""
        self._scan_all_projects()
    
    def get_project_summary(self) -> Dict:
        """Get summary of all detected projects"""
        summary = {
            'total_projects': len(self.detected_projects),
            'projects_with_pcb': len(self.get_projects_with_pcb()),
            'projects_with_schematic': len(self.get_projects_with_schematic()),
            'active_projects': len([p for p in self.detected_projects.values() 
                                  if p.is_being_edited]),
            'project_details': {}
        }
        
        for name, project in self.detected_projects.items():
            summary['project_details'][name] = {
                'has_pcb': project.has_pcb,
                'has_schematic': project.has_schematic,
                'is_being_edited': project.is_being_edited,
                'project_dir': str(project.project_dir)
            }
        
        return summary


# Global instance for easy access
_detector_instance = None

def get_project_detector() -> KiCadProjectDetector:
    """Get singleton project detector instance"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = KiCadProjectDetector()
    return _detector_instance