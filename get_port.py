import psutil
from typing import List, Optional

def get_anytype_ports() -> List[int]:
    ports = []
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == psutil.CONN_LISTEN and 'anytype' in psutil.Process(conn.pid).name().lower():
                ports.append(conn.laddr.port)
        return ports  # Return the list of ports
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        raise RuntimeError(f"An error occurred while retrieving ports: {str(e)}") from e

def get_anytype_port() -> Optional[int]:
    ports = get_anytype_ports()  # Reuse the function to get all ports
    return min(ports) if ports else None 


if __name__ == "__main__":
    try:
        ports = get_anytype_ports()
        if ports:
            print(f"Anytype is listening on ports: {ports}")
        else:
            print("No Anytype port found.")
    except RuntimeError as e:
        print(e)

