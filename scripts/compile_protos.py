#!/usr/bin/env python3
"""
Script to compile Protocol Buffer definitions for the voice assistant system.
Includes gRPC reflection support for external tools like grpcui and grpcurl.
"""

import os
import subprocess
import sys
from pathlib import Path


def compile_protos():
    """Compile all .proto files to Python gRPC stubs with reflection support"""

    # Define paths
    project_root = Path(__file__).parent.parent
    proto_dir = project_root / "protos"
    output_dir = project_root / "src" / "voice_assistant" / "infrastructure" / "grpc" / "generated"

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py files
    (output_dir / "__init__.py").touch()

    # Find all .proto files
    proto_files = list(proto_dir.glob("*.proto"))

    if not proto_files:
        print("No .proto files found in", proto_dir)
        return False

    print(f"Found {len(proto_files)} proto files:")
    for proto_file in proto_files:
        print(f"  - {proto_file.name}")

    # Compile each proto file
    success = True
    for proto_file in proto_files:
        print(f"\nCompiling {proto_file.name}...")

        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            f"--proto_path={proto_dir}",
            f"--python_out={output_dir}",
            f"--grpc_python_out={output_dir}",
            str(proto_file)
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"  [OK] Successfully compiled {proto_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"  [FAIL] Failed to compile {proto_file.name}")
            print(f"    Error: {e.stderr}")
            success = False
        except FileNotFoundError:
            print("  [FAIL] grpcio-tools not found. Install with: pip install grpcio-tools")
            success = False
            break

    if success:
        print(f"\n[OK] All proto files compiled successfully!")
        print(f"Generated files are in: {output_dir}")

        # List generated files
        generated_files = list(output_dir.glob("*_pb2.py")) + list(output_dir.glob("*_pb2_grpc.py"))
        if generated_files:
            print("\nGenerated files:")
            for file in sorted(generated_files):
                print(f"  - {file.name}")

        # Generate reflection descriptors for each service
        print("\nGenerating gRPC reflection descriptors...")
        generate_reflection_descriptors(proto_files, output_dir, proto_dir)
    else:
        print(f"\n[FAIL] Some proto files failed to compile")
        return False

    return True


def generate_reflection_descriptors(proto_files, output_dir, proto_dir):
    """Generate reflection descriptor files for each proto service"""

    reflection_files = []

    for proto_file in proto_files:
        proto_name = proto_file.stem  # e.g., "audio" from "audio.proto"
        descriptor_file = output_dir / f"{proto_name}_pb2.py"

        if descriptor_file.exists():
            # Create a simple reflection module that exports the descriptor
            reflection_module = output_dir / f"{proto_name}_reflection.py"

            reflection_content = f'''# Generated reflection module for {proto_file.name}
# This module enables gRPC reflection for tools like grpcui and grpcurl

import grpc
from grpc_reflection.v1alpha import reflection

# Import the generated pb2 modules
from . import {proto_name}_pb2
from . import {proto_name}_pb2_grpc

# Get the descriptor from the pb2 module
DESCRIPTOR = {proto_name}_pb2.DESCRIPTOR

# Service names for reflection (will be populated by service implementations)
SERVICE_NAMES = []


def add_service_to_reflection(service_name: str):
    """Add a service name to the reflection list"""
    if service_name not in SERVICE_NAMES:
        SERVICE_NAMES.append(service_name)


def enable_reflection(server: grpc.Server):
    """Enable gRPC reflection on the given server"""
    # Add reflection service to the server
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    print(f"  [OK] gRPC reflection enabled for: {{', '.join(SERVICE_NAMES)}}")
'''

            reflection_module.write_text(reflection_content)
            reflection_files.append(reflection_module.name)
            print(f"  [OK] Generated reflection module: {reflection_module.name}")

    if reflection_files:
        print(f"\n[OK] Generated {len(reflection_files)} reflection descriptor files")
        print("  These enable external tools (grpcui, grpcurl) to discover services")
    else:
        print("  No reflection files generated (no valid proto descriptors found)")


if __name__ == "__main__":
    success = compile_protos()
    sys.exit(0 if success else 1)