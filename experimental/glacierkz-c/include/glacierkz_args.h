#ifndef GLACIERKZ_ARGS_H
#define GLACIERKZ_ARGS_H

#include <stddef.h>

typedef enum {
    GZ_ARG_NONE,
    GZ_ARG_FLAG,
    GZ_ARG_STRING,
    GZ_ARG_INT,
    GZ_ARG_FLOAT
} gz_arg_type_t;

typedef struct {
    const char     *short_flag;
    const char     *long_flag;
    const char     *description;
    gz_arg_type_t   type;
    int             required;
    int             found;
    const char     *str_value;
    int             int_value;
    double          float_value;
} gz_arg_def_t;

typedef struct {
    const char *name;
    int         index;
} gz_positional_t;

typedef struct {
    gz_arg_def_t     *defs;
    size_t            def_count;
    gz_positional_t  *positionals;
    size_t            pos_count;
    size_t            pos_capacity;
    int              *pos_indices;
    int               argc;
    char            **argv;
} gz_args_t;

int  gz_args_init(gz_args_t *args, gz_arg_def_t *defs, size_t def_count);
int  gz_args_parse(gz_args_t *args, int argc, char **argv);
void gz_args_free(gz_args_t *args);
void gz_args_print_help(const gz_args_t *args);

int         gz_args_found(const gz_args_t *args, const char *long_flag);
const char *gz_args_get_string(const gz_args_t *args, const char *long_flag, const char *dflt);
int         gz_args_get_int(const gz_args_t *args, const char *long_flag, int dflt);
double      gz_args_get_float(const gz_args_t *args, const char *long_flag, double dflt);

size_t      gz_args_positional_count(const gz_args_t *args);
const char *gz_args_positional(const gz_args_t *args, size_t index);

#endif
