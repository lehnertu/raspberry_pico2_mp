def extract_bit_field(data:bytearray, offset:int, num_bits:int) -> int:
    """
    extract a range of bits from a byte array.
    offset is the index of the first bit (LSB) to be used
    num_bits is the number of bits to be extracted
    returned is the resulting bit array as an integer number.
    """
    # transform the array into a big int
    big_int = int.from_bytes(data, "big")
    # shift right to move the start bit to the LSB position
    shifted = big_int >> offset
    # compute the bitmask selecting the correct number of bits
    bitmask = (1 << num_bits) - 1
    return shifted & bitmask