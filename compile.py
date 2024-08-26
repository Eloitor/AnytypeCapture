import os
from grpc_tools import protoc

proto_dir = "./protos"
proto_files = [f for f in os.listdir(proto_dir) if f.endswith('.proto')]

output_path = "./generated_protos_py"
os.makedirs(output_path, exist_ok=True)

# Compile each .proto file
for proto_file in proto_files:
    full_proto_path = os.path.join(proto_dir, proto_file)
    protoc.main((
        '',
        f'-I{proto_dir}',
        f'--python_out={output_path}',
        f'--grpc_python_out={output_path}',
        full_proto_path,
    ))

print(f"Compilation complete. Files are generated in the '{output_path}' directory.")
