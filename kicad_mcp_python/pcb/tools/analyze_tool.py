from dotenv import load_dotenv


from ...utils.convert_proto import (
    BOARDITEM_TYPE_CONFIGS, 
    get_object_type
)

from ..pcbmodule import PCBTool
from ...core.mcp_manager import ToolManager

from ...utils.kicad_cli import KiCadPCBConverter
from ...utils.project_detector import get_project_detector

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent

load_dotenv()


class BoardAnalyzer(ToolManager, PCBTool):
    '''
    A class that gathers tools for analyzing the board and retrieving information, used in manipulate_tool. 
    '''

    def __init__(self, mcp: FastMCP):
        super().__init__(mcp)
        self.pcb_converter = KiCadPCBConverter()
        self.add_tool(self.get_board_status)        
        self.add_tool(self.get_items_by_type)        
        self.add_tool(self.get_item_type_args_hint)
        self.add_tool(self.get_project_summary)        
        
            
    def get_board_status(self):
        '''
        Retrieves the comprehensive status of the current PCB board including all components and visual representation.
        
        This method collects information about all board items (footprints, tracks, vias, pads, etc.) 
        and generates a visual representation of the current board state. The board is automatically 
        saved before generating the screenshot to ensure all changes are visible.
        
        Returns:
            list: A two-element list containing:
                - dict: Dictionary with board item types as keys and lists of items as values.
                    Failed item types will have error messages instead of item lists.
                - ImageContent: JPEG image representation of the current board layout
                            generated via SVG conversion.
        
        Raises:
            Exception: May raise exceptions during board item retrieval or image conversion,
                    which are caught and reported in the result dictionary.
        
        '''
        result = {}
        for item_type in BOARDITEM_TYPE_CONFIGS.keys():
            try:
                result[item_type] = [item for item in self.board.get_items(get_object_type(item_type))]
            except Exception as e:
                result[item_type] = f'Not yet implemented, {str(e)}'
        
        # Auto-save the board before generating screenshot to ensure changes are visible
        try:
            self.board.save()
        except Exception as e:
            # Log the error but don't fail the entire operation
            print(f"Warning: Auto-save failed: {str(e)}")
                
        base64_image = self.pcb_converter.pcb_to_jpg_via_svg(
            boardname=self.board.name,
            )
        
        return [result, ImageContent(
            type="image",
            data=base64_image,
            mimeType="image/jpeg"
        )]
    
    
    def get_items_by_type(self, item_type: str):
        '''
        Retrieves the list of items of the specified type from the board.
        The item_type should be one of the keys in BOARDITEM_TYPE_CONFIGS.
        
        Args:
            item_type (str): The item type (e.g., 'Footprint', 'Via', 'Track')
        Returns:
            dict: A dictionary containing the list of items of the specified type.
        '''
        
        result = {
            item.id.value:item for item in self.board.get_items(
            get_object_type(item_type)
            )}
        return result
    
    
    def get_item_type_args_hint(self, item_type: str):
        '''
        Retrieves the configuration arguments for a specific board item type.
        
        Args:
            item_type (str): The item type (e.g., 'Footprint', 'Via', 'Track')
        Returns:
            dict: A dictionary containing the configuration arguments for the specified item type.    
        '''
        
        result = BOARDITEM_TYPE_CONFIGS[item_type]
        return result
    
    def get_project_summary(self):
        '''
        Retrieves a comprehensive summary of all detected KiCad projects.
        
        This method scans configured project directories and provides information about
        all detected KiCad projects, including which files are available and their status.
        
        Returns:
            dict: Summary containing:
                - total_projects: Number of detected projects
                - projects_with_pcb: Count of projects with PCB files
                - projects_with_schematic: Count of projects with schematic files  
                - active_projects: Count of projects currently being edited
                - project_details: Dictionary with detailed info for each project
        '''
        try:
            detector = get_project_detector()
            # Refresh to get latest project state
            detector.refresh_projects()
            return detector.get_project_summary()
        except Exception as e:
            return {
                'error': f'Failed to get project summary: {str(e)}',
                'total_projects': 0,
                'projects_with_pcb': 0,
                'projects_with_schematic': 0,
                'active_projects': 0,
                'project_details': {}
            }
    
    
class AnalyzeTools:
    
    @classmethod
    def register_tools(self, mcp: FastMCP):
        '''
        Registers the manipulation tools with the given MCP instance.
        
        Args:
            mcp (FastMCP): The MCP instance to register the tools with.
        '''
        # Register board analyzer
        BoardAnalyzer(mcp)
        