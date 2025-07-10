#!/usr/bin/env python3
"""
ElevenLabs Audio Generator for CivicForge SSML Scripts

Generates high-quality audio from SSML files using ElevenLabs API.
Handles batch processing and concatenation of audio chunks.

Usage:
    python generate_audio.py [--voice-id VOICE_ID] [--list-voices]
    
Environment Variables:
    ELEVENLABS_API_KEY - Your ElevenLabs API key (required)
"""

import os
import sys
import json
import time
import argparse
import requests
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

class ElevenLabsGenerator:
    def __init__(self):
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
        
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Default voice settings (as recommended in scripts)
        self.voice_settings = {
            "stability": 0.75,
            "similarity_boost": 0.85,
            "style": 0.3,
            "use_speaker_boost": True
        }
        
        self.model_id = "eleven_v3"  # As recommended in scripts
        
    def list_voices(self) -> List[Dict]:
        """List available voices from ElevenLabs."""
        try:
            response = requests.get(f"{self.base_url}/voices", headers=self.headers)
            response.raise_for_status()
            
            voices = response.json()["voices"]
            print("\n🎙️  Available ElevenLabs Voices:")
            print("=" * 50)
            
            for voice in voices:
                print(f"Name: {voice['name']}")
                print(f"ID: {voice['voice_id']}")
                print(f"Category: {voice.get('category', 'N/A')}")
                print(f"Description: {voice.get('description', 'No description')}")
                print("-" * 30)
            
            return voices
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching voices: {e}")
            return []
    
    def get_recommended_voice(self) -> Optional[str]:
        """Get a recommended voice ID based on script suggestions."""
        voices = self.list_voices()
        
        # Look for recommended voices from the script
        recommended_names = ['Adam', 'Charlotte', 'Daniel', 'Lily']
        
        for voice in voices:
            if voice['name'] in recommended_names:
                print(f"✅ Found recommended voice: {voice['name']} ({voice['voice_id']})")
                return voice['voice_id']
        
        # Fallback to first available voice
        if voices:
            fallback = voices[0]
            print(f"🔄 Using fallback voice: {fallback['name']} ({fallback['voice_id']})")
            return fallback['voice_id']
        
        return None
    
    def generate_audio_chunk(self, ssml_text: str, voice_id: str, output_path: str) -> bool:
        """Generate audio for a single SSML chunk."""
        
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        data = {
            "text": ssml_text,
            "model_id": self.model_id,
            "voice_settings": self.voice_settings
        }
        
        try:
            print(f"🎵 Generating: {os.path.basename(output_path)}")
            response = requests.post(url, json=data, headers=self.headers)
            response.raise_for_status()
            
            # Save audio file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Generated: {output_path} ({len(response.content)} bytes)")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error generating {output_path}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    print(f"   Details: {error_details}")
                except:
                    print(f"   Response: {e.response.text}")
            return False
    
    def process_script_chunks(self, script_name: str, voice_id: str, output_dir: str) -> List[str]:
        """Process all chunks for a single script."""
        
        ssml_dir = Path("ssml_output")
        chunks = sorted(ssml_dir.glob(f"{script_name}_chunk_*.ssml"))
        
        if not chunks:
            print(f"❌ No SSML chunks found for {script_name}")
            return []
        
        print(f"\n🎬 Processing {script_name} ({len(chunks)} chunks)")
        
        audio_files = []
        
        for chunk_file in chunks:
            # Read SSML content
            with open(chunk_file, 'r', encoding='utf-8') as f:
                ssml_content = f.read()
            
            # Generate output filename
            audio_filename = chunk_file.stem.replace('_chunk_', '_audio_') + '.mp3'
            audio_path = os.path.join(output_dir, audio_filename)
            
            # Generate audio
            if self.generate_audio_chunk(ssml_content, voice_id, audio_path):
                audio_files.append(audio_path)
                time.sleep(1)  # Rate limiting - be nice to the API
            else:
                print(f"❌ Failed to generate {audio_filename}")
        
        return audio_files
    
    def concatenate_audio(self, audio_files: List[str], output_path: str) -> bool:
        """Concatenate audio files using ffmpeg."""
        
        if not audio_files:
            print("❌ No audio files to concatenate")
            return False
        
        # Check if ffmpeg is available
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  ffmpeg not found. Please install ffmpeg to concatenate audio files.")
            print("   Individual chunk files are available in the audio_output directory.")
            return False
        
        # Create file list for ffmpeg
        filelist_path = output_path.replace('.mp3', '_filelist.txt')
        
        with open(filelist_path, 'w') as f:
            for audio_file in audio_files:
                f.write(f"file '{os.path.abspath(audio_file)}'\n")
        
        try:
            print(f"🔗 Concatenating {len(audio_files)} audio files...")
            
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', filelist_path,
                '-c', 'copy',
                '-y',  # Overwrite output file
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Created complete audio: {output_path}")
                
                # Clean up filelist
                os.remove(filelist_path)
                return True
            else:
                print(f"❌ ffmpeg error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error concatenating audio: {e}")
            return False
    
    def generate_all_scripts(self, voice_id: str) -> None:
        """Generate audio for all available scripts."""
        
        # Create output directory
        output_dir = "audio_output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Script names to process
        scripts = [
            "AI_FIRST_CIVICFORGE_AUDIO_SCRIPT",
            "AI_FIRST_CIVICFORGE_AUDIO_SCRIPT_ACADEMIC", 
            "AI_FIRST_CIVICFORGE_AUDIO_SCRIPT_VIRAL"
        ]
        
        print(f"\n🚀 Starting audio generation with voice ID: {voice_id}")
        print(f"📁 Output directory: {output_dir}")
        
        for script_name in scripts:
            print(f"\n{'='*60}")
            
            # Generate chunks
            audio_files = self.process_script_chunks(script_name, voice_id, output_dir)
            
            if audio_files:
                # Concatenate into complete file
                complete_audio_path = os.path.join(output_dir, f"{script_name}_COMPLETE.mp3")
                self.concatenate_audio(audio_files, complete_audio_path)
            
            print(f"✅ Completed: {script_name}")
        
        print(f"\n🎉 Audio generation complete!")
        print(f"📁 Files saved to: {output_dir}/")
        
        # List generated files
        print(f"\n📋 Generated Files:")
        for file in sorted(Path(output_dir).glob("*.mp3")):
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"   {file.name} ({size_mb:.1f} MB)")

def main():
    parser = argparse.ArgumentParser(description='Generate audio from SSML using ElevenLabs API')
    parser.add_argument('--voice-id', help='ElevenLabs voice ID to use')
    parser.add_argument('--list-voices', action='store_true', help='List available voices and exit')
    parser.add_argument('--model', default='eleven_v3', help='ElevenLabs model to use (default: eleven_v3)')
    
    args = parser.parse_args()
    
    try:
        generator = ElevenLabsGenerator()
        generator.model_id = args.model
        
        if args.list_voices:
            generator.list_voices()
            return 0
        
        # Get voice ID
        voice_id = args.voice_id
        if not voice_id:
            print("🔍 No voice ID specified, finding recommended voice...")
            voice_id = generator.get_recommended_voice()
            
            if not voice_id:
                print("❌ No voices available. Please check your API key.")
                return 1
        
        # Generate all audio
        generator.generate_all_scripts(voice_id)
        
        return 0
        
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Make sure to set: export ELEVENLABS_API_KEY=your_api_key")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())