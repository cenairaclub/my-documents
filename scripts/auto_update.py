import os
import re
import json
import subprocess

# Configuration
DOCS_DIR = os.path.join("contents", "docs")
SETTINGS_FILE = os.path.join("settings", "documents.ts")
SEARCH_SCRIPT_CMD = ["npx", "-y", "tsx", "scripts/content.ts"]

def parse_frontmatter(file_path):
    """
    Extracts the 'title' from the MDX frontmatter.
    Assumes frontmatter is at the top of the file between --- markers.
    """
    title = "Untitled"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'^---\s*\n(.*?)\n---\s*', content, re.DOTALL)
            if match:
                frontmatter = match.group(1)
                title_match = re.search(r'^title:\s*(.*)$', frontmatter, re.MULTILINE)
                if title_match:
                    title = title_match.group(1).strip().strip('"\'')
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return title

def scan_directory(current_path, relative_href_prefix=""):
    """
    Recursively scans the directory for .mdx files and builds the structure.
    Returns a list of dictionaries representing the items.
    """
    items = []
    
    try:
        entries = sorted(os.listdir(current_path))
    except FileNotFoundError:
        return []

    # Separate files and directories to process files first (optional preference)
    files = [e for e in entries if os.path.isfile(os.path.join(current_path, e)) and e.endswith('.mdx')]
    dirs = [e for e in entries if os.path.isdir(os.path.join(current_path, e))]

    # Process Files
    for filename in files:
        file_path = os.path.join(current_path, filename)
        title = parse_frontmatter(file_path)
        
        slug = filename.replace('.mdx', '')
        href = f"/{slug}"
        
        # If it's an index file, it might handle the parent route (implementation choice)
        # For this logic, we'll treat it as a regular item but usually index files 
        # are special. Let's keep it simple: just add it.
        # Check if user wants index to reside at root. 
        # Typically in next.js docs: /folder/index.mdx -> /folder
        
        if slug == "index":
             href = "/" 
             # Note: logic in pageroutes might concatenate, so if parent is /foo and this is /, result is /foo/
             # If parent is root and this is /, result is /
             # Let's assume standard file-to-route mapping.

        items.append({
            "title": title,
            "href": href
        })

    # Process Directories
    for dirname in dirs:
        dir_path = os.path.join(current_path, dirname)
        sub_items = scan_directory(dir_path)
        
        if sub_items:
            # Capitalize dirname for title if no specific config found
            folder_title = dirname.replace('-', ' ').title()
            
            items.append({
                "title": folder_title,
                "href": f"/{dirname}",
                "items": sub_items
            })

    return items

def generate_ts_content(items):
    """
    Generates the TypeScript content for settings/documents.ts
    """
    ts_content = 'import { Paths } from "@/lib/pageroutes"\n\n'
    ts_content += 'export const Documents: Paths[] = [\n'
    
    def dict_to_ts(obj, indent=2):
        lines = []
        spaces = ' ' * indent
        lines.append(f'{spaces}{{')
        
        # Title
        lines.append(f'{spaces}  title: "{obj["title"]}",')
        
        # Href
        lines.append(f'{spaces}  href: "{obj["href"]}",')
        
        # Heading (Optional, explicit for top-level if needed, but we'll skip for auto-gen for now or default to title)
        # If it's a top level item, maybe add a heading?
        # Let's leave heading out for simplicity unless it's requested.
        
        # Items
        if "items" in obj:
            lines.append(f'{spaces}  items: [')
            for item in obj["items"]:
                lines.append(dict_to_ts(item, indent + 4))
            lines.append(f'{spaces}  ],')
            
        lines.append(f'{spaces}}},')
        return '\n'.join(lines)

    for item in items:
        ts_content += dict_to_ts(item) + '\n'

    ts_content += ']\n'
    return ts_content

def main():
    print(" scanning contents/docs...")
    items = scan_directory(DOCS_DIR)
    
    print(" Generating settings/documents.ts...")
    ts_content = generate_ts_content(items)
    
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        f.write(ts_content)
    
    print(" settings/documents.ts updated successfully.")
    
    print(" Running search index generation...")
    try:
        # Use shell=True for windows if command involves npx/bat files, 
        # but list format is safer. On Windows npx is a cmd script.
        subprocess.run(SEARCH_SCRIPT_CMD, shell=True, check=True)
        print(" Search index generation complete.")
    except subprocess.CalledProcessError as e:
        print(f" Error generating search index: {e}")

if __name__ == "__main__":
    main()
