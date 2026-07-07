#include <gtest/gtest.h>
#include "glacierkz_tiff.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

class TiffTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(TiffTest, OpenNonexistentReturnsNotFound) {
    gz_tiff_t tiff;
    gz_status_t st = gz_tiff_open(&tiff, "/nonexistent/file.tif");
    EXPECT_EQ(st, GZ_ERR_NOTFOUND);
}

TEST_F(TiffTest, OpenInvalidFileReturnsFormat) {
    const char *tmpfile = "/tmp/test_invalid.tif";
    FILE *f = fopen(tmpfile, "wb");
    ASSERT_NE(f, nullptr);
    fprintf(f, "This is not a TIFF file");
    fclose(f);

    gz_tiff_t tiff;
    gz_status_t st = gz_tiff_open(&tiff, tmpfile);
    EXPECT_EQ(st, GZ_ERR_FORMAT);

    remove(tmpfile);
}

TEST_F(TiffTest, OpenValidMinimalTiff) {
    const char *tmpfile = "/tmp/test_minimal.tif";
    FILE *f = fopen(tmpfile, "wb");
    ASSERT_NE(f, nullptr);

    /* Write minimal TIFF: LE, magic 42, IFD with 1 entry */
    fputc('I', f); fputc('I', f);           /* byte order LE */
    uint16_t magic = 42;
    fwrite(&magic, 2, 1, f);
    uint32_t ifd_offset = 8;
    fwrite(&ifd_offset, 4, 1, f);

    uint16_t entry_count = 1;
    fwrite(&entry_count, 2, 1, f);

    /* ImageWidth tag */
    uint16_t tag = 256;
    fwrite(&tag, 2, 1, f);
    uint16_t type = 3; /* SHORT */
    fwrite(&type, 2, 1, f);
    uint32_t count = 1;
    fwrite(&count, 4, 1, f);
    uint32_t value = 64;
    fwrite(&value, 4, 1, f);

    uint32_t next_ifd = 0;
    fwrite(&next_ifd, 4, 1, f);

    fclose(f);

    gz_tiff_t tiff;
    gz_status_t st = gz_tiff_open(&tiff, tmpfile);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_EQ(tiff.ifd_count, (size_t)1);
    EXPECT_EQ(tiff.ifds[0].count, (uint16_t)1);

    uint32_t w = gz_tiff_get_uint(&tiff.ifds[0], 256, 0);
    EXPECT_EQ(w, (uint32_t)64);

    gz_tiff_close(&tiff);
    remove(tmpfile);
}

TEST_F(TiffTest, GetUintDefaultReturnsFallback) {
    gz_ifd_t ifd;
    memset(&ifd, 0, sizeof(ifd));
    ifd.count = 0;
    ifd.entries = NULL;

    uint32_t val = gz_tiff_get_uint(&ifd, 256, 42);
    EXPECT_EQ(val, (uint32_t)42);
}

TEST_F(TiffTest, GetUshortDefaultReturnsFallback) {
    gz_ifd_t ifd;
    memset(&ifd, 0, sizeof(ifd));
    ifd.count = 0;
    ifd.entries = NULL;

    uint16_t val = gz_tiff_get_ushort(&ifd, 258, 99);
    EXPECT_EQ(val, (uint16_t)99);
}

TEST_F(TiffTest, GetDoubleDefaultReturnsFallback) {
    gz_ifd_t ifd;
    memset(&ifd, 0, sizeof(ifd));
    ifd.count = 0;
    ifd.entries = NULL;

    double val = gz_tiff_get_double(&ifd, 282, 3.14);
    EXPECT_DOUBLE_EQ(val, 3.14);
}

TEST_F(TiffTest, CloseNullIsSafe) {
    gz_tiff_close(NULL);
}

TEST_F(TiffTest, OpenTruncatedReturnsFormat) {
    const char *tmpfile = "/tmp/test_truncated.tif";
    FILE *f = fopen(tmpfile, "wb");
    ASSERT_NE(f, nullptr);

    fputc('I', f); fputc('I', f);
    uint16_t magic = 42;
    fwrite(&magic, 2, 1, f);
    /* Truncated - no IFD offset */

    fclose(f);

    gz_tiff_t tiff;
    gz_status_t st = gz_tiff_open(&tiff, tmpfile);
    EXPECT_EQ(st, GZ_ERR_FORMAT);

    remove(tmpfile);
}

