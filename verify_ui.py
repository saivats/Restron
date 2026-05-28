import sys

def verify(filepath, requirements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    missing = []
    for req in requirements:
        req_double = req
        req_single = req.replace('"', "'")
        
        if req_double not in content and req_single not in content:
            missing.append(req)
            
    if missing:
        print(f"FAILED: {filepath} is missing {missing}")
        sys.exit(1)
    else:
        print(f"SUCCESS: {filepath} has all required elements.")

if __name__ == '__main__':
    filepath = sys.argv[1]
    requirements = sys.argv[2:]
    verify(filepath, requirements)
