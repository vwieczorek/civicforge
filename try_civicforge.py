#!/usr/bin/env python3
"""
CivicForge Interactive Demo - Experience civic engagement through conversation

This is the main entry point for trying CivicForge. It starts both the API server
and an interactive CLI client for a complete conversational experience.
"""

import os
import sys
import time
import subprocess
import signal
import requests
from datetime import datetime

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class CivicForgeDemo:
    """Interactive demo client for CivicForge"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.session_id = None
        self.server_process = None
        
    def start_server(self):
        """Start the API server in the background"""
        print("🚀 Starting CivicForge API server...")
        
        # Set up environment
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))
        
        # Start server
        self.server_process = subprocess.Popen(
            [sys.executable, '-m', 'src.api.main'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for server to be ready
        for i in range(10):
            try:
                response = requests.get(f"{self.base_url}/health", timeout=1)
                if response.status_code == 200:
                    print("✅ Server is ready!\n")
                    return True
            except requests.exceptions.ConnectionError:
                time.sleep(1)
            except Exception as e:
                print(f"⚠️  Unexpected error during server health check: {e}")
                time.sleep(1)
        
        print("❌ Server failed to start")
        return False
    
    def stop_server(self):
        """Stop the API server"""
        if self.server_process:
            print("\n🛑 Shutting down server...")
            self.server_process.terminate()
            self.server_process.wait()
    
    def send_message(self, message):
        """Send a message to the API and get response"""
        data = {
            "message": message,
            "session_id": self.session_id
        }
        
        try:
            response = requests.post(f"{self.base_url}/api/conversation", json=data)
            if response.status_code == 200:
                result = response.json()
                self.session_id = result['session_id']
                return result['response'], result.get('gathered_info', {})
            else:
                return "Sorry, I couldn't process that.", {}
        except requests.exceptions.RequestException as e:
            return f"Error communicating with server: {e}", {}
        except Exception as e:
            return f"Unexpected error: {e}", {}
    
    def show_welcome(self):
        """Display welcome message and instructions"""
        print("🏛️  Welcome to CivicForge - Your Civic Compass")
        print("=" * 50)
        print("\nI'm here to help you connect with your community.")
        print("You can:")
        print("  • Offer your skills and time to help others")
        print("  • Find volunteer opportunities that match your interests")
        print("  • Request help for community projects")
        print("\nJust tell me how you'd like to get involved!\n")
        print("(Type 'examples' to see conversation starters, 'quit' to exit)\n")
    
    def show_examples(self):
        """Show example conversations"""
        print("\n💡 Try saying something like:")
        print("  • \"I want to volunteer to teach programming\"")
        print("  • \"I have free time on weekends and want to help\"")
        print("  • \"We need volunteers for our community garden\"")
        print("  • \"I can cook and would like to help at a food bank\"")
        print("  • \"Show me volunteer opportunities near me\"\n")
    
    def run_interactive_session(self):
        """Run the interactive conversation loop"""
        self.show_welcome()
        
        # Check if we have some demo opportunities
        self._seed_demo_data()
        
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() == 'quit':
                    print("\n👋 Thanks for trying CivicForge! Together we build stronger communities.")
                    break
                elif user_input.lower() == 'examples':
                    self.show_examples()
                    continue
                elif user_input.lower() == 'reset':
                    self.session_id = None
                    print("🔄 Starting a new conversation...\n")
                    continue
                
                # Send message to API
                response, info = self.send_message(user_input)
                
                # Display response
                print(f"\nCivic Compass: {response}")
                
                # Show any gathered information (for demo transparency)
                if info and info.get('skills'):
                    print(f"  [Detected skills: {', '.join(info['skills'])}]")
                if info and info.get('times'):
                    times = [f"{t.get('day', 'any day')} {t.get('period', '')}" for t in info['times']]
                    print(f"  [Available times: {', '.join(times)}]")
                
                print()  # Extra line for readability
                
            except KeyboardInterrupt:
                print("\n\n👋 Thanks for trying CivicForge!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Let's try again...\n")
    
    def _seed_demo_data(self):
        """Create some demo opportunities for a better first experience"""
        opportunities = [
            {
                "title": "Teach Kids Programming",
                "description": "Help teach Python and Scratch to children ages 8-12 at our weekend code club",
                "organization": "Code for Kids",
                "skills_needed": ["teaching", "programming", "python"],
                "location": "Community Center",
                "time_commitment": {"day": "saturday", "period": "morning", "duration": "2 hours"},
                "min_volunteers": 2
            },
            {
                "title": "Community Garden Helper",
                "description": "Join us in maintaining and expanding our neighborhood garden",
                "organization": "Green Thumbs Collective",
                "skills_needed": ["gardening", "landscaping"],
                "location": "Riverside Park",
                "time_commitment": {"day": "sunday", "period": "afternoon", "duration": "3 hours"},
                "min_volunteers": 5
            },
            {
                "title": "Food Bank Distribution",
                "description": "Help sort and distribute food to families in need",
                "organization": "Community Food Network",
                "skills_needed": ["organization", "physical labor"],
                "location": "Food Bank Warehouse",
                "time_commitment": {"day": "saturday", "period": "morning", "duration": "4 hours"},
                "min_volunteers": 10
            }
        ]
        
        # Create demo opportunities
        print("🌱 Seeding demo opportunities...")
        for opp in opportunities:
            try:
                response = requests.post(f"{self.base_url}/api/opportunities", json=opp, timeout=1)
                if response.status_code != 200:
                    print(f"⚠️  Warning: Failed to create demo opportunity '{opp['title']}' (status: {response.status_code})")
            except requests.exceptions.RequestException as e:
                print(f"⚠️  Warning: Failed to seed demo opportunity '{opp.get('title', 'N/A')}'. Error: {e}")
            except Exception as e:
                print(f"⚠️  Warning: Unexpected error while seeding '{opp.get('title', 'N/A')}': {e}")
    
    def run(self):
        """Main entry point"""
        # Start server
        if not self.start_server():
            return
        
        try:
            # Run interactive session
            self.run_interactive_session()
        finally:
            # Always stop server
            self.stop_server()

def main():
    """Run the CivicForge demo"""
    # Check Python version
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ is required")
        sys.exit(1)
    
    # Check if we're in the right directory
    if not os.path.exists('src/api/main.py'):
        print("❌ Please run this script from the CivicForge root directory")
        sys.exit(1)
    
    # Run the demo
    demo = CivicForgeDemo()
    demo.run()

if __name__ == "__main__":
    main()