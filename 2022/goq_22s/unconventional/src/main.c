#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <x86intrin.h>

typedef uint8_t Block[4][4];

const Block key = {{0x21, 0xe5, 0x88, 0xac}, {0xbb, 0xb0, 0x97, 0xea}, {0x16, 0x42, 0x03, 0x0b}, {0x9b, 0xd2, 0x5c, 0x6c}};
const uint8_t sbox[0x100] = {  // ARIA S-box #2
    0xe2, 0x4e, 0x54, 0xfc, 0x94, 0xc2, 0x4a, 0xcc, 0x62, 0x0d, 0x6a, 0x46, 0x3c, 0x4d, 0x8b, 0xd1,
    0x5e, 0xfa, 0x64, 0xcb, 0xb4, 0x97, 0xbe, 0x2b, 0xbc, 0x77, 0x2e, 0x03, 0xd3, 0x19, 0x59, 0xc1,
    0x1d, 0x06, 0x41, 0x6b, 0x55, 0xf0, 0x99, 0x69, 0xea, 0x9c, 0x18, 0xae, 0x63, 0xdf, 0xe7, 0xbb,
    0x00, 0x73, 0x66, 0xfb, 0x96, 0x4c, 0x85, 0xe4, 0x3a, 0x09, 0x45, 0xaa, 0x0f, 0xee, 0x10, 0xeb,
    0x2d, 0x7f, 0xf4, 0x29, 0xac, 0xcf, 0xad, 0x91, 0x8d, 0x78, 0xc8, 0x95, 0xf9, 0x2f, 0xce, 0xcd,
    0x08, 0x7a, 0x88, 0x38, 0x5c, 0x83, 0x2a, 0x28, 0x47, 0xdb, 0xb8, 0xc7, 0x93, 0xa4, 0x12, 0x53,
    0xff, 0x87, 0x0e, 0x31, 0x36, 0x21, 0x58, 0x48, 0x01, 0x8e, 0x37, 0x74, 0x32, 0xca, 0xe9, 0xb1,
    0xb7, 0xab, 0x0c, 0xd7, 0xc4, 0x56, 0x42, 0x26, 0x07, 0x98, 0x60, 0xd9, 0xb6, 0xb9, 0x11, 0x40,
    0xec, 0x20, 0x8c, 0xbd, 0xa0, 0xc9, 0x84, 0x04, 0x49, 0x23, 0xf1, 0x4f, 0x50, 0x1f, 0x13, 0xdc,
    0xd8, 0xc0, 0x9e, 0x57, 0xe3, 0xc3, 0x7b, 0x65, 0x3b, 0x02, 0x8f, 0x3e, 0xe8, 0x25, 0x92, 0xe5,
    0x15, 0xdd, 0xfd, 0x17, 0xa9, 0xbf, 0xd4, 0x9a, 0x7e, 0xc5, 0x39, 0x67, 0xfe, 0x76, 0x9d, 0x43,
    0xa7, 0xe1, 0xd0, 0xf5, 0x68, 0xf2, 0x1b, 0x34, 0x70, 0x05, 0xa3, 0x8a, 0xd5, 0x79, 0x86, 0xa8,
    0x30, 0xc6, 0x51, 0x4b, 0x1e, 0xa6, 0x27, 0xf6, 0x35, 0xd2, 0x6e, 0x24, 0x16, 0x82, 0x5f, 0xda,
    0xe6, 0x75, 0xa2, 0xef, 0x2c, 0xb2, 0x1c, 0x9f, 0x5d, 0x6f, 0x80, 0x0a, 0x72, 0x44, 0x9b, 0x6c,
    0x90, 0x0b, 0x5b, 0x33, 0x7d, 0x5a, 0x52, 0xf3, 0x61, 0xa1, 0xf7, 0xb0, 0xd6, 0x3f, 0x7c, 0x6d,
    0xed, 0x14, 0xe0, 0xa5, 0x3d, 0x22, 0xb3, 0xf8, 0x89, 0xde, 0x71, 0x1a, 0xaf, 0xba, 0xb5, 0x81
};
const uint8_t chain[0x10] = {
    0x3, 0xc, 0xb, 0x5,
    0x8, 0x4, 0x7, 0xd,
    0xf, 0x0, 0x6, 0xe,
    0x9, 0x1, 0xa, 0x2
};
const Block answer[3] = {
    {
        {0x89, 0xb4, 0xf7, 0x8f},
        {0xe1, 0x8b, 0x29, 0x0d},
        {0x37, 0xb1, 0x56, 0xc0},
        {0xf0, 0x75, 0x42, 0x8e},
    },
    {
        {0x1c, 0xc4, 0x2d, 0x1d},
        {0xd9, 0x2e, 0xd4, 0x83},
        {0x55, 0xee, 0x6b, 0xad},
        {0x53, 0x40, 0x79, 0x65},
    },
    {
        {0x07, 0x9a, 0x0a, 0xb2},
        {0x9f, 0x82, 0x99, 0x10},
        {0xdf, 0x45, 0x22, 0x6b},
        {0x50, 0xdb, 0x0b, 0x40},
    },
}; // x86-64_c4ll1ng_c0nv3nt10n_0f_th3_m!rr0r_univers3

