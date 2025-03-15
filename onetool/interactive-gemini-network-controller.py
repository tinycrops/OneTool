import os
import sys
import base64
import asyncio
import subprocess
import socket
import platform
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
        self.model = "gemini-2.0-flash-exp"  # Model with image generation capabilities
        self.machines = {}
        self.operations_history = []
        self.img_count = 0
        self.conversation_history = []
        
        # System information (will be shown in the interface)
        self.system_info = self._get_local_system_info()
        
        # Initialize with our known machines
        self.machines["headless-server"] = {
            "ip": "192.168.1.53", 
            "status": "unknown",
            "services": ["SSH", "File Storage", "Web Server"],
            "os": "Ubuntu 22.04",
            "description": "Headless server for backend processing"
        }
        
        self.machines["laptop"] = {
            "ip": "192.168.1.227", 
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

    def check_all_machines(self):
        """Check the status of all machines in inventory"""
        for name, data in self.machines.items():
            # Check if the machine is reachable
            ping_result = self.ping_machine(data["ip"])
            self.machines[name]["status"] = "online" if ping_result["success"] else "offline"
            self.machines[name]["last_checked"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # If online, scan for open ports
            if ping_result["success"]:
                open_ports = self.scan_ports(data["ip"])
                self.machines[name]["open_ports"] = open_ports
            
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
                # This is a simulated operation
                if target in self.machines:
                    result["success"] = True
                    result["data"] = {
                        "total": "500GB",
                        "used": "125GB",
                        "available": "375GB",
                        "percent_used": "25%"
                    }
                else:
                    result["error"] = f"Machine '{target}' not found in inventory"
            
            elif operation == "list processes":
                # This is a simulated operation
                if target in self.machines:
                    result["success"] = True
                    result["data"] = [
                        {"pid": 1, "name": "systemd", "cpu": "0.1%", "memory": "0.2%"},
                        {"pid": 1234, "name": "nginx", "cpu": "0.5%", "memory": "1.2%"},
                        {"pid": 5678, "name": "python3", "cpu": "2.5%", "memory": "4.3%"}
                    ]
                else:
                    result["error"] = f"Machine '{target}' not found in inventory"
            
            elif operation == "system overview":
                # Check all machines
                self.check_all_machines()
                result["success"] = True
                result["data"] = {name: data for name, data in self.machines.items()}
            
            elif operation == "network topology":
                # Generate a simulated network topology
                result["success"] = True
                result["data"] = {
                    "nodes": [
                        {"name": "Router", "ip": "192.168.1.1", "type": "network"},
                        {"name": "headless-server", "ip": "192.168.1.53", "type": "server"},
                        {"name": "laptop", "ip": "192.168.1.227", "type": "workstation"},
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

    async def generate_interface(self, user_query=None):
        """Generate a visual interface using Gemini based on network status and user input"""
        # Prepare conversation for generating the image
        if user_query:
            # Process the user query to execute relevant operations
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
                        self.execute_operation("