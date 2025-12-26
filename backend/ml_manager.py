import subprocess
import signal
import os
import time
from typing import Dict, Optional

class MLProcessManager:
    """Manages realtime_engagement.py subprocesses"""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
    
    def start_ml_process(self, session_id: int, student_id: int, token: str) -> Optional[int]:
        """Start ML engagement process"""
        key = f"session_{session_id}_student_{student_id}"
        
        if key in self.processes:
            return None
        
        try:
            proc = subprocess.Popen(
                [
                    "python",
                    "realtime_engagement.py",
                    f"--session-id={session_id}",
                    f"--student-id={student_id}",
                    f"--token={token}"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            self.processes[key] = proc
            print(f"✅ ML started: PID={proc.pid}, session={session_id}")
            return proc.pid
            
        except Exception as e:
            print(f"❌ Failed to start ML: {e}")
            return None
    
    def stop_ml_process(self, session_id: int, student_id: int) -> bool:
        """Stop ML engagement process"""
        key = f"session_{session_id}_student_{student_id}"
        
        if key not in self.processes:
            return False
        
        proc = self.processes[key]
        
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=2)
            print(f"✅ ML stopped gracefully: PID={proc.pid}")
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()
            print(f"⚠️ ML force-killed: PID={proc.pid}")
        except Exception as e:
            print(f"❌ Error killing process: {e}")
            return False
        finally:
            del self.processes[key]
        
        return True
    
    def cleanup_all(self):
        """Stop all running ML processes"""
        for key in list(self.processes.keys()):
            parts = key.split("_")
            session_id = int(parts[1])
            student_id = int(parts[3])
            self.stop_ml_process(session_id, student_id)

ml_manager = MLProcessManager()