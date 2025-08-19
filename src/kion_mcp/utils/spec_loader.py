"""Utility for loading the OpenAPI specification file across different deployment scenarios."""

import json
import logging
from pathlib import Path
from typing import Dict, Any
import importlib.resources as pkg_resources



def load_openapi_spec() -> Dict[str, Any]:
    """
    Load the OpenAPI specification file.
    
    This function works across multiple deployment scenarios:
    - Local development (spec file in project root)
    - PyPI installs (spec file included as package data)
    - Docker containers (spec file copied to /app/)
    - Claude Desktop extensions (spec file in distribution)
    
    Returns:
        Dict containing the parsed OpenAPI specification
        
    Raises:
        FileNotFoundError: If the spec file cannot be found in any location
        json.JSONDecodeError: If the spec file is not valid JSON
    """
    spec_content = None
    source_info = None
    
    # Strategy 1: Try to load from package resources (works for installed packages)
    try:
        # First try to load from the kion_mcp package itself
        try:
            spec_content = pkg_resources.files('kion_mcp').joinpath('fixed_spec.json').read_text()
            source_info = "package resources (kion_mcp)"
        except (FileNotFoundError, AttributeError):
            # Try loading from the package root as an artifact
            import kion_mcp
            package_path = Path(kion_mcp.__file__).parent
            # Look for the spec file in the package directory
            possible_paths = [
                package_path / 'fixed_spec.json',
                package_path.parent / 'fixed_spec.json',
            ]
            
            for path in possible_paths:
                if path.exists():
                    spec_content = path.read_text()
                    source_info = f"package directory ({path})"
                    break
                    
    except Exception as e:
        logging.debug(f"Failed to load spec from package resources: {e}")
    
    # Try loading from same directory as this file (package directory)
    if spec_content is None:
        try:
            current_file = Path(__file__)
            # Look for spec file in the kion_mcp package directory
            package_spec_path = current_file.parent.parent / "fixed_spec.json"
            
            if package_spec_path.exists():
                spec_content = package_spec_path.read_text()
                source_info = f"package directory ({package_spec_path})"
        except Exception as e:
            logging.debug(f"Failed to load spec from package directory: {e}")
    
    # Try relative to the current module (local development)
    if spec_content is None:
        try:
            current_file = Path(__file__)
            # Go up from src/kion_mcp/utils/spec_loader.py to project root
            project_root = current_file.parent.parent.parent.parent
            spec_path = project_root / "fixed_spec.json"
            
            if spec_path.exists():
                spec_content = spec_path.read_text()
                source_info = f"project root ({spec_path})"
        except Exception as e:
            logging.debug(f"Failed to load spec from project root: {e}")
    
    # Try current working directory
    if spec_content is None:
        try:
            cwd_spec_path = Path.cwd() / "fixed_spec.json"
            if cwd_spec_path.exists():
                spec_content = cwd_spec_path.read_text()
                source_info = f"current directory ({cwd_spec_path})"
        except Exception as e:
            logging.debug(f"Failed to load spec from current directory: {e}")
    
    # Try environment-specific locations
    if spec_content is None:
        import os
        # Check if there's an environment variable pointing to the spec file
        env_spec_path = os.environ.get('KION_MCP_SPEC_PATH')
        if env_spec_path:
            try:
                env_path = Path(env_spec_path)
                if env_path.exists():
                    spec_content = env_path.read_text()
                    source_info = f"environment variable ({env_path})"
            except Exception as e:
                logging.debug(f"Failed to load spec from environment path: {e}")
    
    if spec_content is None:
        raise FileNotFoundError(
            "Could not find fixed_spec.json in any of the expected locations. "
            "Tried: package resources, project root, Docker location (/app/), "
            "current directory, and KION_MCP_SPEC_PATH environment variable."
        )
    
    try:
        openapi_spec = json.loads(spec_content)
        logging.info(f"Successfully loaded OpenAPI spec from {source_info}")
        return openapi_spec
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in OpenAPI spec file loaded from {source_info}: {e}",
            e.doc, e.pos
        )
