#include <gtest/gtest.h>
#include "glacierkz_args.h"
#include <string.h>

class ArgsTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(ArgsTest, InitDefaults) {
    gz_arg_def_t defs[] = {
        { "-v", "--verbose", "Verbose", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_status_t st = gz_args_init(&args, defs, 1);
    EXPECT_EQ(st, GZ_OK);
    EXPECT_EQ(args.def_count, (size_t)1);
    EXPECT_EQ(defs[0].found, 0);
}

TEST_F(ArgsTest, ParseNoArgs) {
    gz_arg_def_t defs[] = {
        { "-v", "--verbose", "Verbose", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 1);

    char *argv[] = { (char*)"prog" };
    int ret = gz_args_parse(&args, 1, argv);
    EXPECT_EQ(ret, 0);
    EXPECT_EQ(defs[0].found, 0);

    gz_args_free(&args);
}

TEST_F(ArgsTest, ParseShortFlag) {
    gz_arg_def_t defs[] = {
        { "-v", "--verbose", "Verbose", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 1);

    char *argv[] = { (char*)"prog", (char*)"-v" };
    int ret = gz_args_parse(&args, 2, argv);
    EXPECT_EQ(ret, 0);
    EXPECT_EQ(defs[0].found, 1);

    gz_args_free(&args);
}

TEST_F(ArgsTest, ParseLongFlag) {
    gz_arg_def_t defs[] = {
        { "-v", "--verbose", "Verbose", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 1);

    char *argv[] = { (char*)"prog", (char*)"--verbose" };
    int ret = gz_args_parse(&args, 2, argv);
    EXPECT_EQ(ret, 0);
    EXPECT_EQ(defs[0].found, 1);

    gz_args_free(&args);
}

TEST_F(ArgsTest, ParseStringValue) {
    gz_arg_def_t defs[] = {
        { "-o", "--output", "Output file", GZ_ARG_STRING, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 1);

    char *argv[] = { (char*)"prog", (char*)"--output", (char*)"file.tif" };
    int ret = gz_args_parse(&args, 3, argv);
    EXPECT_EQ(ret, 0);
    EXPECT_EQ(defs[0].found, 1);
    EXPECT_STREQ(defs[0].str_value, "file.tif");

    gz_args_free(&args);
}

TEST_F(ArgsTest, ParseIntValue) {
    gz_arg_def_t defs[] = {
        { "-t", "--threads", "Thread count", GZ_ARG_INT, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 1);

    char *argv[] = { (char*)"prog", (char*)"--threads", (char*)"8" };
    int ret = gz_args_parse(&args, 3, argv);
    EXPECT_EQ(ret, 0);
    EXPECT_EQ(defs[0].found, 1);
    EXPECT_EQ(defs[0].int_value, 8);

    gz_args_free(&args);
}

TEST_F(ArgsTest, ParsePositional) {
    gz_arg_def_t defs[] = {
        { NULL, NULL, NULL, GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 0);

    char *argv[] = { (char*)"prog", (char*)"file.tif" };
    int ret = gz_args_parse(&args, 2, argv);
    EXPECT_EQ(ret, 0);
    EXPECT_EQ(gz_args_positional_count(&args), (size_t)1);
    EXPECT_STREQ(gz_args_positional(&args, 0), "file.tif");

    gz_args_free(&args);
}

TEST_F(ArgsTest, ParseMixedArgs) {
    gz_arg_def_t defs[] = {
        { "-v", "--verbose", "Verbose", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
        { "-o", "--output", "Output", GZ_ARG_STRING, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 2);

    char *argv[] = { (char*)"prog", (char*)"-v", (char*)"--output", (char*)"out.tif", (char*)"input.tif" };
    int ret = gz_args_parse(&args, 5, argv);
    EXPECT_EQ(ret, 0);
    EXPECT_EQ(defs[0].found, 1);
    EXPECT_EQ(defs[1].found, 1);
    EXPECT_STREQ(defs[1].str_value, "out.tif");
    EXPECT_EQ(gz_args_positional_count(&args), (size_t)1);
    EXPECT_STREQ(gz_args_positional(&args, 0), "input.tif");

    gz_args_free(&args);
}

TEST_F(ArgsTest, ParseUnknownOptionFails) {
    gz_arg_def_t defs[] = {
        { "-v", "--verbose", "Verbose", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 1);

    char *argv[] = { (char*)"prog", (char*)"--unknown" };
    int ret = gz_args_parse(&args, 2, argv);
    EXPECT_EQ(ret, -1);

    gz_args_free(&args);
}

TEST_F(ArgsTest, FoundReturns0ForMissing) {
    gz_arg_def_t defs[] = {
        { "-v", "--verbose", "Verbose", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 1);

    EXPECT_EQ(gz_args_found(&args, "--verbose"), 0);

    gz_args_free(&args);
}

TEST_F(ArgsTest, GetStringDefault) {
    gz_arg_def_t defs[] = {
        { "-o", "--output", "Output", GZ_ARG_STRING, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 1);

    const char *val = gz_args_get_string(&args, "--output", "default.txt");
    EXPECT_STREQ(val, "default.txt");

    gz_args_free(&args);
}

TEST_F(ArgsTest, GetIntDefault) {
    gz_arg_def_t defs[] = {
        { "-t", "--threads", "Threads", GZ_ARG_INT, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 1);

    int val = gz_args_get_int(&args, "--threads", 4);
    EXPECT_EQ(val, 4);

    gz_args_free(&args);
}

TEST_F(ArgsTest, PrintHelpDoesNotCrash) {
    gz_arg_def_t defs[] = {
        { "-v", "--verbose", "Verbose", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
        { "-o", "--output", "Output file", GZ_ARG_STRING, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 2);

    gz_args_print_help(&args);

    gz_args_free(&args);
}

TEST_F(ArgsTest, PositionalOutOfRange) {
    gz_arg_def_t defs[] = {};
    gz_args_t args;
    gz_args_init(&args, defs, 0);

    const char *val = gz_args_positional(&args, 0);
    EXPECT_EQ(val, nullptr);

    gz_args_free(&args);
}

TEST_F(ArgsTest, FindNonexistentOption) {
    gz_arg_def_t defs[] = {
        { "-v", "--verbose", "Verbose", GZ_ARG_FLAG, 0, 0, NULL, 0, 0.0 },
    };
    gz_args_t args;
    gz_args_init(&args, defs, 1);

    EXPECT_EQ(gz_args_found(&args, "--nonexistent"), 0);

    gz_args_free(&args);
}
