from action_executor import ActionExecutor
import time

executor = ActionExecutor()

print("Testing action executor...\n")

# Test Monitor
print("1. Testing Monitor action on web-server...")
result = executor.execute("Monitor", "web-server")
print(f"   Result: {result}\n")
time.sleep(2)

# Test Analyse
print("2. Testing Analyse action on database...")
result = executor.execute("Analyse", "database")
print(f"   Result: {result}\n")
time.sleep(2)

# Test Analyse on attacker (should be clean since nothing malicious yet)
print("3. Testing Analyse action on attacker...")
result = executor.execute("Analyse", "attacker")
print(f"   Result: {result}\n")
time.sleep(2)

# Test Restore
print("4. Testing Restore action on public-web...")
result = executor.execute("Restore", "public-web")
print(f"   Result: {result}\n")
time.sleep(5)

# Test error handling — non-existent container
print("5. Testing error handling (bad container name)...")
result = executor.execute("Analyse", "nonexistent-host")
print(f"   Result: {result}\n")

print("All actions tested!")
