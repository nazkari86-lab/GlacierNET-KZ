#include <gtest/gtest.h>
#include "glacierkz_raster.h"
#include "glacierkz_tiff.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

class RasterTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(RasterTest, AllocUint8) {
    gz_raster_t raster;
    memset(&raster, 0, sizeof(raster));

    gz_status_t st = gz_raster_alloc(&raster, 64, 32, 1, GZ_DTYPE_UINT8);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_EQ(raster.width, (uint32_t)64);
    EXPECT_EQ(raster.height, (uint32_t)32);
    EXPECT_EQ(raster.bands, (uint16_t)1);
    EXPECT_EQ(raster.dtype, GZ_DTYPE_UINT8);
    EXPECT_NE(raster.data, nullptr);

    gz_raster_free(&raster);
}

TEST_F(RasterTest, AllocFloat32) {
    gz_raster_t raster;
    memset(&raster, 0, sizeof(raster));

    gz_status_t st = gz_raster_alloc(&raster, 100, 100, 3, GZ_DTYPE_FLOAT32);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_EQ(raster.width, (uint32_t)100);
    EXPECT_EQ(raster.height, (uint32_t)100);
    EXPECT_EQ(raster.bands, (uint16_t)3);
    EXPECT_EQ(raster.dtype, GZ_DTYPE_FLOAT32);

    gz_raster_free(&raster);
}

TEST_F(RasterTest, FreeNullSafe) {
    gz_raster_free(NULL);
}

TEST_F(RasterTest, AllocZeroWidthFails) {
    gz_raster_t raster;
    memset(&raster, 0, sizeof(raster));

    gz_status_t st = gz_raster_alloc(&raster, 0, 100, 1, GZ_DTYPE_UINT8);
    EXPECT_EQ(st, GZ_ERR_PARAM);
}

TEST_F(RasterTest, AllocZeroHeightFails) {
    gz_raster_t raster;
    memset(&raster, 0, sizeof(raster));

    gz_status_t st = gz_raster_alloc(&raster, 100, 0, 1, GZ_DTYPE_UINT8);
    EXPECT_EQ(st, GZ_ERR_PARAM);
}

TEST_F(RasterTest, PromoteUint8ToFloat32) {
    gz_raster_t src;
    memset(&src, 0, sizeof(src));
    gz_status_t st = gz_raster_alloc(&src, 4, 4, 1, GZ_DTYPE_UINT8);
    EXPECT_EQ(st, GZ_OK);

    uint8_t *data = (uint8_t *)src.data;
    for (int i = 0; i < 16; i++) data[i] = (uint8_t)(i * 10);

    gz_raster_t dst;
    memset(&dst, 0, sizeof(dst));
    st = gz_raster_promote(&src, &dst, GZ_DTYPE_FLOAT32);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_EQ(dst.dtype, GZ_DTYPE_FLOAT32);
    EXPECT_EQ(dst.width, (uint32_t)4);
    EXPECT_EQ(dst.height, (uint32_t)4);

    float *fdata = (float *)dst.data;
    for (int i = 0; i < 16; i++) {
        EXPECT_FLOAT_EQ(fdata[i], (float)(i * 10));
    }

    gz_raster_free(&src);
    gz_raster_free(&dst);
}

TEST_F(RasterTest, GetSetPixelUint8) {
    gz_raster_t raster;
    memset(&raster, 0, sizeof(raster));
    gz_status_t st = gz_raster_alloc(&raster, 8, 8, 1, GZ_DTYPE_UINT8);
    EXPECT_EQ(st, GZ_OK);

    st = gz_raster_set_pixel(&raster, 3, 5, 0, 42);
    EXPECT_EQ(st, GZ_OK);

    double val = 0;
    st = gz_raster_get_pixel(&raster, 3, 5, 0, &val);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_DOUBLE_EQ(val, 42.0);

    gz_raster_free(&raster);
}

TEST_F(RasterTest, GetPixelOutOfRangeFails) {
    gz_raster_t raster;
    memset(&raster, 0, sizeof(raster));
    gz_status_t st = gz_raster_alloc(&raster, 8, 8, 1, GZ_DTYPE_UINT8);
    EXPECT_EQ(st, GZ_OK);

    double val;
    st = gz_raster_get_pixel(&raster, 10, 10, 0, &val);
    EXPECT_EQ(st, GZ_ERR_PARAM);

    gz_raster_free(&raster);
}

