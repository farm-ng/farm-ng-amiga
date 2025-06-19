import argparse
import asyncio
import logging

from farm_ng import Amiga, nexus as apb

class FocusedTool:
    def __init__(self):
        self.tool_id = None
        self.tool_type = None

    def __str__(self):
        return f"{self.tool_type} ID: {self.tool_id}" if self.tool_id is not None else "No tool focused"

    def __repr__(self):
        return self.__str__()
    
    def focus_tool(self, tool_id: int, tool_type: str):
        """
        Focus on a specific tool by its ID and type.
        
        Args:
            tool_id (int): The ID of the tool to focus on.
            tool_type (str): The type of the tool (e.g., 'hbridge', 'pto').
        """
        
        if not isinstance(tool_id, int) or tool_type not in ["hbridge", "pto"]:
            logging.error("Invalid tool ID or type.")
            return
        
        self.tool_id = tool_id
        self.tool_type = tool_type
        print(f"Selected {self.tool_type} with ID: {self.tool_id}")
        
    def unfocus_tool(self):
        """
        Unfocus the currently focused tool.
        """
        print(f"Unfocused tool: {self.tool_id}")
        self.tool_id = None
        self.tool_type = None
        
        
def validate_tool(tool_id: str, available_tools: dict) -> str:
    if tool_id not in available_tools["hbridge"] and tool_id not in available_tools["pto"]:
        logging.error(f"Tool ID {tool_id} is not available.")
        raise ValueError(f"Tool ID {tool_id} is not available.")
    
    if tool_id in available_tools["hbridge"]:
        return "hbridge"
    elif tool_id in available_tools["pto"]:
        return "pto"

def process_implements(implements: list[apb.ToolRequest], tools_dict: dict) -> None:
    """
    Process the implements and update the tools_dict with available tools.
    
    Args:
        implements (list[apb.ToolRequest]): List of tool requests from feedback.
        tools_dict (dict): Dictionary to store available tools.
    """
    for tool in implements:
        if tool.id not in tools_dict["hbridge"] and tool.id not in tools_dict["pto"]:
            
            tool_state = tool.state
            
            if tool_state.HasField("polar") or tool_state.HasField("switch"):
                if tool.id >= 0 and tool.id < 10:
                    
                    tools_dict["hbridge"].append(tool.id)
                    
            elif tool_state.HasField("rotary"):
                if tool.id >= 10 and tool.id < 20:
                    tools_dict["pto"].append(tool.id)
                    
async def control_tool(focused_tool: FocusedTool, key: str, amiga: Amiga):
    """
    Control the focused tool based on the key input.
    
    Args:
        focused_tool (FocusedTool): The currently focused tool.
        key (str): The key input to control the tool.
        amiga (Amiga): The Amiga instance to send commands to.
    """
    if focused_tool.tool_id is None:
        logging.error("No tool is currently focused.")
        return
    
    if focused_tool.tool_type == "hbridge":
        if key == "z":
            await amiga.activate_tool(focused_tool.tool_id, "hbridge", -5)
            print(f"Moving H-Bridge {focused_tool.tool_id} backward")
        elif key == "x":
            await amiga.activate_tool(focused_tool.tool_id, "hbridge", 5)
            print(f"Moving H-Bridge {focused_tool.tool_id} forward")
        elif key == "d":
            await amiga.deactivate_tool(focused_tool.tool_id, "hbridge")
            print(f"Stopping H-Bridge {focused_tool.tool_id}")
        else:
            logging.error("Invalid command for H-Bridge.")
            
    elif focused_tool.tool_type == "pto":
        if key == "a":
            await amiga.activate_tool(focused_tool.tool_id, "pto", -120)
            print(f"Rotating PTO {focused_tool.tool_id} counter-clockwise")
        elif key == "s":
            await amiga.activate_tool(focused_tool.tool_id, "pto", 120)
            print(f"Rotating PTO {focused_tool.tool_id} clockwise")
        elif key == "d":
            await amiga.deactivate_tool(focused_tool.tool_id, "pto")
            print(f"Stopping PTO {focused_tool.tool_id}")
        else:
            logging.error("Invalid command for PTO.")
    

async def main(address: str):
    logging.info(f"Connecting to Amiga at {address}")
    amiga = Amiga(address=address)
    
    available_tools = {
        "hbridge": [],
        "pto": [],
    }
    
    async def feedback_callback(feedback: apb.Feedback) -> None:
        if feedback.HasField("implement"):
            implements = feedback.implement
            
            if implements and implements.tools:
                process_implements(implements.tools, available_tools)

    try:
        async with amiga.feedback_sub(feedback_callback):
            logging.info("Detecting attatched tools...")

            # Create an event to control how long we run
            stop_event = asyncio.Event()

            # Wait for Ctrl+C
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=3)
            except asyncio.TimeoutError:
                logging.info("Finished")
                
        if not available_tools["hbridge"] and not available_tools["pto"]:
            logging.error("No tools found. Please connect tools to the Amiga.")
            return
        
        focused_tool = FocusedTool()
        while True:
            
            print("\n**Press space to stop all tools!**")
            if focused_tool.tool_id is None:
                print("Select a tool by ID to control it")
                print(f"Available tools: {available_tools}")
                key = input().strip()
                
                if key == " ":
                    await amiga.stop_all_tools(available_tools["hbridge"] + available_tools["pto"])
                    continue
                
                try:
                    key = int(key)
                    tool_type = validate_tool(key, available_tools)
                    focused_tool.focus_tool(key, tool_type)
                except ValueError:
                    print("Invalid input. Please enter a valid tool ID or 'exit'.")
                    continue
                
            else:
                print(f"Controlling {focused_tool}. Press 'q' to select another tool.")
                if focused_tool.tool_type == "hbridge":
                    print("Commands: \n Move backward: 'z', \n Move forward: 'x', \n Stop: 'd'")
                elif focused_tool.tool_type == "pto":
                    print("Commands: \n Counter-Clockwise: 'a', \n Clockwise: 's', \n Stop: 'd'")
                    
                key = input().strip()
                
                if key == " ":
                    await amiga.stop_all_tools(available_tools["hbridge"] + available_tools["pto"])
                    continue
                
                if key == "q":
                    focused_tool.unfocus_tool()
                    continue
                
                await control_tool(focused_tool, key, amiga)
                
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(
        description="Connect to Amiga and record data"
    )
    parser.add_argument(
        "--address",
        type=str,
        default="127.0.0.1",
        help="IP address or hostname of the Amiga"
    )

    args = parser.parse_args()

    asyncio.run(main(args.address))