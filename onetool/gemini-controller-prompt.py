import os
import sys
import base64
import asyncio
import subprocess
from datetime import datetime
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types

class GeminiNetworkInterface:
    """
    A system that uses Gemini to become both the interface and backend controller
    for managing networked computers directly.
    """
    def __init__(self, api_key=None):
        # Initialize the Gemini client
        self.client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))
        self.model = "gemini-2.0-flash-exp"  # Model with image generation capabilities
        self.machines = {}
        self.img_count = 0
        self.current_prompt_state = {}
        
        # Initialize with our known machines
        self.machines["headless-server"] = {"ip": "192.168.1.53", "status": "unknown"}
        self.machines["laptop"] = {"ip": "192.168.1.227", "status": "unknown"}

    def save_image(self, image_data, prefix="network_interface"):
        """Save the generated image to a file"""
        img_path = f"{prefix}_{self.img_count}.png"
        with open(img_path, "wb") as f:
            f.write(image_data)
        self.img_count += 1
        return img_path

    def ping_machine(self, ip_address):
        """Check if a machine is reachable via ping"""
        try:
            # Different ping command parameters based on OS
            param = '-n' if sys.platform.lower() == 'windows' else '-c'
            command = ['ping', param, '1', ip_address]
            
            # Execute the ping command
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
            
            # Return True if ping was successful (return code 0)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            print(f"Error pinging {ip_address}: {str(e)}")
            return False

    def check_all_machines(self):
        """Check the status of all machines in inventory"""
        for name, data in self.machines.items():
            reachable = self.ping_machine(data["ip"])
            self.machines[name]["status"] = "online" if reachable else "offline"
            self.machines[name]["last_checked"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    async def generate_network_interface(self, user_query=None):
        """Generate a visual interface using Gemini based on network status and user query"""
        # First, check the status of our machines
        self.check_all_machines()
        
        # Prepare the system instruction with details about our approach
        system_instruction = """
        You are an AI system that GENERATES IMAGES of network management interfaces. 
        You are the interface itself - not a tool that controls existing UIs.
        
        Your role is to:
        1. Generate visuals that display network status information
        2. Include all textual content WITHIN the image (not as separate text)
        3. Use a modern, clean design with a dark mode theme for IT operations
        4. Highlight machine status with appropriate visual indicators (green for online, red for offline)
        5. Include timestamps of when checks were performed
        6. Show IP addresses and any other relevant network information
        7. Include navigation elements to show what commands/operations are available
        
        You will be given information about machines on a network and should create 
        a complete dashboard visualization that professionals would use to monitor
        and manage these machines.
        """

        # Format current machine status
        machine_status = ""
        for name, data in self.machines.items():
            status_color = "green" if data["status"] == "online" else "red"
            machine_status += f"Machine: {name}\n"
            machine_status += f"IP: {data['ip']}\n"
            machine_status += f"Status: {data['status']} (colored {status_color})\n"
            if "last_checked" in data:
                machine_status += f"Last Checked: {data['last_checked']}\n"
            machine_status += "\n"
        
        # Create the full prompt for image generation
        action_prompt = user_query if user_query else "Show me the status of machines on my network"
        
        complete_prompt = f"""
        {action_prompt}
        
        Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Network Machines Status:
        {machine_status}
        
        IMPORTANT: This is not about creating an interface mock-up or design. You ARE the interface.
        The image you generate IS the actual interface that users will interact with.
        Create a dashboard visualization showing this network information.
        
        Include in your visualization:
        1. Status indicators for each machine
        2. The interface should look like a finished product, not a design mockup
        3. All relevant network information with clean typography
        4. A way to see what operations are available (like "Ping", "Connect", "Get Info")
        5. Make it look like a real application, not a sketch or wireframe
        """

        # Configure the image generation
        generate_content_config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            response_modalities=["image"],
        )

        # Structure the conversation for better image generation
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=system_instruction)]
            ),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="I'll generate a network management interface that directly displays the status of your machines. This will be a finished product view, not a mockup.")]
            ),
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=complete_prompt)]
            )
        ]

        # Generate the image
        try:
            response = None
            async for chunk in self.client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            ):
                if (not chunk.candidates or not chunk.candidates[0].content or 
                    not chunk.candidates[0].content.parts):
                    continue
                
                part = chunk.candidates[0].content.parts[0]
                if hasattr(part, 'inline_data') and part.inline_data:
                    response = chunk
                    break
            
            if not response or not hasattr(response.candidates[0].content.parts[0], 'inline_data'):
                return None, "No image was generated. The model may not have produced image content."
                
            # Extract and save the image
            image_data = response.candidates[0].content.parts[0].inline_data.data
            img_path = self.save_image(image_data)
            
            # Update our internal state for the next interaction
            self.current_prompt_state["last_query"] = user_query
            self.current_prompt_state["last_generated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return image_data, img_path
        except Exception as e:
            print(f"Error generating interface: {str(e)}")
            return None, str(e)

# Example usage
async def main():
    # Initialize the interface
    interface = GeminiNetworkInterface()
    
    # Generate an initial dashboard visualization
    print("Generating initial network interface visualization...")
    image_data, result = await interface.generate_network_interface(
        "Show me the status of my machines at 192.168.1.53 and 192.168.1.227"
    )
    
    if image_data:
        print(f"Generated interface saved to: {result}")
        
        # Display the image if in a notebook environment
        try:
            from IPython.display import display, Image as IPythonImage
            display(IPythonImage(data=image_data))
        except ImportError:
            # Not in a notebook, try to open with PIL
            try:
                Image.open(BytesIO(image_data)).show()
            except Exception as e:
                print(f"Image saved but could not be displayed automatically: {e}")
    else:
        print(f"Failed to generate interface: {result}")
    
    # Simulate user interaction with a follow-up query
    print("\nGenerating detailed view of the headless server...")
    image_data, result = await interface.generate_network_interface(
        "Show me detailed information about the headless server including current status and available operations"
    )
    
    if image_data:
        print(f"Generated detailed view saved to: {result}")
        
        # Display the image if in a notebook environment
        try:
            from IPython.display import display, Image as IPythonImage
            display(IPythonImage(data=image_data))
        except ImportError:
            # Not in a notebook, try to open with PIL
            try:
                Image.open(BytesIO(image_data)).show()
            except Exception as e:
                print(f"Image saved but could not be displayed automatically: {e}")
    else:
        print(f"Failed to generate detailed view: {result}")

if __name__ == "__main__":
    asyncio.run(main())
