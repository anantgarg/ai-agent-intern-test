import sys
import argparse
from agent import SupportAgent

def main():
    parser = argparse.ArgumentParser(description="Aster & Row AI Support Agent")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    print("Initializing Aster & Row Support Agent...")
    agent = SupportAgent(debug=args.debug)
    print("Agent is ready! Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            
            if not user_input.strip():
                continue
                
            response = agent.chat(user_input)
            print(f"\nAgent: {response}\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n[ERROR] {str(e)}\n")

if __name__ == "__main__":
    main()
