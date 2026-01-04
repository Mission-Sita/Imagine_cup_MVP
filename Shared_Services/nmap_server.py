from mcp.server.fastmcp import FastMCP
import asyncio
import shutil
import subprocess
import sys
import os
import logging

# 📝 SETUP FILE LOGGING (The "Black Box" Recorder)
# This creates a file 'debug_nmap.log' in the same folder.
logging.basicConfig(
    filename="debug_nmap.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w" # Overwrite each time
)

logging.info("🔥 Nmap Server Starting Up...")

mcp = FastMCP("nmap")

def run_nmap_sync_debug(command):
    logging.info(f"🧵 [THREAD] Starting command: {command}")
    try:
        logging.info("🧵 [THREAD] subprocess.run() calling...")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=45,
            stdin=subprocess.DEVNULL
        )
        logging.info(f"🧵 [THREAD] Finished. Return Code: {result.returncode}")
        return result.stdout, result.stderr, result.returncode

    except subprocess.TimeoutExpired:
        logging.error("🧵 [THREAD] ❌ TIMEOUT!")
        return None, "TIMEOUT", -1
    except Exception as e:
        logging.error(f"🧵 [THREAD] ❌ CRASH: {e}")
        return None, str(e), -1

@mcp.tool()
async def do_nmap(target: str, nmap_args: list[str] = None) -> str:
    logging.info(f"📨 [Request Received] Target: {target}")

    # 1. Path Setup
    nmap_path = shutil.which("nmap")
    if not nmap_path:
        possible = [r"C:\Program Files (x86)\Nmap\nmap.exe", r"C:\Program Files\Nmap\nmap.exe"]
        for p in possible:
            if os.path.exists(p):
                nmap_path = p
                break
    
    if not nmap_path:
        logging.error("❌ Nmap not found in PATH")
        return "Error: 'nmap' not found. Install it and add to PATH."

    # 2. Arg Cleanup
    if not nmap_args: nmap_args = ["-F", "-T4"]
    if isinstance(nmap_args, str):
         nmap_args = nmap_args.replace("[","").replace("]","").replace("'","").replace('"','').split()

    # 3. Execution
    command = [nmap_path, target] + nmap_args
    logging.info(f"🚀 Preparing to execute: {command}")

    try:
        logging.info("🚀 Offloading to thread...")
        stdout, stderr, returncode = await asyncio.to_thread(run_nmap_sync_debug, command)
        logging.info("🚀 Thread returned.")

        if stderr == "TIMEOUT":
             return "❌ Error: Nmap scan timed out (45s limit)."
        
        output = (stdout or "").strip()
        error = (stderr or "").strip()

        if returncode != 0:
            logging.warning(f"⚠️ Nmap Non-Zero Exit: {returncode}")
            return f"Nmap Failed (Code {returncode}):\n{output}\nError Log:\n{error}"

        if output:
            logging.info("✅ Success! Returning output.")
            return output
        elif error:
            return f"Nmap Output:\n{output}\nInfo:\n{error}"
        else:
            return "Nmap finished but returned no output."

    except Exception as e:
        logging.critical(f"🔥 CRITICAL ERROR: {e}")
        return f"Execution Critical Error: {str(e)}"

if __name__ == "__main__":
    logging.info("✅ Server Ready and Listening via Stdio")
    # Also print to stderr just in case console works
    print("✅ Nmap Server Online (File Logging Mode)", file=sys.stderr)
    try:
        mcp.run()
    except Exception as e:
        logging.critical(f"🔥 MCP RUN FAILED: {e}")