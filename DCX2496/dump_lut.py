# ("parameter", [("7bits", "8bit", "9bit")])
# 7bits: Byte containing 7bits of information, 8th bit is always 0
# 8bit: Byte just containing the 8th bit... stupid but yes...
# 9bit: Byte (only one bit of it) representing the 9th bit of information

# Lookup table
dump_lut = {
    "gain": [
        (),
        (0x92, (0x94, 5), (0x93, 0)),  # A
        (0x120, (0x124, 3), (0x121, 0)),  # B
        (0x1AE, (0x1B4, 1), (0x1AF, 0)),  # C
        (0x23B, (0x23C, 6), (0x23D, 0)),  # SUM
        (0x2C9, (0x2CC, 4), (0x2CA, 0)),  # 1
        (0x372, (0x374, 5), (0x373, 0)),  # 2
        (0x42A, (0x42B, 6), (0x42C, 0)),  # 3
        (0x4D4, (0x4DB, 0), (0x4D5, 0)),  # 4
        (0x57D, (0x583, 1), (0x57E, 0)),  # 5
        (0x626, (0x62B, 2), (0x627, 0)),  # 6
    ],
}
