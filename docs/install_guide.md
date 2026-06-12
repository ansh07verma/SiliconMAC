# OpenMAC-PD Installation Guide

## System Requirements

- **OS**: Windows with WSL2 (Ubuntu 22.04+ or 24.04+)
- **Docker**: Docker Desktop for Windows (with WSL2 backend)
- **Memory**: 8 GB RAM minimum (16 GB recommended)
- **Disk**: 10 GB free space for PDK and tools

## Step 1: Install WSL2

```powershell
# In PowerShell (Admin)
wsl --install -d Ubuntu
# Restart when prompted
```

## Step 2: Install Docker

1. Download Docker Desktop from https://www.docker.com/products/docker-desktop/
2. Install with WSL2 backend enabled
3. Verify in WSL:
```bash
wsl -d Ubuntu -- docker --version
```

## Step 3: Get OpenLane Docker Image

```bash
wsl -d Ubuntu -- docker pull efabless/openlane:latest
```

## Step 4: Install Sky130 PDK

The PDK is installed inside the Docker container:

```bash
# Start container
docker run -d --name openlane-pd \
  -v /path/to/OpenMAC-PD:/workspace \
  efabless/openlane:latest sleep infinity

# Install PDK inside container
docker exec openlane-pd bash -c '
  export PATH=/nix/store/*/bin:$PATH
  volare fetch --pdk sky130 0fe599b2afb6708d281543108caf8310912f54af
  volare enable --pdk sky130 --pdk-root /opt/pdk 0fe599b2afb6708d281543108caf8310912f54af
'
```

## Step 5: Install Simulation Tools (Optional)

For local simulation without Docker:

```bash
# In WSL
sudo apt install iverilog gtkwave
```

## Step 6: Verify Installation

```bash
# Test simulation
cd /path/to/OpenMAC-PD/verification
make sim

# Test synthesis (in Docker)
docker exec openlane-pd bash -c 'cd /workspace && make -C flow syn'

# Test full flow
docker exec openlane-pd bash -c '
  export PDK_ROOT=/opt/pdk
  cd /workspace
  python3 openmac.py flow --width 8 --array-size 4
'
```

## Troubleshooting

### Docker container stops immediately
Use `sleep infinity` as the container command:
```bash
docker run -d --name openlane-pd \
  -v /path/to/OpenMAC-PD:/workspace \
  efabless/openlane:latest sleep infinity
```

### PDK not found
Ensure the PDK is enabled:
```bash
docker exec openlane-pd bash -c 'ls /opt/pdk/sky130A/libs.ref/'
```

### iverilog not found
Install in WSL:
```bash
sudo apt install iverilog
```

### Yosys not found
Use the Docker container which has Yosys pre-installed:
```bash
docker exec openlane-pd yosys --version
```
