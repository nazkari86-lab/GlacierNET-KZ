#pragma once

#include <vector>
#include <queue>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <future>
#include <functional>
#include <atomic>
#include <memory>
#include <stdexcept>
#include <optional>
#include <chrono>

namespace glacierkz {

struct TaskStats {
    std::atomic<size_t> tasks_submitted{0};
    std::atomic<size_t> tasks_completed{0};
    std::atomic<size_t> tasks_failed{0};

    double completion_rate() const {
        size_t submitted = tasks_submitted.load();
        if (submitted == 0) return 0.0;
        return static_cast<double>(tasks_completed.load()) / submitted * 100.0;
    }
};

class ThreadPool {
public:
    explicit ThreadPool(size_t num_threads = 0);
    ~ThreadPool();

    ThreadPool(const ThreadPool&) = delete;
    ThreadPool& operator=(const ThreadPool&) = delete;

    template<typename F, typename... Args>
    auto submit(F&& f, Args&&... args)
        -> std::future<std::invoke_result_t<F, Args...>>;

    template<typename F>
    void submit_void(F&& f);

    void wait_all();
    bool wait_for(std::chrono::milliseconds timeout);

    void pause();
    void resume();
    bool is_paused() const;

    void cancel();
    bool is_cancelled() const;

    size_t thread_count() const;
    size_t pending_tasks() const;
    size_t completed_tasks() const;
    const TaskStats& stats() const;

    void resize(size_t num_threads);

private:
    std::vector<std::thread> workers_;
    std::queue<std::function<void()>> tasks_;

    mutable std::mutex queue_mutex_;
    mutable std::mutex wait_mutex_;
    std::condition_variable queue_cv_;
    std::condition_variable wait_cv_;

    std::atomic<bool> stop_{false};
    std::atomic<bool> paused_{false};
    std::atomic<bool> cancelled_{false};
    std::atomic<size_t> active_tasks_{0};
    TaskStats stats_;

    void worker_loop();
};

template<typename F, typename... Args>
auto ThreadPool::submit(F&& f, Args&&... args)
    -> std::future<std::invoke_result_t<F, Args...>>
{
    using return_type = std::invoke_result_t<F, Args...>;

    auto task = std::make_shared<std::packaged_task<return_type()>>(
        std::bind(std::forward<F>(f), std::forward<Args>(args)...)
    );

    std::future<return_type> result = task->get_future();

    {
        std::unique_lock lock(queue_mutex_);
        if (stop_) {
            throw std::runtime_error("ThreadPool: submit on stopped pool");
        }
        tasks_.emplace([task]() { (*task)(); });
        stats_.tasks_submitted.fetch_add(1, std::memory_order_relaxed);
    }
    queue_cv_.notify_one();

    return result;
}

template<typename F>
void ThreadPool::submit_void(F&& f) {
    {
        std::unique_lock lock(queue_mutex_);
        if (stop_) {
            throw std::runtime_error("ThreadPool: submit on stopped pool");
        }
        tasks_.emplace(std::forward<F>(f));
        stats_.tasks_submitted.fetch_add(1, std::memory_order_relaxed);
    }
    queue_cv_.notify_one();
}

class ScopedPool {
public:
    explicit ScopedPool(size_t threads = 0)
        : pool_(threads) {}
    ThreadPool& pool() { return pool_; }
    ThreadPool* operator->() { return &pool_; }
private:
    ThreadPool pool_;
};

} // namespace glacierkz