TEST_F(RasterTest, StatsUint8) {
    gz_raster_t raster;
    memset(&raster, 0, sizeof(raster));
    gz_status_t st = gz_raster_alloc(&raster, 4, 4, 1, GZ_DTYPE_UINT8);
    EXPECT_EQ(st, GZ_OK);

    uint8_t *data = (uint8_t *)raster.data;
    for (int i = 0; i < 16; i++) data[i] = (uint8_t)(i + 1);

    double min, max, mean, stddev;
    st = gz_raster_stats(&raster, 0, &min, &max, &mean, &stddev);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_DOUBLE_EQ(min, 1.0);
    EXPECT_DOUBLE_EQ(max, 16.0);
    EXPECT_DOUBLE_EQ(mean, 8.5);
    EXPECT_GT(stddev, 0.0);

    gz_raster_free(&raster);
}

TEST_F(RasterTest, StatsNullRasterFails) {
    double min, max, mean, stddev;
    gz_status_t st = gz_raster_stats(NULL, 0, &min, &max, &mean, &stddev);
    EXPECT_EQ(st, GZ_ERR_PARAM);
}

TEST_F(RasterTest, CopyRaster) {
    gz_raster_t src;
    memset(&src, 0, sizeof(src));
    gz_status_t st = gz_raster_alloc(&src, 4, 4, 1, GZ_DTYPE_UINT8);
    EXPECT_EQ(st, GZ_OK);

    uint8_t *data = (uint8_t *)src.data;
    for (int i = 0; i < 16; i++) data[i] = (uint8_t)i;

    gz_raster_t dst;
    memset(&dst, 0, sizeof(dst));
    st = gz_raster_copy(&src, &dst);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_EQ(dst.width, src.width);
    EXPECT_EQ(dst.height, src.height);
    EXPECT_EQ(dst.dtype, src.dtype);

    uint8_t *dst_data = (uint8_t *)dst.data;
    for (int i = 0; i < 16; i++) {
        EXPECT_EQ(dst_data[i], data[i]);
    }

    gz_raster_free(&src);
    gz_raster_free(&dst);
}

TEST_F(RasterTest, CropRaster) {
    gz_raster_t src;
    memset(&src, 0, sizeof(src));
    gz_status_t st = gz_raster_alloc(&src, 16, 16, 1, GZ_DTYPE_UINT8);
    EXPECT_EQ(st, GZ_OK);

    uint8_t *data = (uint8_t *)src.data;
    for (int i = 0; i < 256; i++) data[i] = (uint8_t)(i & 0xFF);

    gz_raster_t crop;
    memset(&crop, 0, sizeof(crop));
    st = gz_raster_crop(&src, &crop, 4, 4, 8, 8);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_EQ(crop.width, (uint32_t)8);
    EXPECT_EQ(crop.height, (uint32_t)8);

    gz_raster_free(&src);
    gz_raster_free(&crop);
}

TEST_F(RasterTest, SetPixelOutOfRangeFails) {
    gz_raster_t raster;
    memset(&raster, 0, sizeof(raster));
    gz_status_t st = gz_raster_alloc(&raster, 4, 4, 1, GZ_DTYPE_UINT8);
    EXPECT_EQ(st, GZ_OK);

    st = gz_raster_set_pixel(&raster, 100, 100, 0, 1.0);
    EXPECT_EQ(st, GZ_ERR_PARAM);

    gz_raster_free(&raster);
}

TEST_F(RasterTest, StatsConstantValue) {
    gz_raster_t raster;
    memset(&raster, 0, sizeof(raster));
    gz_status_t st = gz_raster_alloc(&raster, 4, 4, 1, GZ_DTYPE_UINT8);
    EXPECT_EQ(st, GZ_OK);

    uint8_t *data = (uint8_t *)raster.data;
    for (int i = 0; i < 16; i++) data[i] = 128;

    double min, max, mean, stddev;
    st = gz_raster_stats(&raster, 0, &min, &max, &mean, &stddev);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_DOUBLE_EQ(min, 128.0);
    EXPECT_DOUBLE_EQ(max, 128.0);
    EXPECT_DOUBLE_EQ(mean, 128.0);
    EXPECT_DOUBLE_EQ(stddev, 0.0);

    gz_raster_free(&raster);
}
