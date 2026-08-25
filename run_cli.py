from src.agent import run_agent

def main():
    print("Welcome to Aster & Row Support. Type 'quit' to exit.")
    messages = []
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break
            
        messages.append({"role": "user", "content": user_input})
        print("\nThinking...")
        
        result = run_agent(messages)
        messages.append({"role": "assistant", "content": result["response"]})
        
        print(f"\nAster & Row: {result['response']}")
        if result["sources"]:
            print(f"\n[Sources: {', '.join(result['sources'])}]")
        if result["handoff"]:
            print("\n[System: Human Handoff Recommended]")

if __name__ == "__main__":
    main()