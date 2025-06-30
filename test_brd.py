from llm_engine.run_local_llm import generate_brd

# Test with a simple function
test_function = '''
def calculate_total(items, tax_rate=0.1):
    """Calculate total price including tax"""
    subtotal = sum(item['price'] * item['quantity'] for item in items)
    tax = subtotal * tax_rate
    return subtotal + tax
'''

print("Testing generate_brd function with codellama:13b...")
result = generate_brd(test_function, "codellama:13b")
print("\n" + "="*50)
print("RESULT:")
print("="*50)
print(result) 