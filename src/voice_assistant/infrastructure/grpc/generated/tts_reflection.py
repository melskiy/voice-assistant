# Generated reflection module for tts.proto
# This module enables gRPC reflection for tools like grpcui and grpcurl

import grpc
from grpc_reflection.v1alpha import reflection

# Import the generated pb2 modules
from . import tts_pb2
from . import tts_pb2_grpc

# Get the descriptor from the pb2 module
DESCRIPTOR = tts_pb2.DESCRIPTOR

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
    print(f"  [OK] gRPC reflection enabled for: {', '.join(SERVICE_NAMES)}")
