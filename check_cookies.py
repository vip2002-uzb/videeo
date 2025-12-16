
import os

try:
    with open("cookies.txt", "rb") as f:
        content = f.read(100)
        print(f"First 100 bytes: {content}")
        try:
            print(f"Decoded (utf-8): {content.decode('utf-8')}")
        except:
            print("Decoded (utf-8): FAILED")
            
        try:
            print(f"Decoded (utf-16): {content.decode('utf-16')}")
        except:
            print("Decoded (utf-16): FAILED")
            
except Exception as e:
    print(f"Error reading file: {e}")
