import hashlib

def hash_string(input_str: str) -> str:
    return hashlib.sha256(input_str.encode('utf-8')).hexdigest()

# Example usage
if __name__ == "__main__":
    s = "John"
    print(hash_string(s))