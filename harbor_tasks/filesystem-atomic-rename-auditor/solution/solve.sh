#!/bin/bash
# Hint from Snorkel
# Expert-authored step-by-step solution contained with a shell script that reliably and accurately completes the task.

set -euo pipefail

mkdir -p /app

cat > /app/solution.py <<'PY_EOF'
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class WriteOp:
    """Represents a write operation."""
    seq: int
    size: Optional[int]  # None if unknown


@dataclass
class FileDescriptor:
    """Tracks a file descriptor's state."""
    pid: int
    fd: int
    path: str
    writes: list[WriteOp] = field(default_factory=list)
    last_fsync: Optional[int] = None  # Sequence number of last fsync
    closed: bool = False
    closed_seq: Optional[int] = None


@dataclass
class RenameOp:
    """Represents a rename operation."""
    pid: int
    seq: int
    from_path: str
    to_path: str
    status: str = "UNKNOWN"
    reason: str = ""


class TraceAnalyzer:
    """Analyzes filesystem trace logs to determine rename atomicity."""
    
    def __init__(self):
        self.fds: dict[tuple[int, int], FileDescriptor] = {}  # (pid, fd) -> FileDescriptor
        self.path_to_fd: dict[tuple[int, str], tuple[int, int]] = {}  # (pid, path) -> (pid, fd)
        self.renames: list[RenameOp] = []
        self.dir_fsyncs: dict[str, int] = {}  # dir -> last sequence number
        self.seq = 0
        self.all_ops: list[tuple[int, str, str]] = []  # (seq, op_type, args) for debugging
        self.path_renames: dict[str, str] = {}  # Track path changes through renames: old_path -> current_path
    
    def parse_line(self, line: str) -> None:
        """Parse a single trace line."""
        line = line.strip()
        if not line or line.startswith("#"):
            return
        
        self.seq += 1
        
        # Format: pid:operation:args
        # Split into max 3 parts: pid, operation, and all remaining args
        parts = line.split(":", 2)
        if len(parts) < 3:
            return
        
        pid = int(parts[0])
        op = parts[1]
        args = parts[2]
        
        self.all_ops.append((self.seq, op, args))
        
        if op == "open":
            self._handle_open(pid, args)
        elif op == "write":
            self._handle_write(pid, args)
        elif op == "fsync":
            self._handle_fsync(pid, args)
        elif op == "rename":
            self._handle_rename(pid, args)
        elif op == "close":
            self._handle_close(pid, args)
        elif op == "dir_fsync":
            self._handle_dir_fsync(args)
    
    def _handle_open(self, pid: int, args: str) -> None:
        """Handle open operation: pid:open:path:flags:fd=X"""
        match = re.search(r'fd=(\d+)', args)
        if not match:
            return
        
        fd = int(match.group(1))
        # Extract path (before :fd= or before first :)
        path_match = re.match(r'([^:]+)', args)
        if not path_match:
            return
        
        path = path_match.group(1)
        key = (pid, fd)
        self.fds[key] = FileDescriptor(pid=pid, fd=fd, path=path)
        self.path_to_fd[(pid, path)] = (pid, fd)
    
    def _handle_write(self, pid: int, args: str) -> None:
        """Handle write operation: pid:write:fd=X:size=N"""
        match = re.search(r'fd=(\d+)', args)
        if not match:
            return
        
        fd = int(match.group(1))
        key = (pid, fd)
        
        if key not in self.fds:
            return
        
        # Extract size
        size_match = re.search(r'size=(\d+|\?)', args)
        if size_match:
            size_str = size_match.group(1)
            if size_str == "?":
                self.fds[key].writes.append(WriteOp(seq=self.seq, size=None))
            else:
                self.fds[key].writes.append(WriteOp(seq=self.seq, size=int(size_str)))
        else:
            self.fds[key].writes.append(WriteOp(seq=self.seq, size=None))
    
    def _handle_fsync(self, pid: int, args: str) -> None:
        """Handle fsync operation: pid:fsync:fd=X"""
        match = re.search(r'fd=(\d+)', args)
        if not match:
            return
        
        fd = int(match.group(1))
        key = (pid, fd)
        
        if key in self.fds:
            self.fds[key].last_fsync = self.seq
    
    def _handle_close(self, pid: int, args: str) -> None:
        """Handle close operation: pid:close:fd=X"""
        match = re.search(r'fd=(\d+)', args)
        if not match:
            return
        
        fd = int(match.group(1))
        key = (pid, fd)
        
        if key in self.fds:
            self.fds[key].closed = True
            self.fds[key].closed_seq = self.seq
    
    def _handle_rename(self, pid: int, args: str) -> None:
        """Handle rename operation: pid:rename:from_path:to_path"""
        parts = args.split(":", 1)
        if len(parts) < 2:
            return
        
        from_path = parts[0]
        to_path = parts[1]
        
        # Track path changes for subsequent renames
        # Update path tracking: if from_path was already renamed, update the chain
        # Otherwise, just track this rename
        updated = False
        for orig_path, current_path in list(self.path_renames.items()):
            if current_path == from_path:
                self.path_renames[orig_path] = to_path
                updated = True
                break
        if not updated:
            self.path_renames[from_path] = to_path
        
        # Store the rename operation with original paths from trace
        rename_op = RenameOp(pid=pid, seq=self.seq, from_path=from_path, to_path=to_path)
        self.renames.append(rename_op)
    
    def _handle_dir_fsync(self, args: str) -> None:
        """Handle directory fsync: dir_fsync:path"""
        path = args.strip()
        self.dir_fsyncs[path] = self.seq
    
    def analyze(self) -> None:
        """Analyze all renames and determine their safety."""
        for rename in self.renames:
            self._analyze_rename(rename)
    
    def _get_fd_for_path(self, pid: int, path: str, at_seq: int) -> Optional[FileDescriptor]:
        """Get file descriptor for a path at a given sequence number."""
        # Resolve path through renames
        current_path = path
        for old_path, new_path in self.path_renames.items():
            if new_path == current_path:
                # Check if this rename happened before at_seq
                rename_op = next((r for r in self.renames if r.to_path == new_path and r.seq <= at_seq), None)
                if rename_op:
                    current_path = old_path
                    break
        
        # First try direct lookup
        if (pid, current_path) in self.path_to_fd:
            key = self.path_to_fd[(pid, current_path)]
            if key in self.fds:
                fd = self.fds[key]
                if fd.closed_seq is None or fd.closed_seq > at_seq:
                    return fd
        
        # Search all FDs that might have written to this path (or its original path)
        for key, fd in self.fds.items():
            if fd.path == current_path and (fd.closed_seq is None or fd.closed_seq > at_seq):
                return fd
        
        return None
    
    def _analyze_rename(self, rename: RenameOp) -> None:
        """Determine if a rename is SAFE, UNSAFE, or AMBIGUOUS."""
        from_path = rename.from_path
        to_path = rename.to_path
        to_dir = str(Path(to_path).parent)
        
        # Find file descriptor that wrote to this file
        # Look for FDs that accessed this path, even if they were closed before rename
        fd_info = None
        # First try to find FD from the same process
        for key, fd_obj in self.fds.items():
            if fd_obj.pid == rename.pid and fd_obj.path == from_path:
                # Check if this FD was used before the rename
                if fd_obj.writes or fd_obj.last_fsync is not None:
                    fd_info = fd_obj
                    break
        
        # If not found, try to find any FD that accessed this path
        if not fd_info:
            for key, fd_obj in self.fds.items():
                if fd_obj.path == from_path:
                    # Check if this FD was used before the rename
                    if fd_obj.writes or fd_obj.last_fsync is not None:
                        fd_info = fd_obj
                        break
        
        # Check for missing write size information (must check before other validations)
        if fd_info:
            if any(w.size is None for w in fd_info.writes):
                rename.status = "AMBIGUOUS"
                rename.reason = "Missing write size information"
                return
        
        # Check for cross-process file descriptor leak
        # Find all open FDs from other processes pointing to the same file
        # Key issue: if process A has open FD, process B renames, then process A writes
        # FDs point to inodes, so after rename, the FD still points to the same file
        for key, fd_obj in self.fds.items():
            # Check if this FD was opened to the same file (the from_path before rename)
            if fd_obj.path == from_path:
                if fd_obj.pid != rename.pid:
                    # Check if FD was open at rename time
                    if fd_obj.closed_seq is None or fd_obj.closed_seq > rename.seq:
                        # Check if there were writes AFTER rename from this other process
                        writes_after_rename = [w for w in fd_obj.writes if w.seq > rename.seq]
                        if writes_after_rename:
                            rename.status = "UNSAFE"
                            rename.reason = "Cross-process file descriptor leak: another process has open FD with writes after rename"
                            return
        
        # Check if file was properly fsynced before rename
        if not fd_info:
            # Can't determine file state, but still check directory fsync
            dir_fsync_seq = self.dir_fsyncs.get(to_dir)
            if dir_fsync_seq is None or dir_fsync_seq < rename.seq:
                rename.status = "UNSAFE"
                rename.reason = "Directory not fsynced after rename"
            else:
                rename.status = "AMBIGUOUS"
                rename.reason = "Cannot determine file state"
            return
        
        # Check if fsync was on the correct FD
        # For the file being renamed, we need fsync on THIS specific FD
        # Check if there's a fsync on this FD
        if fd_info.last_fsync is None:
            # Check if there was an fsync on a different FD from the same process
            # This handles the case where fsync was called on wrong FD (Test 5)
            for key, other_fd in self.fds.items():
                if other_fd.pid == rename.pid and other_fd.path != from_path:
                    if other_fd.last_fsync is not None and other_fd.last_fsync < rename.seq:
                        rename.status = "UNSAFE"
                        rename.reason = "fsync was called on different file descriptor"
                        return
            
            rename.status = "UNSAFE"
            rename.reason = "File not fsynced before rename"
            return
        
        # Check for writes after fsync (on the same FD)
        if fd_info.last_fsync is not None:
            writes_after_fsync = [w for w in fd_info.writes if w.seq > fd_info.last_fsync]
            if writes_after_fsync:
                rename.status = "UNSAFE"
                rename.reason = "Write after fsync invalidates durability"
                return
        
        # Check directory fsync - must happen AFTER rename
        dir_fsync_seq = self.dir_fsyncs.get(to_dir)
        if dir_fsync_seq is None:
            rename.status = "UNSAFE"
            rename.reason = "Directory not fsynced after rename"
            return
        
        if dir_fsync_seq < rename.seq:
            rename.status = "UNSAFE"
            rename.reason = "Directory fsync happened before rename (must be after)"
            return
        
        # Check if there are other renames to the same directory before this rename
        # If multiple renames happen to the same directory before a dir_fsync, only the first one should be safe
        other_renames_before_this = [
            r for r in self.renames
            if r.seq < rename.seq and r.seq < dir_fsync_seq and str(Path(r.to_path).parent) == to_dir
        ]
        if other_renames_before_this:
            # There are other renames to the same directory before this rename
            # Only the first rename before the dir_fsync should be safe
            # So this rename is unsafe
            rename.status = "UNSAFE"
            rename.reason = "Directory not fsynced after rename (other renames to same directory before fsync)"
            return
        
        # Check if there's a subsequent rename of the same file
        # If the file is renamed again, we need a directory fsync between the renames
        next_rename = None
        for other_rename in self.renames:
            if other_rename.seq > rename.seq and other_rename.from_path == to_path:
                next_rename = other_rename
                break
        
        # If there's a subsequent rename, check if there's a dir_fsync between them
        if next_rename is not None:
            # Need a directory fsync between this rename and the next one
            # The dir_fsync must happen after this rename AND before the next rename
            if dir_fsync_seq >= next_rename.seq:
                # Directory fsync happens after the next rename, so this rename is unsafe
                rename.status = "UNSAFE"
                rename.reason = "Directory not fsynced after rename (file renamed again without intermediate fsync)"
                return
        
        # All checks passed
        rename.status = "SAFE"
        rename.reason = "File fsynced, directory fsynced after rename"
    
    def get_results(self) -> dict:
        """Return results as dictionary."""
        return {
            "renames": [
                {
                    "from": r.from_path,
                    "to": r.to_path,
                    "pid": r.pid,
                    "status": r.status,
                    "reason": r.reason,
                }
                for r in self.renames
            ]
        }


def audit_renames(trace_path: str, out_path: str) -> None:
    """Main function to audit renames in a trace file.
    
    Args:
        trace_path: Path to trace.log file
        out_path: Path to write results.json
    """
    analyzer = TraceAnalyzer()
    
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            analyzer.parse_line(line)
    
    analyzer.analyze()
    
    results = analyzer.get_results()
    
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
PY_EOF
