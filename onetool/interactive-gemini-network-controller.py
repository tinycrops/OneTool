import os
import sys
import base64
import asyncio
import subprocess
import socket
import platform
import paramiko
import json
from datetime import datetime
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types

class GeminiNetworkOS:
    """
    A fully integrated system where Gemini both creates the interface and controls
    network machines - bypassing traditional UIs entirely.
    """
    def __init__(self, api_key=None):
        # Initialize the Gemini client
        self.client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))
        self.model = "gemini-2.0-flash-exp-image-generation"  # Model with image generation capabilities
        self.machines = {}
        self.operations_history = []
        self.img_count = 0
        self.conversation_history = []
        self.prompt_history = []  # Add a list to store prompt history
        
        # System information (will be shown in the interface)
        self.system_info = self._get_local_system_info()
        
        # Initialize with our known machines
        self.machines["headless-server"] = {
            "ip": "192.168.1.53", 
            "username": "aath",
            "password": "a",
            "status": "unknown",
            "services": ["SSH", "File Storage", "Web Server"],
            "os": "Ubuntu 22.04",
            "description": "Headless server for backend processing"
        }
        
        self.machines["laptop"] = {
            "ip": "192.168.1.227", 
            "username": "ath",
            "password": "a",
            "status": "unknown",
            "services": ["SSH", "Development Environment"],
            "os": "Ubuntu 22.04",
            "description": "Main development laptop"
        }
        
        # Available operations that can be performed
        self.available_operations = [
            "ping",
            "port scan",
            "check disk space",
            "list processes",
            "system overview",
            "network topology",
        ]

    def _get_local_system_info(self):
        """Get information about the local system running this code"""
        info = {
            "os": platform.platform(),
            "hostname": socket.gethostname(),
            "ip": self._get_local_ip(),
            "python": sys.version,
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        return info
    
    def _get_local_ip(self):
        """Get the local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Doesn't need to be reachable
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def format_network_info(self, network_info, indent_level=0):
        """Format network information in a readable way"""
        indent = "  " * indent_level
        output = []
        
        # Format machines info
        if 'machines' in network_info:
            output.append(f"{indent}Machines:")
            for machine_name, machine_data in network_info['machines'].items():
                output.append(f"{indent}  {machine_name}:")
                for key, value in machine_data.items():
                    if isinstance(value, (dict, list)) and value:
                        output.append(f"{indent}    {key}:")
                        if isinstance(value, dict):
                            for k, v in value.items():
                                output.append(f"{indent}      {k}: {v}")
                        else:  # list
                            for item in value:
                                output.append(f"{indent}      - {item}")
                    else:
                        output.append(f"{indent}    {key}: {value}")
        
        # Format system info
        if 'system_info' in network_info:
            output.append(f"{indent}System Info:")
            for key, value in network_info['system_info'].items():
                output.append(f"{indent}  {key}: {value}")
        
        # Format operations history
        if 'operations_history' in network_info and network_info['operations_history']:
            output.append(f"{indent}Recent Operations:")
            for op in network_info['operations_history']:
                output.append(f"{indent}  - {op.get('operation')} on {op.get('target')} at {op.get('timestamp')}: {'Success' if op.get('success') else 'Failed'}")
        
        # Format available operations
        if 'available_operations' in network_info:
            output.append(f"{indent}Available Operations:")
            for op in network_info['available_operations']:
                output.append(f"{indent}  - {op}")
        
        return "\n".join(output)

    def save_image(self, image_data, prefix="network_os"):
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
            
            # Return detailed info
            return {
                "success": result.returncode == 0,
                "output": result.stdout.decode('utf-8'),
                "error": result.stderr.decode('utf-8') if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": None, "error": "Timeout while pinging"}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    def scan_ports(self, ip_address, port_range=(1, 1024)):
        """Scan common ports on a machine"""
        open_ports = []
        common_services = {
            22: "SSH",
            80: "HTTP",
            443: "HTTPS",
            21: "FTP",
            25: "SMTP",
            53: "DNS",
            3306: "MySQL",
            5432: "PostgreSQL",
            8080: "HTTP-ALT",
            27017: "MongoDB"
        }
        
        # Only scan a few important ports for the proof of concept
        scan_ports = [22, 80, 443, 8080, 3306, 5432]
        
        for port in scan_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex((ip_address, port))
            if result == 0:
                service = common_services.get(port, "Unknown")
                open_ports.append({"port": port, "service": service})
            sock.close()
        
        return open_ports

    def get_real_machine_info(self, machine_name):
        """Get real information from a machine using SSH"""
        machine = self.machines.get(machine_name)
        if not machine:
            return {"error": f"Machine '{machine_name}' not found"}
        
        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to the machine
            ssh.connect(
                machine["ip"], 
                username=machine["username"], 
                password=machine["password"],
                timeout=5
            )
            
            # Get disk space
            stdin, stdout, stderr = ssh.exec_command("df -h /")
            disk_info = stdout.read().decode('utf-8')
            
            # Get running processes
            stdin, stdout, stderr = ssh.exec_command("ps aux | head -10")
            processes = stdout.read().decode('utf-8')
            
            # Get system info
            stdin, stdout, stderr = ssh.exec_command("uname -a")
            system_info = stdout.read().decode('utf-8')
            
            # Get memory usage
            stdin, stdout, stderr = ssh.exec_command("free -h")
            memory_info = stdout.read().decode('utf-8')
            
            # Close the connection
            ssh.close()
            
            return {
                "success": True,
                "disk_info": disk_info,
                "processes": processes,
                "system_info": system_info,
                "memory_info": memory_info
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_all_machines(self):
        """Check the status of all machines in inventory and get real information"""
        for name, data in self.machines.items():
            # Check if the machine is reachable
            ping_result = self.ping_machine(data["ip"])
            self.machines[name]["status"] = "online" if ping_result["success"] else "offline"
            self.machines[name]["last_checked"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # If online, scan for open ports and get real information
            if ping_result["success"]:
                open_ports = self.scan_ports(data["ip"])
                self.machines[name]["open_ports"] = open_ports
                
                # Get real information from the machine
                real_info = self.get_real_machine_info(name)
                if real_info.get("success"):
                    self.machines[name]["real_info"] = real_info
            
            # Record this operation
            self.operations_history.append({
                "operation": "check_status",
                "target": name,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "result": "success" if ping_result["success"] else "failed"
            })

    def execute_operation(self, operation, target=None):
        """Execute a specific operation on a target machine"""
        result = {
            "operation": operation,
            "target": target,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "success": False,
            "data": None,
            "error": None
        }
        
        try:
            if operation == "ping":
                if target in self.machines:
                    ping_result = self.ping_machine(self.machines[target]["ip"])
                    result["success"] = ping_result["success"]
                    result["data"] = ping_result["output"]
                    result["error"] = ping_result["error"]
                else:
                    result["error"] = f"Machine '{target}' not found in inventory"
            
            elif operation == "port scan":
                if target in self.machines:
                    open_ports = self.scan_ports(self.machines[target]["ip"])
                    result["success"] = True
                    result["data"] = open_ports
                else:
                    result["error"] = f"Machine '{target}' not found in inventory"
            
            elif operation == "check disk space":
                if target in self.machines:
                    real_info = self.get_real_machine_info(target)
                    if real_info.get("success"):
                        result["success"] = True
                        result["data"] = real_info["disk_info"]
                    else:
                        result["error"] = real_info.get("error", "Failed to get disk information")
                else:
                    result["error"] = f"Machine '{target}' not found in inventory"
            
            elif operation == "list processes":
                if target in self.machines:
                    real_info = self.get_real_machine_info(target)
                    if real_info.get("success"):
                        result["success"] = True
                        result["data"] = real_info["processes"]
                    else:
                        result["error"] = real_info.get("error", "Failed to get process information")
                else:
                    result["error"] = f"Machine '{target}' not found in inventory"
            
            elif operation == "system overview":
                # Check all machines
                self.check_all_machines()
                result["success"] = True
                result["data"] = {name: data for name, data in self.machines.items()}
            
            elif operation == "network topology":
                # Generate a network topology with real information
                self.check_all_machines()
                result["success"] = True
                result["data"] = {
                    "nodes": [
                        {"name": "Router", "ip": "192.168.1.1", "type": "network"},
                        {"name": "headless-server", "ip": "192.168.1.53", "type": "server", 
                         "status": self.machines["headless-server"]["status"]},
                        {"name": "laptop", "ip": "192.168.1.227", "type": "workstation",
                         "status": self.machines["laptop"]["status"]},
                        {"name": "controller", "ip": self.system_info["ip"], "type": "controller"}
                    ],
                    "connections": [
                        {"from": "Router", "to": "headless-server"},
                        {"from": "Router", "to": "laptop"},
                        {"from": "Router", "to": "controller"}
                    ]
                }
            else:
                result["error"] = f"Unknown operation: {operation}"
        
        except Exception as e:
            result["error"] = str(e)
        
        # Record this operation in history
        self.operations_history.append(result)
        return result

    def display_prompt_history(self):
        """Display the history of prompts sent to the LLM"""
        print("\n===== PROMPT HISTORY =====")
        for i, prompt_data in enumerate(self.prompt_history):
            print(f"\n--- Prompt #{i+1} ({prompt_data['timestamp']}) ---")
            print(f"User Query: {prompt_data['user_query']}")
            print("Full Prompt:")
            # Format the network_info part of the prompt nicely
            network_info = prompt_data.get('network_info', {})
            if network_info:
                print(self.format_network_info(network_info))
            else:
                # If no network_info, just print the raw prompt
                print(prompt_data['prompt'])
            print("----------------------------")
        print("===========================\n")
    
    def save_prompt_history(self, filename="prompt_history.json"):
        """Save the prompt history to a JSON file"""
        try:
            # Convert the history to a serializable format
            serializable_history = []
            for item in self.prompt_history:
                # Create a copy of the item to avoid modifying the original
                serializable_item = item.copy()
                
                # Format network_info in a more readable way
                if 'network_info' in serializable_item:
                    network_info = serializable_item['network_info']
                    formatted_network_info = {
                        'machines': {},
                        'system_info': {},
                        'operations_history': [],
                        'available_operations': []
                    }
                    
                    # Format machines
                    if 'machines' in network_info:
                        for machine_name, machine_data in network_info['machines'].items():
                            formatted_network_info['machines'][machine_name] = {
                                key: str(value) if isinstance(value, (dict, list)) else value
                                for key, value in machine_data.items()
                            }
                    
                    # Format system info
                    if 'system_info' in network_info:
                        formatted_network_info['system_info'] = network_info['system_info']
                    
                    # Format operations history
                    if 'operations_history' in network_info:
                        for op in network_info['operations_history']:
                            formatted_op = {
                                'operation': op.get('operation'),
                                'target': op.get('target'),
                                'timestamp': op.get('timestamp'),
                                'success': op.get('success'),
                                'error': op.get('error')
                            }
                            # Convert any complex data to string
                            if 'data' in op and op['data']:
                                formatted_op['data'] = str(op['data'])
                            formatted_network_info['operations_history'].append(formatted_op)
                    
                    # Format available operations
                    if 'available_operations' in network_info:
                        formatted_network_info['available_operations'] = network_info['available_operations']
                    
                    serializable_item['network_info'] = formatted_network_info
                
                serializable_history.append(serializable_item)
            
            # Save to file with nice formatting
            with open(filename, 'w') as f:
                json.dump(serializable_history, f, indent=2, default=str)
            
            print(f"Prompt history saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving prompt history: {e}")
            return False

    def save_comparison_prompts(self):
        """Save the original and refined prompts to separate files for comparison"""
        try:
            # Find pairs of original and refined prompts
            original_prompts = []
            refined_prompts = []
            
            for item in self.prompt_history:
                if "Refined prompt for:" in item.get("user_query", ""):
                    refined_prompts.append({
                        "timestamp": item["timestamp"],
                        "prompt": item["prompt"],
                        "original_prompt": item.get("original_prompt", ""),
                        "original_image": item.get("original_image", "")
                    })
                elif "network_info" in item:
                    original_prompts.append({
                        "timestamp": item["timestamp"],
                        "prompt": item["prompt"],
                        "user_query": item["user_query"]
                    })
            
            # Save original prompts
            if original_prompts:
                with open("original_prompts.json", 'w') as f:
                    json.dump(original_prompts, f, indent=2, default=str)
                print("Original prompts saved to original_prompts.json")
            
            # Save refined prompts
            if refined_prompts:
                with open("refined_prompts.json", 'w') as f:
                    json.dump(refined_prompts, f, indent=2, default=str)
                print("Refined prompts saved to refined_prompts.json")
            
            # Save a comparison file
            if original_prompts and refined_prompts:
                comparisons = []
                for i in range(min(len(original_prompts), len(refined_prompts))):
                    comparisons.append({
                        "original": {
                            "timestamp": original_prompts[i]["timestamp"],
                            "prompt": original_prompts[i]["prompt"],
                            "user_query": original_prompts[i]["user_query"]
                        },
                        "refined": {
                            "timestamp": refined_prompts[i]["timestamp"],
                            "prompt": refined_prompts[i]["prompt"]
                        }
                    })
                
                with open("prompt_comparisons.json", 'w') as f:
                    json.dump(comparisons, f, indent=2, default=str)
                print("Prompt comparisons saved to prompt_comparisons.json")
            
            return True
        except Exception as e:
            print(f"Error saving comparison prompts: {e}")
            return False

    async def generate_interface(self, user_query=None):
        """Generate a visual interface using Gemini based on network status and user input"""
        # Process the user query to execute relevant operations
        if user_query:
            if "ping" in user_query.lower() and any(machine in user_query.lower() for machine in self.machines):
                for machine in self.machines:
                    if machine in user_query.lower():
                        self.execute_operation("ping", machine)
            
            elif "scan" in user_query.lower() and any(machine in user_query.lower() for machine in self.machines):
                for machine in self.machines:
                    if machine in user_query.lower():
                        self.execute_operation("port scan", machine)
            
            elif "disk" in user_query.lower() and any(machine in user_query.lower() for machine in self.machines):
                for machine in self.machines:
                    if machine in user_query.lower():
                        self.execute_operation("check disk space", machine)
            
            elif "process" in user_query.lower() and any(machine in user_query.lower() for machine in self.machines):
                for machine in self.machines:
                    if machine in user_query.lower():
                        self.execute_operation("list processes", machine)
            
            elif "overview" in user_query.lower() or "status" in user_query.lower():
                self.execute_operation("system overview")
            
            elif "topology" in user_query.lower() or "network map" in user_query.lower():
                self.execute_operation("network topology")

        # First, check the status of our machines
        self.check_all_machines()
        
        # Format current machine status
        machine_info = {}
        for name, data in self.machines.items():
            machine_info[name] = {
                "ip": data["ip"],
                "status": data["status"],
                "os": data.get("os", "Unknown"),
                "description": data.get("description", ""),
                "services": data.get("services", []),
                "last_checked": data.get("last_checked", "")
            }
            
            if "open_ports" in data:
                machine_info[name]["open_ports"] = data["open_ports"]
                
            if "real_info" in data:
                machine_info[name]["real_info"] = data["real_info"]
        
        # Create a simplified prompt for image generation
        network_info = {
            "machines": machine_info,
            "system_info": self.system_info,
            "operations_history": self.operations_history[-5:],  # Last 5 operations
            "available_operations": self.available_operations
        }
        
        # Simplified prompt
        simplified_prompt = f"generate a computer monitor with the following text on it {network_info}"
        
        # Display the prompt in the terminal
        print("\n===== CURRENT PROMPT =====")
        print("User Query:", user_query if user_query else "None")
        print("\nNetwork Information:")
        print(self.format_network_info(network_info, indent_level=1))
        print("\nRaw Prompt:")
        print(simplified_prompt)
        print("==========================\n")
        
        # Save the prompt to history
        self.prompt_history.append({
            "user_query": user_query,
            "prompt": simplified_prompt,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "network_info": network_info
        })

        # Configure the image generation
        generate_content_config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_modalities=[
                "image",
                "text",
            ],
            response_mime_type="text/plain",
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_CIVIC_INTEGRITY",
                    threshold="OFF",  # Off
                ),
            ],
        )

        # Structure the conversation for better image generation
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=simplified_prompt)]
            )
        ]

        # Generate the image
        try:
            response = None
            # Fix the async for loop by properly awaiting the coroutine
            stream = await self.client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            )
            
            async for chunk in stream:
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
            
            # Add this interaction to conversation history
            self.conversation_history.append({
                "query": user_query,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "image_path": img_path
            })
            
            return image_data, img_path
        except Exception as e:
            print(f"Error generating interface: {str(e)}")
            return None, str(e)

    async def refine_image_prompt(self, original_prompt, image_path, user_query):
        """
        Send the original prompt and generated image to Gemini 2.0 Flash Exp
        to get a refined prompt for better image generation
        """
        try:
            # Read the image file
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # Create a prompt for Gemini to refine the image generation prompt
            refinement_prompt = f"""
            I'm using Gemini to generate network management interface visualizations.
            
            Here's my original prompt:
            "{original_prompt}"
            
            This prompt was based on a user query: "{user_query}"
            
            The image generated from this prompt is attached. I'd like you to:
            
            1. Analyze what works and what doesn't work about the current image
            2. Rewrite my prompt to create a better network management interface visualization
            3. Focus on making the interface look more professional, clear, and informative
            4. Include specific details about layout, colors, typography, and information organization
            5. Make sure all the network information is clearly displayed
            
            Please provide a completely rewritten prompt that I can use with the image generation model.
            """
            
            # Configure the content generation
            generate_content_config = types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            )
            
            # Create the image part - fixing the error here
            image_part = types.Part(
                inline_data=types.Blob(
                    mime_type="image/png",
                    data=image_data
                )
            )
            
            # Structure the conversation for prompt refinement
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=refinement_prompt),
                        image_part
                    ]
                )
            ]
            
            # Generate the refined prompt
            response = await self.client.aio.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=contents,
                config=generate_content_config,
            )
            
            # Extract the refined prompt
            refined_prompt = response.text
            
            print("\n===== REFINED PROMPT =====")
            print(refined_prompt)
            print("==========================\n")
            
            # Save the refined prompt to history
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.prompt_history.append({
                "user_query": f"Refined prompt for: {user_query}",
                "prompt": refined_prompt,
                "timestamp": timestamp,
                "original_prompt": original_prompt,
                "original_image": image_path
            })
            
            return refined_prompt
            
        except Exception as e:
            print(f"Error refining prompt: {e}")
            return None

    async def generate_interface_with_refined_prompt(self, user_query=None):
        """
        Generate a visual interface using Gemini with a refined prompt
        """
        # First generate with the original prompt
        image_data, img_path = await self.generate_interface(user_query)
        
        if not image_data:
            return None, "Failed to generate initial image"
        
        # Get the original prompt
        original_prompt = self.prompt_history[-1]["prompt"]
        
        # Refine the prompt
        print("Refining the prompt for better image generation...")
        refined_prompt = await self.refine_image_prompt(original_prompt, img_path, user_query)
        
        if not refined_prompt:
            return image_data, img_path  # Return the original image if refinement fails
        
        # Configure the image generation with the refined prompt
        generate_content_config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_modalities=[
                "image",
                "text",
            ],
            response_mime_type="text/plain",
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_CIVIC_INTEGRITY",
                    threshold="OFF",  # Off
                ),
            ],
        )

        # Structure the conversation for better image generation
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=refined_prompt)]
            )
        ]

        # Generate the image with the refined prompt
        try:
            response = None
            # Fix the async for loop by properly awaiting the coroutine
            stream = await self.client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            )
            
            async for chunk in stream:
                if (not chunk.candidates or not chunk.candidates[0].content or 
                    not chunk.candidates[0].content.parts):
                    continue
                
                part = chunk.candidates[0].content.parts[0]
                if hasattr(part, 'inline_data') and part.inline_data:
                    response = chunk
                    break
            
            if not response or not hasattr(response.candidates[0].content.parts[0], 'inline_data'):
                return image_data, img_path  # Return the original image if refined generation fails
                
            # Extract and save the refined image
            refined_image_data = response.candidates[0].content.parts[0].inline_data.data
            refined_img_path = self.save_image(refined_image_data, prefix="refined_network_os")
            
            # Create a side-by-side comparison
            comparison_path = self.compare_images(img_path, refined_img_path)
            
            # Add this interaction to conversation history
            self.conversation_history.append({
                "query": f"Refined image for: {user_query}",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "image_path": refined_img_path,
                "original_image_path": img_path,
                "comparison_path": comparison_path
            })
            
            # Save a text file with the prompts for comparison
            with open(f"prompt_comparison_{self.img_count-1}.txt", "w") as f:
                f.write("ORIGINAL PROMPT:\n")
                f.write(original_prompt)
                f.write("\n\n")
                f.write("REFINED PROMPT:\n")
                f.write(refined_prompt)
            
            print(f"Prompt comparison saved to: prompt_comparison_{self.img_count-1}.txt")
            
            # Return the refined image data and path
            return refined_image_data, refined_img_path
        except Exception as e:
            print(f"Error generating interface with refined prompt: {e}")
            return image_data, img_path  # Return the original image if an error occurs

    def compare_images(self, original_path, refined_path):
        """Create a side-by-side comparison of the original and refined images"""
        try:
            # Open the images
            original_img = Image.open(original_path)
            refined_img = Image.open(refined_path)
            
            # Resize if needed to make them the same height
            height = min(original_img.height, refined_img.height)
            original_width = int(original_img.width * (height / original_img.height))
            refined_width = int(refined_img.width * (height / refined_img.height))
            
            original_img = original_img.resize((original_width, height))
            refined_img = refined_img.resize((refined_width, height))
            
            # Create a new image with both side by side
            total_width = original_width + refined_width
            comparison_img = Image.new('RGB', (total_width, height))
            
            # Paste the images
            comparison_img.paste(original_img, (0, 0))
            comparison_img.paste(refined_img, (original_width, 0))
            
            # Save the comparison
            comparison_path = f"comparison_{self.img_count}.png"
            comparison_img.save(comparison_path)
            
            print(f"Comparison image saved to: {comparison_path}")
            return comparison_path
        except Exception as e:
            print(f"Error creating comparison image: {e}")
            return None

# Example usage
async def main():
    # Initialize the interface
    interface = GeminiNetworkOS()
    
    # User query
    user_query = "Show me the status of all machines on my network"
    
    # Generate an initial dashboard visualization and then refine it
    print("Generating network interface visualization with refined prompt...")
    image_data, result = await interface.generate_interface_with_refined_prompt(user_query)
    
    if image_data:
        print(f"Generated interface saved to: {result}")
        
        # Get the comparison path from the last conversation entry
        comparison_path = None
        if interface.conversation_history:
            comparison_path = interface.conversation_history[-1].get("comparison_path")
        
        # Display the comparison image if available
        if comparison_path and os.path.exists(comparison_path):
            print(f"Comparison image saved to: {comparison_path}")
            try:
                # Try to display the comparison image
                comparison_img = Image.open(comparison_path)
                comparison_img.show()
            except Exception as e:
                print(f"Could not display comparison image automatically: {e}")
        else:
            # Display the refined image if in a notebook environment
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
    
    # Display the prompt history
    interface.display_prompt_history()
    
    # Save the prompt history to a file
    interface.save_prompt_history()
    
    # Save comparison prompts
    interface.save_comparison_prompts()

if __name__ == "__main__":
    asyncio.run(main())