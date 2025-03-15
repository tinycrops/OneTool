import os
import base64
import asyncio
import paramiko
from PIL import Image
from io import BytesIO
from datetime import datetime
from google import genai
from google.genai import types

class NetworkController:
    """
    A system that uses Gemini to generate visual interfaces and control network machines
    directly through SSH connections, bypassing traditional UI interaction.
    """
    def __init__(self, api_key=None):
        # Initialize the Gemini client
        self.client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))
        self.model = "gemini-2.0-flash-exp"  # Model with image generation capabilities
        self.machines = {}
        self.ssh_connections = {}
        self.img_count = 0

    def add_machine(self, name, ip, username, password=None, key_file=None):
        """Add a machine to the controller's inventory"""
        self.machines[name] = {
            "ip": ip,
            "username": username,
            "password": password,
            "key_file": key_file,
            "status": "disconnected",
            "info": {}
        }
        return self

    def save_image(self, image_data, prefix="gemini_ui"):
        """Save the generated image to a file"""
        img_path = f"{prefix}_{self.img_count}.png"
        with open(img_path, "wb") as f:
            f.write(image_data)
        self.img_count += 1
        return img_path

    def connect_to_machine(self, machine_name):
        """Establish SSH connection to a specified machine"""
        if machine_name not in self.machines:
            raise ValueError(f"Machine {machine_name} not in inventory")
        
        machine = self.machines[machine_name]
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect using password or key file
            if machine["key_file"]:
                client.connect(
                    machine["ip"],
                    username=machine["username"],
                    key_filename=machine["key_file"]
                )
            else:
                client.connect(
                    machine["ip"],
                    username=machine["username"],
                    password=machine["password"]
                )
            
            self.ssh_connections[machine_name] = client
            self.machines[machine_name]["status"] = "connected"
            return True
        except Exception as e:
            print(f"Failed to connect to {machine_name}: {str(e)}")
            self.machines[machine_name]["status"] = f"error: {str(e)}"
            return False

    def execute_command(self, machine_name, command):
        """Execute a command on a connected machine"""
        if machine_name not in self.ssh_connections:
            if not self.connect_to_machine(machine_name):
                return {"error": f"Cannot connect to {machine_name}"}
        
        client = self.ssh_connections[machine_name]
        
        try:
            stdin, stdout, stderr = client.exec_command(command)
            result = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            return {
                "stdout": result,
                "stderr": error,
                "success": not error
            }
        except Exception as e:
            return {"error": str(e)}

    def get_system_info(self, machine_name):
        """Get system information from a machine"""
        commands = {
            "hostname": "hostname",
            "cpu_info": "lscpu | grep 'Model name' | cut -d: -f2 | sed 's/^ *//'",
            "memory": "free -h | grep Mem | awk '{print $2}'",
            "disk": "df -h / | awk 'NR==2 {print $2}'",
            "uptime": "uptime -p",
            "load": "uptime | awk -F'load average:' '{ print $2 }'",
            "processes": "ps aux | wc -l",
            "distro": "cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'"
        }
        
        results = {}
        for key, cmd in commands.items():
            cmd_result = self.execute_command(machine_name, cmd)
            if "error" not in cmd_result:
                results[key] = cmd_result["stdout"].strip()
        
        self.machines[machine_name]["info"] = results
        return results

    async def generate_interface(self, prompt, context=None):
        """Generate a visual interface using Gemini"""
        system_instruction = """
        You are a specialized AI that creates informative, clear dashboards for IT and network management. 
        Your visuals should:
        1. Use a clean, professional design with a dark mode theme
        2. Include all relevant system status information clearly labeled
        3. Highlight critical information or alerts with appropriate colors (red for errors, yellow for warnings)
        4. Use a consistent layout with proper spacing and alignment
        5. Include a timestamp of when the data was collected
        6. Generate text as part of the image (not separate) that's readable and properly sized
        7. Use icons where appropriate to enhance readability
        
        Your UI should be complete and ready to present to users with no additional processing needed.
        """
        
        # Format machine data for display
        machines_data = ""
        for name, data in self.machines.items():
            machines_data += f"Machine: {name} ({data['ip']})\n"
            machines_data += f"Status: {data['status']}\n"
            
            if data["info"]:
                machines_data += "System Information:\n"
                for key, value in data["info"].items():
                    machines_data += f"  - {key}: {value}\n"
            machines_data += "\n"
        
        # Create content for generating the image
        complete_prompt = f"""
        {prompt}
        
        Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Network Machines:
        {machines_data}
        
        Additional Context:
        {context or 'No additional context provided.'}
        
        Create a dashboard interface that displays this information clearly and professionally.
        """

        generate_content_config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            response_modalities=["image"],
        )

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=system_instruction)]
            ),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="I'll generate a clean, professional dashboard with all the network information.")]
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
                
                if chunk.candidates[0].content.parts[0].inline_data:
                    response = chunk
                    break
            
            if not response:
                return None, "No image generated"
                
            # Extract and save the image
            image_data = response.candidates[0].content.parts[0].inline_data.data
            mime_type = response.candidates[0].content.parts[0].inline_data.mime_type
            img_path = self.save_image(image_data)
            
            return image_data, img_path
        except Exception as e:
            print(f"Error generating interface: {str(e)}")
            return None, str(e)

# Example usage
async def main():
    # Initialize the controller
    controller = NetworkController()
    
    # Add the two machines
    controller.add_machine(
        name="headless-server", 
        ip="192.168.1.53", 
        username="user",  # Replace with actual username
        password="password"  # Replace with actual password or use key_file
    )
    
    controller.add_machine(
        name="laptop", 
        ip="192.168.1.227", 
        username="user",  # Replace with actual username
        password="password"  # Replace with actual password or use key_file
    )
    
    # Try to get system info (this will attempt connection)
    try:
        controller.get_system_info("headless-server")
    except Exception as e:
        print(f"Could not connect to headless-server: {e}")
    
    try:
        controller.get_system_info("laptop")
    except Exception as e:
        print(f"Could not connect to laptop: {e}")
    
    # Generate the interface visualization
    prompt = "Show me the status dashboard for my network machines"
    image_data, img_path = await controller.generate_interface(prompt)
    
    if image_data:
        print(f"Generated interface saved to: {img_path}")
        
        # Display the image if in a notebook environment
        try:
            from IPython.display import display, Image as IPythonImage
            display(IPythonImage(data=image_data))
        except ImportError:
            # Not in a notebook, open the file
            try:
                Image.open(BytesIO(image_data)).show()
            except:
                print("Image saved but could not be displayed automatically")
    else:
        print(f"Failed to generate interface: {img_path}")

if __name__ == "__main__":
    asyncio.run(main())
