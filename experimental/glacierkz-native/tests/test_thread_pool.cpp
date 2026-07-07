#include <gtest/gtest.h>
#include "glacierkz/thread_pool.hpp"

#include <atomic>
#include <chrono>
#include <thread>

using namespace glacierkz;

TEST(ThreadPoolTest, BasicSubmit) {
    ThreadPool pool(2);
    std::atomic<int> counter{0};
    for (int i = 0; i < 10; ++i) {
        pool.submit([&counter]() { counter.fetch_add(1); });
    }
    pool.wait_all();
    EXPECT_EQ(counter.load(), 10);
}

TEST(ThreadPoolTest, WaitAll) {
    ThreadPool pool(4);
    std::atomic<int> counter{0};
    for (int i = 0; i < 100; ++i) {
        pool.submit([&counter]() {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
            counter.fetch_add(1);
        });
    }
    pool.wait_all();
    EXPECT_EQ(counter.load(), 100);
}

TEST(ThreadPoolTest, WaitFor) {
    ThreadPool pool(2);
    std::atomic<bool> done{false};
    pool.submit([&done]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        done = true;
    });
    bool result = pool.wait_for(std::chrono::milliseconds(200));
    EXPECT_TRUE(result);
    EXPECT_TRUE(done);
}

TEST(ThreadPoolTest, PauseResume) {
    ThreadPool pool(1);
    std::atomic<int> counter{0};

    pool.submit([&pool, &counter]() {
        counter.fetch_add(1);
    });

    pool.pause();
    pool.wait_all();
    EXPECT_EQ(counter.load(), 1);

    pool.submit([&counter]() { counter.fetch_add(1); });
    pool.resume();
    pool.wait_all();
    EXPECT_EQ(counter.load(), 2);
}

TEST(ThreadPoolTest, Cancel) {
    ThreadPool pool(2);
    pool.cancel();
    EXPECT_TRUE(pool.is_cancelled());
}

TEST(ThreadPoolTest, ThreadCount) {
    ThreadPool pool(4);
    EXPECT_EQ(pool.thread_count(), 4u);
}

TEST(ThreadPoolTest, PendingTasks) {
    ThreadPool pool(1);
    EXPECT_EQ(pool.pending_tasks(), 0u);
}

TEST(ThreadPoolTest, CompletedTasks) {
    ThreadPool pool(2);
    std::atomic<int> counter{0};
    for (int i = 0; i < 10; ++i) {
        pool.submit([&counter]() { counter.fetch_add(1); });
    }
    pool.wait_all();
    EXPECT_GE(pool.completed_tasks(), 10u);
}

TEST(ThreadPoolTest, Stats) {
    ThreadPool pool(2);
    std::atomic<int> counter{0};
    for (int i = 0; i < 5; ++i) {
        pool.submit([&counter]() { counter.fetch_add(1); });
    }
    pool.wait_all();
    const auto& s = pool.stats();
    EXPECT_GE(s.tasks_completed.load(), 5u);
}

TEST(ThreadPoolTest, Resize) {
    ThreadPool pool(2);
    EXPECT_EQ(pool.thread_count(), 2u);
    pool.resize(4);
    EXPECT_EQ(pool.thread_count(), 4u);
}
