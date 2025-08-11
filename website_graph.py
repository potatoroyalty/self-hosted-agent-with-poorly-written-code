import json
import os
from collections import deque
from typing import Dict, List, Optional, Any

class WebsiteGraph:
    """
    Represents the structure of a website as a graph, where pages are nodes
    and actions (like clicks or navigations) are edges.
    """
    def __init__(self, graph_file_path: str = "graph.json"):
        self.graph_file_path = graph_file_path
        self.graph: Dict[str, Dict[str, Any]] = {}
        self.load_graph()

    def load_graph(self):
        """Loads the graph from the specified file."""
        if os.path.exists(self.graph_file_path):
            with open(self.graph_file_path, 'r', encoding='utf-8') as f:
                self.graph = json.load(f)
            print(f"[INFO] Website graph loaded from {self.graph_file_path}")

    def save_graph(self):
        """Saves the graph to the specified file."""
        with open(self.graph_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.graph, f, indent=4)
        print(f"[INFO] Website graph saved to {self.graph_file_path}")

    def add_page(self, url: str, page_title: Optional[str] = None):
        """
        Adds a page (node) to the graph if it doesn't already exist.

        Args:
            url (str): The URL of the page to add.
            page_title (str, optional): The title of the page.
        """
        if url not in self.graph:
            self.graph[url] = {
                "title": page_title,
                "edges": []
            }
            print(f"[INFO] Added new page to graph: {url}")

    def add_edge(self, from_url: str, to_url: str, action: Dict[str, Any]):
        """
        Adds a directed edge (action) between two pages.

        Args:
            from_url (str): The URL of the source page.
            to_url (str): The URL of the destination page.
            action (Dict[str, Any]): A dictionary describing the action.
                                     e.g., {"type": "click", "element_label": 3}
        """
        if from_url not in self.graph:
            self.add_page(from_url)

        # Avoid duplicate edges
        for edge in self.graph[from_url]["edges"]:
            if edge["to_url"] == to_url and edge["action"] == action:
                return

        self.graph[from_url]["edges"].append({
            "to_url": to_url,
            "action": action
        })
        print(f"[INFO] Added new edge: {from_url} -> {to_url} via {action}")

    def find_path(self, start_url: str, end_url: str) -> Optional[List[Dict[str, Any]]]:
        """
        Finds the shortest path from a start URL to an end URL using BFS.

        Args:
            start_url (str): The starting URL.
            end_url (str): The destination URL.

        Returns:
            A list of actions representing the path, or None if no path is found.
        """
        if start_url not in self.graph or end_url not in self.graph:
            return None

        queue = deque([(start_url, [])])  # (current_url, path_of_actions)
        visited = {start_url}

        while queue:
            current_url, path = queue.popleft()

            if current_url == end_url:
                return path

            for edge in self.graph.get(current_url, {}).get("edges", []):
                next_url = edge["to_url"]
                if next_url not in visited:
                    visited.add(next_url)
                    new_path = path + [edge["action"]]
                    queue.append((next_url, new_path))

        return None
