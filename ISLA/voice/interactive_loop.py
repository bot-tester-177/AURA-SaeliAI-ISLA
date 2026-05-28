"""Interactive voice loop for Isla — test voice I/O with personality integration.

This script provides a simple REPL for testing Isla's voice pipeline:
- User input (keyboard or mic)
- LLM response generation
- Voice output with speaker cloning
- Memory persistence

Usage:
    python -m ISLA.voice.interactive_loop

Commands:
    /help       - Show available commands
    /assets     - Show configured voice assets
    /memory     - Show recent voice memories
    /quit       - Exit the loop
    Any other text will be sent to Isla
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Callable

# Ensure workspace root is on path
workspace_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(workspace_root))

from ISLA.voice.voice_loop import VoiceLoop
from ISLA.voice.voice_memory import VoiceMemory, VoiceMemoryStore
from ISLA.voice.personality_examples import get_few_shot_prompt


class InteractiveVoiceLoop:
    """Interactive voice testing loop with memory and personality integration."""
    
    def __init__(self, use_mic: bool = False):
        """Initialize the interactive loop.
        
        Args:
            use_mic: Whether to use actual microphone input.
        """
        self.voice_loop = VoiceLoop()
        self.memory_store = VoiceMemoryStore()
        self.use_mic = use_mic
        self.responder = self._create_responder()
        self.stats = {
            "turns": 0,
            "total_input_chars": 0,
            "total_response_chars": 0,
            "total_speak_time": 0.0,
        }
    
    def _create_responder(self) -> Callable[[str], str]:
        """Create a responder function that generates responses.
        
        Returns:
            A function that takes user input and returns Isla's response.
        """
        def responder(text: str) -> str:
            # For now, a simple echo responder that applies personality tone
            # In full implementation, this would call the LLM with the few-shot prompt
            if not text.strip():
                return ""
            
            # Use personality few-shot prompt
            few_shot = get_few_shot_prompt(num_examples=3)
            
            # Simple response: reflect personality traits
            response = f"I appreciate that perspective about {text.split()[0] if text.split() else 'that'}. Tell me more?"
            return response
        
        return responder
    
    def _show_help(self) -> None:
        """Display help information."""
        help_text = """
Isla Interactive Voice Loop
===========================

Commands:
  /help       - Show this help message
  /assets     - Show configured voice asset paths
  /memory     - Show recent voice memories
  /stats      - Show session statistics
  /important  - Show marked important memories
  /quit       - Exit the loop

Input:
  - Type any text and press Enter to send to Isla
  - Isla will generate a response and speak it aloud (if TTS is available)
  - Voice interactions are saved to memory

Memory:
  - Important memories are preserved across sessions
  - You can search and recall conversations later
"""
        print(help_text)
    
    def _show_assets(self) -> None:
        """Show configured voice assets."""
        print("\nConfigured Voice Assets:")
        print("-" * 50)
        for name, path in self.voice_loop.assets.existing_paths().items():
            print(f"  {name}: {path}")
        
        wavs = self.voice_loop.assets.reference_wavs()
        print(f"  reference_wavs: {len(wavs)} files available")
        if wavs:
            print(f"    First: {wavs[0].name}")
            print(f"    Using for voice cloning: {self.voice_loop.assets.preferred_reference_wav()}")
        print()
    
    def _show_memory(self) -> None:
        """Show recent voice memories."""
        memories = self.memory_store.get_recent_memories(limit=5)
        
        print("\nRecent Voice Memories:")
        print("-" * 50)
        if not memories:
            print("  No memories yet. Start a conversation!")
        else:
            for mem in memories:
                timestamp = mem.timestamp.strftime("%Y-%m-%d %H:%M:%S") if mem.timestamp else "Unknown"
                marker = "⭐" if mem.important else "  "
                print(f"{marker} [{timestamp}]")
                print(f"    You: {mem.user_input[:60]}")
                print(f"    Isla: {mem.isla_response[:60]}...")
                if mem.emotion_detected:
                    print(f"    Emotion: {mem.emotion_detected}")
        print()
    
    def _show_stats(self) -> None:
        """Show session statistics."""
        stats = self.memory_store.get_memory_summary()
        
        print("\nSession Statistics:")
        print("-" * 50)
        print(f"  Turns this session: {self.stats['turns']}")
        print(f"  Input characters: {self.stats['total_input_chars']}")
        print(f"  Response characters: {self.stats['total_response_chars']}")
        print(f"  Total speak time: {self.stats['total_speak_time']:.2f}s")
        print(f"\nMemory Store Statistics:")
        print(f"  Total memories: {stats['total_memories']}")
        print(f"  Important memories: {stats['important_count']}")
        print()
    
    def _show_important(self) -> None:
        """Show marked important memories."""
        memories = self.memory_store.get_important_memories(limit=10)
        
        print("\nImportant Voice Memories:")
        print("-" * 50)
        if not memories:
            print("  No important memories marked yet.")
        else:
            for mem in memories:
                timestamp = mem.timestamp.strftime("%Y-%m-%d %H:%M:%S") if mem.timestamp else "Unknown"
                print(f"  [{timestamp}]")
                print(f"    You: {mem.user_input[:60]}")
                print(f"    Isla: {mem.isla_response[:60]}...")
                if mem.notes:
                    print(f"    Notes: {mem.notes}")
        print()
    
    def run(self) -> None:
        """Run the interactive loop."""
        print("\n" + "=" * 50)
        print("Isla Interactive Voice Loop")
        print("=" * 50)
        print("Type /help for commands or just start talking!\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == "/quit":
                    print("Goodbye!")
                    break
                elif user_input.lower() == "/help":
                    self._show_help()
                    continue
                elif user_input.lower() == "/assets":
                    self._show_assets()
                    continue
                elif user_input.lower() == "/memory":
                    self._show_memory()
                    continue
                elif user_input.lower() == "/stats":
                    self._show_stats()
                    continue
                elif user_input.lower() == "/important":
                    self._show_important()
                    continue
                
                # Process normal input
                self.stats["turns"] += 1
                self.stats["total_input_chars"] += len(user_input)
                
                # Generate response
                response = self.responder(user_input)
                if response:
                    self.stats["total_response_chars"] += len(response)
                    print(f"Isla: {response}")
                    
                    # Attempt to speak (may fail if TTS not available)
                    try:
                        start_time = time.time()
                        self.voice_loop.speak(response)
                        self.stats["total_speak_time"] += time.time() - start_time
                    except Exception as e:
                        print(f"  [TTS unavailable: {type(e).__name__}]")
                    
                    # Save to memory
                    memory = VoiceMemory(
                        user_input=user_input,
                        isla_response=response,
                        important=False,
                    )
                    mem_id = self.memory_store.save_memory(memory)
                    print(f"  [Memory saved: #{mem_id}]")
                    
            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"Error: {type(e).__name__}: {e}")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the interactive loop."""
    argv = list(sys.argv[1:]) if argv is None else argv
    
    use_mic = "--mic" in argv
    
    try:
        loop = InteractiveVoiceLoop(use_mic=use_mic)
        loop.run()
        return 0
    except Exception as e:
        print(f"Failed to start interactive loop: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
