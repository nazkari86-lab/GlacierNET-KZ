#ifndef GLACIERKZ_THREAD_H
#define GLACIERKZ_THREAD_H

#include "glacierkz_tiff.h"
#include <pthread.h>
#include <stddef.h>

typedef void (*gz_task_fn)(void *arg);

typedef struct gz_task {
    gz_task_fn       fn;
    void            *arg;
    struct gz_task  *next;
} gz_task_t;

typedef struct {
    pthread_t       *threads;
    size_t           thread_count;

    gz_task_t       *task_head;
    gz_task_t       *task_tail;
    size_t           task_count;

    pthread_mutex_t  mutex;
    pthread_cond_t   not_empty;
    pthread_cond_t   all_done;

    int              shutdown;
    size_t           tasks_submitted;
    size_t           tasks_completed;
} gz_threadpool_t;

gz_status_t gz_threadpool_create(gz_threadpool_t *pool, size_t thread_count);
void        gz_threadpool_destroy(gz_threadpool_t *pool);
gz_status_t gz_threadpool_submit(gz_threadpool_t *pool, gz_task_fn fn, void *arg);
void        gz_threadpool_wait(gz_threadpool_t *pool);
size_t      gz_threadpool_completed(const gz_threadpool_t *pool);

#endif