TEST_F(TiffTest, ByteOrderBig) {
    const char *tmpfile = "/tmp/test_bigendian.tif";
    FILE *f = fopen(tmpfile, "wb");
    ASSERT_NE(f, nullptr);

    fputc('M', f); fputc('M', f);           /* byte order BE */
    uint16_t magic = 42;
    /* Write big-endian magic */
    fputc(0, f); fputc(42, f);
    uint32_t ifd_offset = 8;
    /* Write big-endian offset */
    fputc(0, f); fputc(0, f); fputc(0, f); fputc(8, f);

    uint16_t entry_count = 0;
    fputc(0, f); fputc(0, f);

    uint32_t next_ifd = 0;
    fputc(0, f); fputc(0, f); fputc(0, f); fputc(0, f);

    fclose(f);

    gz_tiff_t tiff;
    gz_status_t st = gz_tiff_open(&tiff, tmpfile);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_EQ(tiff.byte_order, GZ_ENDIAN_BIG);
    EXPECT_EQ(tiff.is_bigtiff, 0);

    gz_tiff_close(&tiff);
    remove(tmpfile);
}

TEST_F(TiffTest, MultipleTagsParsed) {
    const char *tmpfile = "/tmp/test_multitags.tif";
    FILE *f = fopen(tmpfile, "wb");
    ASSERT_NE(f, nullptr);

    /* LE TIFF */
    fputc('I', f); fputc('I', f);
    uint16_t magic = 42;
    fwrite(&magic, 2, 1, f);
    uint32_t ifd_off = 8;
    fwrite(&ifd_off, 4, 1, f);

    uint16_t count = 3;
    fwrite(&count, 2, 1, f);

    /* Tag 256: ImageWidth = 100 */
    uint16_t tag = 256;
    fwrite(&tag, 2, 1, f);
    uint16_t type = 3;
    fwrite(&type, 2, 1, f);
    uint32_t cnt = 1;
    fwrite(&cnt, 4, 1, f);
    uint32_t val = 100;
    fwrite(&val, 4, 1, f);

    /* Tag 257: ImageLength = 200 */
    tag = 257;
    fwrite(&tag, 2, 1, f);
    fwrite(&type, 2, 1, f);
    fwrite(&cnt, 4, 1, f);
    val = 200;
    fwrite(&val, 4, 1, f);

    /* Tag 258: BitsPerSample = 16 */
    tag = 258;
    fwrite(&tag, 2, 1, f);
    fwrite(&type, 2, 1, f);
    fwrite(&cnt, 4, 1, f);
    val = 16;
    fwrite(&val, 4, 1, f);

    uint32_t next = 0;
    fwrite(&next, 4, 1, f);

    fclose(f);

    gz_tiff_t tiff;
    gz_status_t st = gz_tiff_open(&tiff, tmpfile);
    EXPECT_EQ(st, GZ_OK);

    const gz_ifd_t *ifd = &tiff.ifds[0];
    EXPECT_EQ(gz_tiff_get_uint(ifd, 256, 0), (uint32_t)100);
    EXPECT_EQ(gz_tiff_get_uint(ifd, 257, 0), (uint32_t)200);
    EXPECT_EQ(gz_tiff_get_ushort(ifd, 258, 0), (uint16_t)16);

    gz_tiff_close(&tiff);
    remove(tmpfile);
}

TEST_F(TiffTest, ZeroIfdCount) {
    const char *tmpfile = "/tmp/test_zeroifd.tif";
    FILE *f = fopen(tmpfile, "wb");
    ASSERT_NE(f, nullptr);

    fputc('I', f); fputc('I', f);
    uint16_t magic = 42;
    fwrite(&magic, 2, 1, f);
    uint32_t ifd_off = 8;
    fwrite(&ifd_off, 4, 1, f);

    uint16_t count = 0;
    fwrite(&count, 2, 1, f);

    uint32_t next = 0;
    fwrite(&next, 4, 1, f);

    fclose(f);

    gz_tiff_t tiff;
    gz_status_t st = gz_tiff_open(&tiff, tmpfile);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_EQ(tiff.ifd_count, (size_t)0);

    gz_tiff_close(&tiff);
    remove(tmpfile);
}
