import psutil
from typing import Optional

def read_fd_max() -> int:
    try:
        with open('/proc/sys/fs/file-max', 'r') as file:
            pid_max = file.read().strip()
        return int(pid_max)
    except FileNotFoundError:
        raise RuntimeError("The file /proc/sys/kernel/pid_max does not exist.")
    except PermissionError:
        raise RuntimeError("Permission denied when trying to read /proc/sys/kernel/pid_max.")
    except ValueError:
        raise RuntimeError("Unexpected content in /proc/sys/kernel/pid_max; could not convert to an integer.")

def get_anytype_port() -> int:
    first_port_fd = read_fd_max()
    first_port = None
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.fd < first_port_fd and  conn.status == psutil.CONN_LISTEN and  'anytype' in psutil.Process(conn.pid).name().lower():
                first_port_fd = conn.fd
                first_port = conn.laddr.port
        return first_port
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
        raise RuntimeError(f"An error occurred while retrieving ports: {str(e)}") from e

if __name__ == "__main__":
    try:
        ports = get_anytype_port()
        if ports:
            print(f"Anytype is listening on port: {ports}")
        else:
            print("No Anytype port found.")
    except RuntimeError as e:
        print(e)

