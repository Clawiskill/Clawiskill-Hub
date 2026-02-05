
import sys
import os
import re

def analyze_composition(text):
    trimmed_text = text.strip()
    char_count = len(trimmed_text)
    return char_count

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python cli.py [file_path]")
        print("If no file path is provided, reads from standard input.")
        print("Example 1: python cli.py essay.txt")
        print("Example 2: echo \"作文内容\" | python cli.py")
        sys.exit(0)
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        
        try:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)
    else:
        content = sys.stdin.read()
        if not content.strip():
            print("Error: No content provided")
            sys.exit(1)

    char_count = analyze_composition(content)
    print("=== Composition Analysis ===")
    print(f"Character Count: {char_count}")
    print("Note: Character count includes all text content, including punctuation and spaces.")

if __name__ == "__main__":
    main()
