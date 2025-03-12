import os
import networkx as nx
import matplotlib.pyplot as plt
import openai
import json
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in environment variables")
    print("Please create a .env file with your OpenAI API key or set it in your environment")
    sys.exit(1)

# Initialize OpenAI client
client = openai.OpenAI(api_key=api_key)

# Initialize a simple knowledge graph
def initialize_knowledge_graph():
    G = nx.DiGraph()
    
    # Add some initial nodes
    nodes = [
        {"id": "n1", "label": "Impact-Resistant Materials", "type": "concept"},
        {"id": "n2", "label": "Self-Healing Materials", "type": "concept"},
        {"id": "n3", "label": "Machine Learning Algorithms", "type": "concept"}
    ]
    
    # Add nodes to graph
    for node in nodes:
        G.add_node(node["id"], label=node["label"], type=node["type"])
    
    # Add some initial relationships
    edges = [
        {"source": "n1", "target": "n2", "relation": "RELATES-TO"},
        {"source": "n3", "target": "n1", "relation": "OPTIMIZES"}
    ]
    
    # Add edges to graph
    for edge in edges:
        G.add_edge(edge["source"], edge["target"], relation=edge["relation"])
    
    return G

# Visualize the knowledge graph
def visualize_graph(G, title="Knowledge Graph"):
    plt.figure(figsize=(10, 8))
    
    # Create position layout
    pos = nx.spring_layout(G, seed=42)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=500)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, arrows=True)
    
    # Draw node labels
    labels = {node: G.nodes[node]['label'] for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=10)
    
    # Draw edge labels
    edge_labels = {(u, v): G.edges[u, v]['relation'] for u, v in G.edges()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
    
    plt.title(title)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(f"{title.replace(' ', '_')}.png")
    print(f"Graph visualization saved as '{title.replace(' ', '_')}.png'")
    plt.close()

# Convert NetworkX graph to a string representation for the LLM
def graph_to_string(G):
    nodes_str = ""
    for node_id in G.nodes():
        label = G.nodes[node_id].get('label', node_id)
        node_type = G.nodes[node_id].get('type', 'concept')
        nodes_str += f"Node: {node_id}, Label: {label}, Type: {node_type}\n"
    
    edges_str = ""
    for source, target, data in G.edges(data=True):
        source_label = G.nodes[source].get('label', source)
        target_label = G.nodes[target].get('label', target)
        relation = data.get('relation', 'RELATES-TO')
        edges_str += f"Edge: {source_label} --[{relation}]--> {target_label}\n"
    
    return f"Nodes:\n{nodes_str}\nEdges:\n{edges_str}"

# Test the add_node function using GPT-4o
def test_add_node(G, node_type, topic):
    # Create a prompt for GPT-4o
    graph_representation = graph_to_string(G)
    
    prompt = f"""
You are an AI assistant that helps expand knowledge graphs by suggesting new concepts.

Here is the current state of a knowledge graph:
{graph_representation}

Your task is to suggest a new node of type "{node_type}" related to the topic "{topic}" that would be valuable to add to this knowledge graph.

Return your response in the following JSON format only:
{{
    "node_id": "unique ID for the new node (e.g., n4, n5, etc.)",
    "label": "descriptive label for the new node",
    "type": "{node_type}",
    "description": "brief description explaining what this concept is",
    "connections": [
        {{
            "target_node": "ID of an existing node to connect to",
            "relation": "type of relationship (e.g., IS-A, RELATES-TO, INFLUENCES, etc.)",
            "explanation": "brief explanation of why this relationship exists"
        }}
    ]
}}

Make sure your output is valid JSON that can be directly parsed.
"""

    try:
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        # Extract and parse the response
        result = json.loads(response.choices[0].message.content)
        
        # Print the suggestion
        print("\nGPT-4o Suggestion:")
        print(json.dumps(result, indent=2))
        
        # Add the new node to the graph
        G.add_node(
            result["node_id"], 
            label=result["label"], 
            type=result["type"],
            description=result["description"]
        )
        
        # Add the connections
        for connection in result["connections"]:
            G.add_edge(
                result["node_id"],
                connection["target_node"],
                relation=connection["relation"],
                explanation=connection["explanation"]
            )
        
        print(f"\nSuccessfully added new node '{result['label']}' to the knowledge graph with {len(result['connections'])} connections")
        return G, result
    
    except Exception as e:
        print(f"Error in test_add_node: {e}")
        return G, None

# Main function
def main():
    print("Initializing knowledge graph...")
    G = initialize_knowledge_graph()
    
    # Visualize initial graph
    visualize_graph(G, "Initial Knowledge Graph")
    
    # Test adding a node with GPT-4o
    print("\nTesting add_node function with GPT-4o...")
    topic = "sustainable construction materials"
    node_type = "concept"
    
    # Call the function
    G, result = test_add_node(G, node_type, topic)
    
    if result:
        # Visualize the updated graph
        visualize_graph(G, "Updated Knowledge Graph")
        
        # Print graph statistics
        print("\nGraph Statistics:")
        print(f"Number of nodes: {G.number_of_nodes()}")
        print(f"Number of edges: {G.number_of_edges()}")
        
        # Print new relationships
        print("\nNew relationships:")
        for connection in result["connections"]:
            source_label = G.nodes[result["node_id"]]["label"]
            target_label = G.nodes[connection["target_node"]]["label"]
            print(f"- {source_label} --[{connection['relation']}]--> {target_label}: {connection['explanation']}")

if __name__ == "__main__":
    main()
