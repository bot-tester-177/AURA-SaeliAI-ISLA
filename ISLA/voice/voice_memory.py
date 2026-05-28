"""Voice-triggered memory management for Isla.

Stores and recalls voice interaction facts, ensuring that important context
from voice sessions is persisted and available across sessions.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class VoiceMemory:
    """A voice interaction memory entry."""
    
    id: int | None = None
    timestamp: datetime | None = None
    user_input: str = ""
    isla_response: str = ""
    emotion_detected: str | None = None
    important: bool = False
    notes: str | None = None
    
    def to_tuple(self) -> tuple:
        """Convert to tuple for SQLite insertion (excluding id)."""
        ts = (self.timestamp or datetime.now(timezone.utc)).isoformat()
        return (ts, self.user_input, self.isla_response, self.emotion_detected, 
                self.important, self.notes)


class VoiceMemoryStore:
    """SQLite-backed storage for voice interaction memories."""
    
    TABLE_NAME = "voice_memories"
    
    def __init__(self, db_path: Path | str = ".isla_voice_memory.db"):
        """Initialize the memory store.
        
        Args:
            db_path: Path to the SQLite database.
        """
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    isla_response TEXT NOT NULL,
                    emotion_detected TEXT,
                    important BOOLEAN DEFAULT 0,
                    notes TEXT
                )
            """)
            # Create index for efficient recent-memory queries
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_timestamp ON {self.TABLE_NAME}(timestamp DESC)")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_important ON {self.TABLE_NAME}(important DESC)")
            conn.commit()
    
    def save_memory(self, memory: VoiceMemory) -> int:
        """Save a voice memory to the store.
        
        Args:
            memory: The VoiceMemory to save.
        
        Returns:
            The ID of the saved memory.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {self.TABLE_NAME}
                (timestamp, user_input, isla_response, emotion_detected, important, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, memory.to_tuple())
            conn.commit()
            return cursor.lastrowid
    
    def get_recent_memories(self, limit: int = 5) -> list[VoiceMemory]:
        """Get the most recent voice memories.
        
        Args:
            limit: Maximum number of memories to return.
        
        Returns:
            List of VoiceMemory objects, most recent first.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM {self.TABLE_NAME}
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        
        return [self._row_to_memory(row) for row in rows]
    
    def get_important_memories(self, limit: int = 10) -> list[VoiceMemory]:
        """Get marked important voice memories.
        
        Args:
            limit: Maximum number of memories to return.
        
        Returns:
            List of VoiceMemory objects marked as important.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM {self.TABLE_NAME}
                WHERE important = 1
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        
        return [self._row_to_memory(row) for row in rows]
    
    def search_memories(self, query: str, limit: int = 10) -> list[VoiceMemory]:
        """Search through voice memories by user input or response.
        
        Args:
            query: Search term to find in user input or isla response.
            limit: Maximum number of results to return.
        
        Returns:
            List of matching VoiceMemory objects.
        """
        search_pattern = f"%{query}%"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM {self.TABLE_NAME}
                WHERE user_input LIKE ? OR isla_response LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (search_pattern, search_pattern, limit))
            rows = cursor.fetchall()
        
        return [self._row_to_memory(row) for row in rows]
    
    def mark_important(self, memory_id: int) -> bool:
        """Mark a memory as important for retention.
        
        Args:
            memory_id: The ID of the memory to mark.
        
        Returns:
            True if successful, False if memory not found.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {self.TABLE_NAME} SET important = 1 WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_memory_summary(self) -> dict:
        """Get a summary of voice memory statistics.
        
        Returns:
            Dict with total_memories, important_count, and memory_dates.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT COUNT(*) FROM {self.TABLE_NAME}")
            total = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE important = 1")
            important_count = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {self.TABLE_NAME}")
            min_ts, max_ts = cursor.fetchone()
        
        return {
            "total_memories": total,
            "important_count": important_count,
            "oldest_memory": min_ts,
            "newest_memory": max_ts,
        }
    
    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> VoiceMemory:
        """Convert a sqlite3.Row to a VoiceMemory object."""
        return VoiceMemory(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            user_input=row["user_input"],
            isla_response=row["isla_response"],
            emotion_detected=row["emotion_detected"],
            important=bool(row["important"]),
            notes=row["notes"],
        )


if __name__ == "__main__":
    # Quick test of the memory store
    store = VoiceMemoryStore()
    
    # Save a test memory
    test_memory = VoiceMemory(
        user_input="What's your favorite thing about our conversations?",
        isla_response="Honestly? When you ask real questions. The ones where you're genuinely curious about something, not just making small talk.",
        emotion_detected="engaged",
        important=True,
        notes="Meaningful conversation about connection",
    )
    mem_id = store.save_memory(test_memory)
    print(f"Saved memory with ID: {mem_id}")
    
    # Retrieve and display stats
    stats = store.get_memory_summary()
    print(f"Memory store stats: {stats}")
    
    # Get important memories
    important = store.get_important_memories()
    for mem in important:
        print(f"Important memory: {mem.user_input[:50]}...")
