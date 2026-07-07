#include <gtest/gtest.h>
#include "glacierkz_thread.h"
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

class ThreadTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

static void simple_task(void *arg) {
    int *val = (int *)arg;
    *val = 42;
}

static void increment_task(void *arg) {
    int *val = (int *)arg;
    __sync_fetch_and_add(val, 1);
}

TEST_F(ThreadTest, PoolCreateDestroy) {
    gz_threadpool_t pool;
    gz_status_t st = gz_threadpool_create(&pool, 4);
    EXPECT_EQ(st, GZ_OK);

    gz_threadpool_destroy(&pool);
}

TEST_F(ThreadTest, PoolCreateZeroThreadsFails) {
    gz_threadpool_t pool;
    gz_status_t st = gz_threadpool_create(&pool, 0);
    EXPECT_EQ(st, GZ_ERR_PARAM);
}

TEST_F(ThreadTest, PoolSubmitSingleTask) {
    gz_threadpool_t pool;
    gz_status_t st = gz_threadpool_create(&pool, 2);
    EXPECT_EQ(st, GZ_OK);

    int result = 0;
    st = gz_threadpool_submit(&pool, simple_task, &result);
    EXPECT_EQ(st, GZ_OK);

    gz_threadpool_wait(&pool);
    EXPECT_EQ(result, 42);

    gz_threadpool_destroy(&pool);
}

TEST_F(ThreadTest, PoolSubmitManyTasks) {
    gz_threadpool_t pool;
    gz_status_t st = gz_threadpool_create(&pool, 4);
    EXPECT_EQ(st, GZ_OK);

    int counter = 0;
    for (int i = 0; i < 100; i++) {
        st = gz_threadpool_submit(&pool, increment_task, &counter);
        EXPECT_EQ(st, GZ_OK);
    }

    gz_threadpool_wait(&pool);
    EXPECT_EQ(counter, 100);

    gz_threadpool_destroy(&pool);
}

TEST_F(ThreadTest, PoolWaitWithoutSubmit) {
    gz_threadpool_t pool;
    gz_status_t st = gz_threadpool_create(&pool, 2);
    EXPECT_EQ(st, GZ_OK);

    gz_threadpool_wait(&pool);

    gz_threadpool_destroy(&pool);
}

TEST_F(ThreadTest, CompletedCount) {
    gz_threadpool_t pool;
    gz_status_t st = gz_threadpool_create(&pool, 2);
    EXPECT_EQ(st, GZ_OK);

    int result = 0;
    st = gz_threadpool_submit(&pool, simple_task, &result);
    EXPECT_EQ(st, GZ_OK);

    gz_threadpool_wait(&pool);

    size_t completed = gz_threadpool_completed(&pool);
    EXPECT_EQ(completed, (size_t)1);

    gz_threadpool_destroy(&pool);
}

TEST_F(ThreadTest, PoolDestroyWhileRunning) {
    gz_threadpool_t pool;
    gz_status_t st = gz_threadpool_create(&pool, 4);
    EXPECT_EQ(st, GZ_OK);

    for (int i = 0; i < 50; i++) {
        st = gz_threadpool_submit(&pool, simple_task, (void *)(intptr_t)0);
        EXPECT_EQ(st, GZ_OK);
    }

    gz_threadpool_destroy(&pool);
}

TEST_F(ThreadTest, PoolSubmitAfterShutdownFails) {
    gz_threadpool_t pool;
    gz_status_t st = gz_threadpool_create(&pool, 2);
    EXPECT_EQ(st, GZ_OK);

    gz_threadpool_destroy(&pool);

    st = gz_threadpool_submit(&pool, simple_task, (void *)0);
    EXPECT_NE(st, GZ_OK);
}

TEST_F(ThreadTest, MultiplePools) {
    gz_threadpool_t pool1, pool2;
    gz_status_t st1 = gz_threadpool_create(&pool1, 2);
    gz_status_t st2 = gz_threadpool_create(&pool2, 3);
    EXPECT_EQ(st1, GZ_OK);
    EXPECT_EQ(st2, GZ_OK);

    int r1 = 0, r2 = 0;
    gz_threadpool_submit(&pool1, simple_task, &r1);
    gz_threadpool_submit(&pool2, simple_task, &r2);

    gz_threadpool_wait(&pool1);
    gz_threadpool_wait(&pool2);

    EXPECT_EQ(r1, 42);
    EXPECT_EQ(r2, 42);

    gz_threadpool_destroy(&pool1);
    gz_threadpool_destroy(&pool2);
}
