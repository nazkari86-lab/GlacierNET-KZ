#ifndef GLACIERKZ_LOG_H
#define GLACIERKZ_LOG_H

#include <stdio.h>
#include <stdarg.h>

typedef enum {
    GZ_LOG_TRACE = 0,
    GZ_LOG_DEBUG = 1,
    GZ_LOG_INFO  = 2,
    GZ_LOG_WARN  = 3,
    GZ_LOG_ERROR = 4,
    GZ_LOG_FATAL = 5
} gz_log_level_t;

typedef struct {
    gz_log_level_t min_level;
    FILE          *output;
    int            use_color;
    int            show_timestamp;
    const char    *prefix;
} gz_logger_t;

void gz_log_init(gz_logger_t *logger);
void gz_log_set_level(gz_logger_t *logger, gz_log_level_t level);
void gz_log_set_output(gz_logger_t *logger, FILE *fp);
void gz_log_set_color(gz_logger_t *logger, int enabled);
void gz_log_set_timestamp(gz_logger_t *logger, int enabled);
void gz_log_set_prefix(gz_logger_t *logger, const char *prefix);

void gz_log_write(gz_logger_t *logger, gz_log_level_t level,
                  const char *file, int line, const char *fmt, ...);
void gz_log_writev(gz_logger_t *logger, gz_log_level_t level,
                   const char *file, int line, const char *fmt, va_list ap);

const char *gz_log_level_name(gz_log_level_t level);

extern gz_logger_t g_gz_logger;

#define GZ_LOG(level, ...) \
    gz_log_write(&g_gz_logger, level, __FILE__, __LINE__, __VA_ARGS__)

#define GZ_TRACE(...) GZ_LOG(GZ_LOG_TRACE, __VA_ARGS__)
#define GZ_DEBUG(...) GZ_LOG(GZ_LOG_DEBUG, __VA_ARGS__)
#define GZ_INFO(...)  GZ_LOG(GZ_LOG_INFO, __VA_ARGS__)
#define GZ_WARN(...)  GZ_LOG(GZ_LOG_WARN, __VA_ARGS__)
#define GZ_ERROR(...) GZ_LOG(GZ_LOG_ERROR, __VA_ARGS__)
#define GZ_FATAL(...) GZ_LOG(GZ_LOG_FATAL, __VA_ARGS__)

#endif
