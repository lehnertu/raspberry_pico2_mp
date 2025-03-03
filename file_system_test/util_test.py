from util import *

arr = bytearray([
    0x12, 0x34, 0x56, 0x78,
    0x9A, 0xBC, 0xDE, 0xF0,
    0x11, 0x22, 0x33, 0x44,
    0x55, 0x66, 0x77, 0x88 ])


print(' '.join(f'{byte:02x}' for byte in arr))
print()

res = extract_bit_field(arr,0,8)
print(f"Extracted value arr(0,8): {res} = 0x{res:X}")

res = extract_bit_field(arr,8,8)
print(f"Extracted value arr(8,8): {res} = 0x{res:X}")

res = extract_bit_field(arr,8,5)
print(f"Extracted value arr(8,5): {res} = 0x{res:X}")

res = extract_bit_field(arr,8,2)
print(f"Extracted value arr(8,2): {res} = 0x{res:X}")

res = extract_bit_field(arr,8,1)
print(f"Extracted value arr(8,1): {res} = 0x{res:X}")

res = extract_bit_field(arr,8,16)
print(f"Extracted value arr(8,16): {res} = 0x{res:X}")

res = extract_bit_field(arr,8,10)
print(f"Extracted value arr(8,10): {res} = 0x{res:X}")