#ifndef NDEBUG
void DUMPBLOCK(Block block);
#endif
void SubBytes(Block block);
void RotateBlock(Block block);
void Twiddle(Block block);
void AddRoundKey(Block block, Block key);

int main(void)
{
    Block input[3];
    char buf[0x31] = {0,};

    if (fgets(buf, 0x31, stdin) != buf)
        goto FAIL;
    buf[strcspn(buf, "\n")] = '\0';
    memcpy(input, buf, sizeof(input));

    for (int i = 0; i < 3; i++) {
        Block round_key;
        memcpy(round_key, key, sizeof(round_key));
        for (int j = 0; j < 0xc0ff33; j++) {
            SubBytes(input[i]);
            RotateBlock(input[i]);
            Twiddle(input[i]);
            AddRoundKey(input[i], round_key);
        }
#ifndef NDEBUG
        DUMPBLOCK(input[i]);
#endif
    }

    if (!memcmp(answer, input, sizeof(answer)))
        printf("GoN{%s}\n", buf);
    else
FAIL:
        printf("Nah...\n");
    
    return 0;
}

#ifndef NDEBUG
void DUMPBLOCK(Block block)
{
    printf("{\n");
    for (int y = 0; y < 4; y++)
        printf("    {0x%02x, 0x%02x, 0x%02x, 0x%02x},\n", block[y][0], block[y][1], block[y][2], block[y][3]);
    printf("},\n");
}
#endif

void SubBytes(Block block)
{
    // S-box substitution
    for (int y = 0; y < 4; y++)
        for (int x = 0; x < 4; x++)
            block[y][x] = sbox[block[y][x]];
}

void RotateBlock(Block block)
{
    // rotate downwards by 0, 1, 2, 3
    Block tmp;
    for (int x = 0; x < 4; x++)
        for (int y = 0; y < 4; y++)
            tmp[y][x] = block[(y+4-x)%4][x];
    memcpy(block, tmp, sizeof(tmp));
}

void Twiddle(Block block)
{
    // Invert(Xor) -> Add -> Rotate
    for (int i = 0, idx = 0; i < 0x10; i++, idx = chain[idx])
        block[idx/4][idx%4] ^= (chain[idx] << 4) | chain[idx];
    
    for (int i = 0, idx = 0; i < 0x10; i++, idx = chain[idx])
        block[chain[idx]/4][chain[idx]%4] += block[idx/4][idx%4];
    
    for (int i = 0, idx = 0; i < 0x10; i++, idx = chain[idx])
        block[idx/4][idx%4] = __rolb(block[idx/4][idx%4], chain[idx] % 8);
}

void AddRoundKey(Block block, Block key)
{
    // XOR with current round key
    for (int y = 0; y < 4; y++)
        for (int x = 0; x < 4; x++)
            block[y][x] ^= key[y][x];

    // (Next key) = (Current key) |> SubBytes |> RotateBlock |> Twiddle
    SubBytes(key);
    RotateBlock(key);
    Twiddle(key);
}
