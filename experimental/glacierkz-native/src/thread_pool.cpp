#include "glacierkz/thread_pool.hpp"

#include <algorithm>
#include <stdexcept>
#include <spdlog/spdlog.h>

namespace glacierkz {

ThreadPool::ThreadPool(size_t num_threads) {
    if (num_threads == 0) {
        num_threads = std::max(1u, std::thread::hardware_concurrency());
    }

    workers_.reserve(num_threads);
    for (size_t i = 0; i < num_threads; ++i) {
        workers_.emplace_back(&ThreadPool::worker_loop, this);
    }

    spdlog::info("ThreadPool started with {} workers", num_threads);
}

ThreadPool::~ThreadPool() {
    {
        std::unique_lock lock(queue_mutex_);
        stop_ = true;
    }
    queue_cv_.notify_all();

    for (auto& t : workers_) {
        if (t.joinable()) t.join();
    }
}

void ThreadPool::wait_all() {
    std::unique_lock lock(wait_mutex_);
    wait_cv_.wait(lock, [this] {
        return tasks_.empty() && active_tasks_ == 0;
    });
}

bool ThreadPool::wait_for(std::chrono::milliseconds timeout) {
    std::unique_lock lock(wait_mutex_);
    return wait_cv_.wait_for(lock, timeout, [this] {
        return tasks_.empty() && active_tasks_ == 0;
    });
}

void ThreadPool::pause() {
    paused_ = true;
}

void ThreadPool::resume() {
    paused_ = false;
    queue_cv_.notify_all();
}

bool ThreadPool::is_paused() const {
    return paused_;
}

void ThreadPool::cancel() {
    cancelled_ = true;
    {
        std::unique_lock lock(queue_mutex_);
        std::queue<std::function<void()>> empty;
        tasks_.swap(empty);
    }
    queue_cv_.notify_all();
}

bool ThreadPool::is_cancelled() const {
    return cancelled_;
}

size_t ThreadPool::thread_count() const {
    return workers_.size();
}

size_t ThreadPool::pending_tasks() const {
    std::lock_guard lock(queue_mutex_);
    return tasks_.size();
}

size_t ThreadPool::completed_tasks() const {
    return stats_.tasks_completed.load(std::memory_order_relaxed);
}

const TaskStats& ThreadPool::stats() const {
    return stats_;
}

void ThreadPool::resize(size_t num_threads) {
    {
        std::unique_lock lock(queue_mutex_);
        stop_ = true;
    }
    queue_cv_.notify_all();

    for (auto& t : workers_) {
        if (t.joinable()) t.join();
    }
    workers_.clear();

    {
        std::unique_lock lock(queue_mutex_);
        stop_ = false;
    }

    workers_.reserve(num_threads);
    for (size_t i = 0; i < num_threads; ++i) {
        workers_.emplace_back(&ThreadPool::worker_loop, this);
    }
}

void ThreadPool::worker_loop() {
    while (true) {
        std::function<void()> task;

        {
            std::unique_lock lock(queue_mutex_);
            queue_cv_.wait(lock, [this] {
                return stop_ || !tasks_.empty();
            });

            if (stop_ && tasks_.empty()) return;

            if (paused_) {
                continue;
            }

            if (cancelled_) {
                tasks_ = std::queue<std::function<void()>>();
                return;
            }

            task = std::move(tasks_.front());
            tasks_.pop();
        }

        active_tasks_.fetch_add(1, std::memory_order_relaxed);

        try {
            task();
            stats_.tasks_completed.fetch_add(1, std::memory_order_relaxed);
        } catch (const std::exception& e) {
            stats_.tasks_failed.fetch_add(1, std::memory_order_relaxed);
            spdlog::error("Task exception: {}", e.what());
        } catch (...) {
            stats_.tasks_failed.fetch_add(1, std::memory_order_relaxed);
            spdlog::error("Task threw unknown exception");
        }

        active_tasks_.fetch_sub(1, std::memory_order_relaxed);
        wait_cv_.notify_all();
    }
}

} // namespace glacierkz
