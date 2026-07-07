#include "glacierkz_log.h"
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stdarg.h>

gz_logger_t g_gz_logger = {
    .min_level = GZ_LOG_INFO,
    .output = NULL,
    .use_color = 1,
    .show_timestamp = 1,
    .prefix = NULL
};

void gz_log_init(gz_logger_t *logger) {
    if (!logger) return;
    logger->min_level = GZ_LOG_INFO;
    logger->output = NULL;
    logger->use_color = 1;
    logger->show_timestamp = 1;
    logger->prefix = NULL;
}

void gz_log_set_level(gz_logger_t *logger, gz_log_level_t level) {
    if (!logger) return;
    logger->min_level = level;
}

void gz_log_set_output(gz_logger_t *logger, FILE *fp) {
    if (!logger) return;
    logger->output = fp;
}

void gz_log_set_color(gz_logger_t *logger, int enabled) {
    if (!logger) return;
    logger->use_color = enabled;
}

void gz_log_set_timestamp(gz_logger_t *logger, int enabled) {
    if (!logger) return;
    logger->show_timestamp = enabled;
}

void gz_log_set_prefix(gz_logger_t *logger, const char *prefix) {
    if (!logger) return;
    logger->prefix = prefix;
}

const char *gz_log_level_name(gz_log_level_t level) {
    switch (level) {
        case GZ_LOG_TRACE: return "TRACE";
        case GZ_LOG_DEBUG: return "DEBUG";
        case GZ_LOG_INFO:  return "INFO ";
        case GZ_LOG_WARN:  return "WARN ";
        case GZ_LOG_ERROR: return "ERROR";
        case GZ_LOG_FATAL: return "FATAL";
    }
    return "?????";
}

static const char *level_colors[] = {
    "\033[36m",   /* TRACE - cyan */
    "\033[35m",   /* DEBUG - magenta */
    "\033[32m",   /* INFO  - green */
    "\033[33m",   /* WARN  - yellow */
    "\033[31m",   /* ERROR - red */
    "\033[1;31m"  /* FATAL - bold red */
};

#define COLOR_RESET "\033[0m"

void gz_log_write(gz_logger_t *logger, gz_log_level_t level,
                  const char *file, int line, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    gz_log_writev(logger, level, file, line, fmt, ap);
    va_end(ap);
}

void gz_log_writev(gz_logger_t *logger, gz_log_level_t level,
                   const char *file, int line, const char *fmt, va_list ap) {
    if (!logger) return;
    if (level < logger->min_level) return;

    FILE *out = logger->output ? logger->output : stderr;

    if (logger->show_timestamp) {
        time_t now = time(NULL);
        struct tm tm_buf;
#ifdef _WIN32
        localtime_s(&tm_buf, &now);
#else
        localtime_r(&now, &tm_buf);
#endif
        char time_buf[32];
        strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", &tm_buf);

        if (logger->use_color) {
            fprintf(out, "%s[%s]%s ", COLOR_RESET, time_buf, COLOR_RESET);
        } else {
            fprintf(out, "[%s] ", time_buf);
        }
    }

    if (logger->use_color) {
        fprintf(out, "%s%s%s ", level_colors[level], gz_log_level_name(level), COLOR_RESET);
    } else {
        fprintf(out, "%s ", gz_log_level_name(level));
    }

    if (logger->prefix) {
        fprintf(out, "[%s] ", logger->prefix);
    }

    vfprintf(out, fmt, ap);

    if (file && level >= GZ_LOG_DEBUG) {
        fprintf(out, " (%s:%d)", file, line);
    }

    fprintf(out, "\n");
    fflush(out);
}
