#!/usr/bin/env python3
"""
CivicForge Audio Script to SSML Converter

Converts Markdown audio scripts to optimized SSML format for ElevenLabs TTS.
Handles proper chunking, voice direction tags, and markup optimization.

Usage:
    python convert_to_ssml.py input.md [output_directory]
"""

import re
import sys
import os
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

class SSMLConverter:
    def __init__(self):
        # ElevenLabs character limits per model
        self.character_limits = {
            'eleven_v3': 10000,
            'eleven_multilingual_v2': 10000,
            'eleven_flash_v2_5': 40000,
            'eleven_turbo_v2_5': 40000
        }
        
        # Default to Eleven v3 as recommended in scripts
        self.default_model = 'eleven_v3'
        self.chunk_size = self.character_limits[self.default_model] - 500  # Safety margin
        
    def parse_voice_directions(self, text: str) -> str:
        """Convert voice direction markdown to SSML markup."""
        
        # Convert [pause] to break tags
        text = re.sub(r'\[pause\]', '<break strength="medium"/>', text)
        text = re.sub(r'\[longer pause\]', '<break strength="strong"/>', text)
        
        # Convert [emphasized] to emphasis tags
        text = re.sub(r'\[emphasized\]', '<emphasis level="strong">', text)
        text = re.sub(r'\[/emphasized\]', '</emphasis>', text)
        
        # Handle inline emphasis with content
        def replace_emphasized(match):
            content = match.group(1)
            return f'<emphasis level="strong">{content}</emphasis>'
        
        text = re.sub(r'\[emphasized\]\s*([^[]+?)(?=\s*\[|$)', replace_emphasized, text)
        
        # Convert mood/tone directions
        mood_mappings = {
            r'\[cheerfully\]': '<prosody rate="1.1" pitch="+5%">',
            r'\[quietly\]': '<prosody volume="soft">',
            r'\[whispers\]': '<prosody volume="x-soft" rate="0.9">',
            r'\[normal\]': '</prosody>',
            r'\[softly\]': '<prosody volume="soft">',
            r'\[warmly\]': '<prosody pitch="+3%" rate="0.95">',
            r'\[serious tone\]': '<prosody pitch="-3%" rate="0.9">',
            r'\[nervously\]': '<prosody rate="1.1" pitch="+2%">',
            r'\[hopefully\]': '<prosody pitch="+5%" rate="1.05">',
            r'\[playfully\]': '<prosody pitch="+8%" rate="1.1">',
            r'\[triumphantly\]': '<prosody pitch="+10%" rate="1.1" volume="loud">',
            r'\[dramatically\]': '<prosody pitch="+5%" rate="0.8">',
            r'\[deliberately\]': '<prosody rate="0.8">',
            r'\[thoughtfully\]': '<prosody rate="0.9" pitch="-2%">',
            r'\[intimately\]': '<prosody volume="soft" rate="0.9">',
            r'\[emotionally\]': '<prosody pitch="+3%" rate="0.95">',
            r'\[gently\]': '<prosody volume="soft" rate="0.9">',
        }
        
        for pattern, replacement in mood_mappings.items():
            text = re.sub(pattern, replacement, text)
        
        # Convert special effects
        text = re.sub(r'\[sighs\]', '<break time="500ms"/>', text)
        text = re.sub(r'\[record scratch\]', '<break time="800ms"/>', text)
        
        return text
    
    def clean_markdown_formatting(self, text: str) -> str:
        """Convert markdown formatting to SSML equivalents."""
        
        # Convert **bold** to strong emphasis
        text = re.sub(r'\*\*([^*]+?)\*\*', r'<emphasis level="strong">\1</emphasis>', text)
        
        # Convert *italic* to moderate emphasis  
        text = re.sub(r'\*([^*]+?)\*', r'<emphasis level="moderate">\1</emphasis>', text)
        
        # Remove markdown headers but keep content
        text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)
        
        # Convert horizontal rules to longer breaks
        text = re.sub(r'^---+$', '<break time="2s"/>', text, flags=re.MULTILINE)
        
        # Remove production notes and stage directions in brackets (but keep voice directions)
        text = re.sub(r'\*\[([^\]]+)\]\*', '', text)
        text = re.sub(r'^\*\*[^*]+\*\*:\s*$', '', text, flags=re.MULTILINE)
        
        return text
    
    def add_pronunciation_guides(self, text: str) -> str:
        """Add pronunciation guides for technical terms and proper nouns."""
        
        # Technical terms that might be mispronounced
        pronunciations = {
            'CivicForge': '<phoneme alphabet="ipa" ph="ˈsɪvɪk fɔrdʒ">CivicForge</phoneme>',
            'UI': '<say-as interpret-as="characters">UI</say-as>',
            'AI': '<say-as interpret-as="characters">AI</say-as>',
            'API': '<say-as interpret-as="characters">API</say-as>',
            'PDF': '<say-as interpret-as="characters">PDF</say-as>',
            'SMS': '<say-as interpret-as="characters">SMS</say-as>',
            'Karpathy': '<phoneme alphabet="ipa" ph="kɑrˈpæθi">Karpathy</phoneme>',
        }
        
        for word, pronunciation in pronunciations.items():
            # Only replace if not already inside SSML tags
            pattern = rf'\b{re.escape(word)}\b(?![^<]*>)'
            text = re.sub(pattern, pronunciation, text)
        
        return text
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks suitable for ElevenLabs API."""
        
        # Split by double newlines (paragraph breaks) first
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # Check if adding this paragraph would exceed chunk size
            test_chunk = current_chunk + '\n\n' + paragraph if current_chunk else paragraph
            
            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If single paragraph is too long, split by sentences
                if len(paragraph) > self.chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    current_chunk = ""
                    
                    for sentence in sentences:
                        test_sentence_chunk = current_chunk + ' ' + sentence if current_chunk else sentence
                        
                        if len(test_sentence_chunk) <= self.chunk_size:
                            current_chunk = test_sentence_chunk
                        else:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = sentence
                    
                else:
                    current_chunk = paragraph
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def wrap_in_speak_tags(self, text: str) -> str:
        """Wrap text in SSML speak tags with proper attributes."""
        
        # Clean up any malformed tags or extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Ensure proper closing of any unclosed prosody tags
        open_prosody = text.count('<prosody')
        close_prosody = text.count('</prosody>')
        
        if open_prosody > close_prosody:
            text += '</prosody>' * (open_prosody - close_prosody)
        
        return f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">\n{text}\n</speak>'
    
    def convert_file(self, input_path: str, output_dir: str = None) -> List[str]:
        """Convert a markdown audio script to SSML chunks."""
        
        # Read input file
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract content sections (skip metadata and production notes)
        content_start = content.find('## Opening:') or content.find('## Episode 1:') or content.find('## Chapter 1:')
        if content_start == -1:
            content_start = 0
        
        content_end = content.find('## Production Notes') or content.find('---\n\n*[End of script]*') or len(content)
        
        main_content = content[content_start:content_end]
        
        # Apply all transformations
        processed_text = self.parse_voice_directions(main_content)
        processed_text = self.clean_markdown_formatting(processed_text)
        processed_text = self.add_pronunciation_guides(processed_text)
        
        # Remove extra whitespace and empty lines
        processed_text = re.sub(r'\n\s*\n\s*\n', '\n\n', processed_text)
        processed_text = processed_text.strip()
        
        # Chunk the text
        chunks = self.chunk_text(processed_text)
        
        # Wrap each chunk in speak tags
        ssml_chunks = [self.wrap_in_speak_tags(chunk) for chunk in chunks]
        
        # Save chunks to output files
        if output_dir is None:
            output_dir = os.path.dirname(input_path)
        
        os.makedirs(output_dir, exist_ok=True)
        
        input_name = Path(input_path).stem
        output_files = []
        
        for i, chunk in enumerate(ssml_chunks, 1):
            output_file = os.path.join(output_dir, f"{input_name}_chunk_{i:02d}.ssml")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(chunk)
            
            output_files.append(output_file)
            print(f"Created: {output_file} ({len(chunk)} characters)")
        
        # Create a metadata file with chunk information
        metadata_file = os.path.join(output_dir, f"{input_name}_metadata.txt")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(f"Original file: {input_path}\n")
            f.write(f"Total chunks: {len(ssml_chunks)}\n")
            f.write(f"Recommended model: {self.default_model}\n")
            f.write(f"Character limit used: {self.chunk_size}\n\n")
            
            for i, chunk in enumerate(ssml_chunks, 1):
                f.write(f"Chunk {i:02d}: {len(chunk)} characters\n")
        
        print(f"Created metadata: {metadata_file}")
        
        return output_files

def main():
    parser = argparse.ArgumentParser(description='Convert Markdown audio scripts to SSML for ElevenLabs')
    parser.add_argument('input_file', help='Input markdown file')
    parser.add_argument('output_dir', nargs='?', help='Output directory (default: same as input)')
    parser.add_argument('--model', choices=['eleven_v3', 'eleven_multilingual_v2', 'eleven_flash_v2_5', 'eleven_turbo_v2_5'], 
                       default='eleven_v3', help='Target ElevenLabs model (affects chunking)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        return 1
    
    converter = SSMLConverter()
    converter.default_model = args.model
    converter.chunk_size = converter.character_limits[args.model] - 500
    
    try:
        output_files = converter.convert_file(args.input_file, args.output_dir)
        print(f"\nSuccessfully converted '{args.input_file}' to {len(output_files)} SSML chunks")
        print("Ready for ElevenLabs TTS generation!")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())