#include <gtest/gtest.h>
#include "glacierkz_checksum.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

class ChecksumTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(ChecksumTest, CRC32KnownValue) {
    const char *data = "123456789";
    uint32_t crc = gz_crc32(data, strlen(data));
    EXPECT_EQ(crc, (uint32_t)0xCBF43926);
}

TEST_F(ChecksumTest, CRC32Empty) {
    uint32_t crc = gz_crc32("", 0);
    EXPECT_EQ(crc, (uint32_t)0x00000000);
}

TEST_F(ChecksumTest, CRC32SingleByte) {
    uint8_t byte = 'A';
    uint32_t crc = gz_crc32(&byte, 1);
    EXPECT_NE(crc, (uint32_t)0);
}

TEST_F(ChecksumTest, CRC32Incremental) {
    const char *part1 = "Hello, ";
    const char *part2 = "world!";

    uint32_t crc1 = gz_crc32(part1, strlen(part1));
    uint32_t crc2 = gz_crc32_update(crc1, part2, strlen(part2));

    char full[64];
    snprintf(full, sizeof(full), "%s%s", part1, part2);
    uint32_t crc_full = gz_crc32(full, strlen(full));

    EXPECT_EQ(crc2, crc_full);
}

TEST_F(ChecksumTest, SHA256KnownValue) {
    const char *data = "abc";
    uint8_t hash[GZ_SHA256_SIZE];
    gz_sha256(data, strlen(data), hash);

    uint8_t expected[] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x46, 0x9a, 0x54, 0x37, 0x1a, 0x4d, 0x8f, 0x3f,
        0xb1, 0x93, 0x7a, 0x3b, 0x54, 0x54, 0xe5, 0x8c,
        0x3f, 0xd4, 0x20, 0xf3, 0x40, 0x48, 0xb3, 0x4d
    };

    EXPECT_EQ(memcmp(hash, expected, GZ_SHA256_SIZE), 0);
}

TEST_F(ChecksumTest, SHA256Empty) {
    uint8_t hash[GZ_SHA256_SIZE];
    gz_sha256("", 0, hash);

    uint8_t expected[] = {
        0xe3, 0xb0, 0xc4, 0x42, 0x98, 0xfc, 0x1c, 0x14,
        0x9a, 0xfb, 0xf4, 0xdf, 0x85, 0x64, 0xeb, 0x37,
        0x86, 0x79, 0x98, 0xf8, 0xf4, 0x7f, 0x8e, 0xb3,
        0xcb, 0x02, 0x4e, 0x3d, 0x93, 0x76, 0x6e, 0xb3
    };

    EXPECT_EQ(memcmp(hash, expected, GZ_SHA256_SIZE), 0);
}

TEST_F(ChecksumTest, SHA256Incremental) {
    const char *part1 = "Hello, ";
    const char *part2 = "world!";

    gz_sha256_ctx_t ctx;
    gz_sha256_init(&ctx);
    gz_sha256_update(&ctx, part1, strlen(part1));
    gz_sha256_update(&ctx, part2, strlen(part2));

    uint8_t hash1[GZ_SHA256_SIZE];
    gz_sha256_final(&ctx, hash1);

    char full[64];
    snprintf(full, sizeof(full), "%s%s", part1, part2);
    uint8_t hash2[GZ_SHA256_SIZE];
    gz_sha256(full, strlen(full), hash2);

    EXPECT_EQ(memcmp(hash1, hash2, GZ_SHA256_SIZE), 0);
}

TEST_F(ChecksumTest, CRC32FileNotFound) {
    uint32_t crc;
    gz_status_t st = gz_crc32_file("/nonexistent/file.bin", &crc);
    EXPECT_EQ(st, GZ_ERR_NOTFOUND);
}

TEST_F(ChecksumTest, SHA256FileNotFound) {
    uint8_t hash[GZ_SHA256_SIZE];
    gz_status_t st = gz_sha256_file("/nonexistent/file.bin", hash);
    EXPECT_EQ(st, GZ_ERR_NOTFOUND);
}

TEST_F(ChecksumTest, CRC32FileRead) {
    const char *tmpfile = "/tmp/test_crc32.bin";
    FILE *f = fopen(tmpfile, "wb");
    ASSERT_NE(f, nullptr);
    const char *data = "test data for checksum";
    fwrite(data, 1, strlen(data), f);
    fclose(f);

    uint32_t crc_file;
    gz_status_t st = gz_crc32_file(tmpfile, &crc_file);
    EXPECT_EQ(st, GZ_OK);

    uint32_t crc_mem = gz_crc32(data, strlen(data));
    EXPECT_EQ(crc_file, crc_mem);

    remove(tmpfile);
}

TEST_F(ChecksumTest, SHA256FileRead) {
    const char *tmpfile = "/tmp/test_sha256.bin";
    FILE *f = fopen(tmpfile, "wb");
    ASSERT_NE(f, nullptr);
    const char *data = "test data for sha256";
    fwrite(data, 1, strlen(data), f);
    fclose(f);

    uint8_t hash_file[GZ_SHA256_SIZE];
    gz_status_t st = gz_sha256_file(tmpfile, hash_file);
    EXPECT_EQ(st, GZ_OK);

    uint8_t hash_mem[GZ_SHA256_SIZE];
    gz_sha256(data, strlen(data), hash_mem);

    EXPECT_EQ(memcmp(hash_file, hash_mem, GZ_SHA256_SIZE), 0);

    remove(tmpfile);
}
