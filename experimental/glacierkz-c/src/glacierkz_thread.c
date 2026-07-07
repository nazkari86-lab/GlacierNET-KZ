#include "glacierkz_thread.h"
#include "glacierkz_log.h"
#include <stdlib.h>
#include <string.h>

static void *worker_thread(void *arg) {
    gz_threadpool_t *pool = (gz_threadpool_t *)arg;

    while (1) {
        pthread_mutex_lock(&pool->mutex);

        while (pool->task_head == NULL && !pool->shutdown) {
            pthread_cond_wait(&pool->not_empty, &pool->mutex);
        }

        if (pool->shutdown && pool->task_head == NULL) {
            pthread_mutex_unlock(&pool->mutex);
            break;
        }

        gz_task_t *task = pool->task_head;
        if (task) {
            pool->task_head = task->next;
            if (!pool->task_head) pool->task_tail = NULL;
            pool->task_count--;
        }

        pthread_mutex_unlock(&pool->mutex);

        if (task) {
            task->fn(task->arg);
            free(task);

            pthread_mutex_lock(&pool->mutex);
            pool->tasks_completed++;
            if (pool->tasks_completed == pool->tasks_submitted) {
                pthread_cond_broadcast(&pool->all_done);
            }
            pthread_mutex_unlock(&pool->mutex);
        }
    }

    return NULL;
}

gz_status_t gz_threadpool_create(gz_threadpool_t *pool, size_t thread_count) {
    if (!pool || thread_count == 0) return GZ_ERR_PARAM;

    memset(pool, 0, sizeof(*pool));

    pool->threads = calloc(thread_count, sizeof(pthread_t));
    if (!pool->threads) return GZ_ERR_NOMEM;

    pool->thread_count = thread_count;
    pool->shutdown = 0;
    pool->tasks_submitted = 0;
    pool->tasks_completed = 0;

    if (pthread_mutex_init(&pool->mutex, NULL) != 0) {
        free(pool->threads);
        return GZ_ERR_NOMEM;
    }
    if (pthread_cond_init(&pool->not_empty, NULL) != 0) {
        pthread_mutex_destroy(&pool->mutex);
        free(pool->threads);
        return GZ_ERR_NOMEM;
    }
    if (pthread_cond_init(&pool->all_done, NULL) != 0) {
        pthread_cond_destroy(&pool->not_empty);
        pthread_mutex_destroy(&pool->mutex);
        free(pool->threads);
        return GZ_ERR_NOMEM;
    }

    for (size_t i = 0; i < thread_count; i++) {
        if (pthread_create(&pool->threads[i], NULL, worker_thread, pool) != 0) {
            pool->thread_count = i;
            gz_threadpool_destroy(pool);
            return GZ_ERR_NOMEM;
        }
    }

    GZ_DEBUG("Thread pool created with %zu threads", thread_count);
    return GZ_OK;
}

void gz_threadpool_destroy(gz_threadpool_t *pool) {
    if (!pool) return;

    pthread_mutex_lock(&pool->mutex);
    pool->shutdown = 1;
    pthread_cond_broadcast(&pool->not_empty);
    pthread_mutex_unlock(&pool->mutex);

    for (size_t i = 0; i < pool->thread_count; i++) {
        pthread_join(pool->threads[i], NULL);
    }

    gz_task_t *task = pool->task_head;
    while (task) {
        gz_task_t *next = task->next;
        free(task);
        task = next;
    }

    pthread_mutex_destroy(&pool->mutex);
    pthread_cond_destroy(&pool->not_empty);
    pthread_cond_destroy(&pool->all_done);
    free(pool->threads);

    pool->threads = NULL;
    pool->thread_count = 0;
    pool->task_head = NULL;
    pool->task_tail = NULL;
    pool->task_count = 0;
}

gz_status_t gz_threadpool_submit(gz_threadpool_t *pool, gz_task_fn fn, void *arg) {
    if (!pool || !fn) return GZ_ERR_PARAM;

    gz_task_t *task = malloc(sizeof(gz_task_t));
    if (!task) return GZ_ERR_NOMEM;

    task->fn = fn;
    task->arg = arg;
    task->next = NULL;

    pthread_mutex_lock(&pool->mutex);

    if (pool->shutdown) {
        pthread_mutex_unlock(&pool->mutex);
        free(task);
        return GZ_ERR_LIMIT;
    }

    if (pool->task_tail) {
        pool->task_tail->next = task;
    } else {
        pool->task_head = task;
    }
    pool->task_tail = task;
    pool->task_count++;
    pool->tasks_submitted++;

    pthread_cond_signal(&pool->not_empty);
    pthread_mutex_unlock(&pool->mutex);
    return GZ_OK;
}

void gz_threadpool_wait(gz_threadpool_t *pool) {
    if (!pool) return;

    pthread_mutex_lock(&pool->mutex);
    while (pool->tasks_completed < pool->tasks_submitted || pool->task_count > 0) {
        pthread_cond_wait(&pool->all_done, &pool->mutex);
    }
    pthread_mutex_unlock(&pool->mutex);
}

size_t gz_threadpool_completed(const gz_threadpool_t *pool) {
    if (!pool) return 0;
    pthread_mutex_lock((pthread_mutex_t *)&pool->mutex);
    size_t c = pool->tasks_completed;
    pthread_mutex_unlock((pthread_mutex_t *)&pool->mutex);
    return c;
}
