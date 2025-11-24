"""Test Audit Logger.

This module provides functionality to log test interactions, specifically LLM calls,
to a markdown file for auditing purposes.
"""

import os
import json
import datetime
from typing import Any, Dict, Optional

class TestAuditLogger:
    """Logs test interactions to a markdown file."""
    
    def __init__(self, log_file: str = "test_audit_log.md"):
        self.log_file = log_file
        self._ensure_log_file_exists()
    
    def _ensure_log_file_exists(self):
        """Initialize the log file with a header if it doesn't exist."""
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.write("# 🕵️‍♂️ Test Audit Log\n\n")
                f.write(f"Created: {datetime.datetime.now().isoformat()}\n\n")
                f.write("---\n\n")
    
    def log_llm_interaction(self, context: str, input_data: Any, output_data: Any, metadata: Optional[Dict] = None):
        """Log an LLM interaction."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"## 🤖 LLM Call: {context}\n")
            f.write(f"**Time:** `{timestamp}`\n\n")
            
            if metadata:
                f.write("**Metadata:**\n```json\n")
                f.write(json.dumps(metadata, indent=2, default=str))
                f.write("\n```\n\n")
            
            f.write("### 📥 Input (Prompt/Message)\n")
            if isinstance(input_data, (dict, list)):
                f.write("```json\n")
                f.write(json.dumps(input_data, indent=2, default=str))
                f.write("\n```\n")
            else:
                f.write("```text\n")
                f.write(str(input_data))
                f.write("\n```\n")
            
            f.write("\n### 📤 Output (Response)\n")
            if isinstance(output_data, (dict, list)):
                f.write("```json\n")
                f.write(json.dumps(output_data, indent=2, default=str))
                f.write("\n```\n")
            else:
                f.write("```text\n")
                f.write(str(output_data))
                f.write("\n```\n")
            
            f.write("\n---\n\n")
    
    def log_event(self, title: str, description: str):
        """Log a general test event."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"## ℹ️ {title}\n")
            f.write(f"**Time:** `{timestamp}`\n\n")
            f.write(f"{description}\n\n")
            f.write("---\n\n")
            
# Global instance
audit_logger = TestAuditLogger()
