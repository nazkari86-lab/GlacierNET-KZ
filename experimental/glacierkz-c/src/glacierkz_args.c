#include "glacierkz_args.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <ctype.h>

int gz_args_init(gz_args_t *args, gz_arg_def_t *defs, size_t def_count) {
    if (!args || !defs) return -1;

    args->defs = defs;
    args->def_count = def_count;
    args->positionals = NULL;
    args->pos_count = 0;
    args->pos_capacity = 0;
    args->pos_indices = NULL;
    args->argc = 0;
    args->argv = NULL;

    for (size_t i = 0; i < def_count; i++) {
        defs[i].found = 0;
        defs[i].str_value = NULL;
        defs[i].int_value = 0;
        defs[i].float_value = 0.0;
    }

    return 0;
}

static gz_arg_def_t *find_def_short(gz_args_t *args, const char *flag) {
    for (size_t i = 0; i < args->def_count; i++) {
        if (args->defs[i].short_flag && strcmp(args->defs[i].short_flag, flag) == 0) {
            return &args->defs[i];
        }
    }
    return NULL;
}

static gz_arg_def_t *find_def_long(gz_args_t *args, const char *flag) {
    for (size_t i = 0; i < args->def_count; i++) {
        if (args->defs[i].long_flag && strcmp(args->defs[i].long_flag, flag) == 0) {
            return &args->defs[i];
        }
    }
    return NULL;
}

static gz_arg_def_t *find_def_long_prefix(gz_args_t *args, const char *flag, size_t len) {
    for (size_t i = 0; i < args->def_count; i++) {
        if (args->defs[i].long_flag && strlen(args->defs[i].long_flag) == len &&
            strncmp(args->defs[i].long_flag, flag, len) == 0) {
            return &args->defs[i];
        }
    }
    return NULL;
}

static int add_positional(gz_args_t *args, const char *value, int index) {
    if (args->pos_count >= args->pos_capacity) {
        size_t new_cap = args->pos_capacity ? args->pos_capacity * 2 : 8;
        gz_positional_t *new_pos = realloc(args->positionals, new_cap * sizeof(gz_positional_t));
        int *new_idx = realloc(args->pos_indices, new_cap * sizeof(int));
        if (!new_pos || !new_idx) return -1;
        args->positionals = new_pos;
        args->pos_indices = new_idx;
        args->pos_capacity = new_cap;
    }

    args->positionals[args->pos_count].name = value;
    args->positionals[args->pos_count].index = index;
    args->pos_indices[args->pos_count] = index;
    args->pos_count++;
    return 0;
}

int gz_args_parse(gz_args_t *args, int argc, char **argv) {
    if (!args || argc < 1) return -1;

    args->argc = argc;
    args->argv = argv;

    int i = 1;
    while (i < argc) {
        const char *arg = argv[i];

        if (arg[0] == '-') {
            if (arg[1] == '-') {
                if (arg[2] == '\0') {
                    i++;
                    while (i < argc) {
                        add_positional(args, argv[i], i);
                        i++;
                    }
                    break;
                }

                const char *eq = strchr(arg + 2, '=');
                size_t flag_len = eq ? (size_t)(eq - arg - 2) : strlen(arg + 2);

                gz_arg_def_t *def = find_def_long_prefix(args, arg + 2, flag_len);
                if (!def) {
                    fprintf(stderr, "Unknown option: %s\n", arg);
                    return -1;
                }

                def->found = 1;
                if (def->type == GZ_ARG_FLAG) {
                    /* no value */
                } else if (def->type == GZ_ARG_STRING) {
                    def->str_value = eq ? eq + 1 : (i + 1 < argc ? argv[++i] : NULL);
                } else if (def->type == GZ_ARG_INT) {
                    const char *val = eq ? eq + 1 : (i + 1 < argc ? argv[++i] : NULL);
                    if (val) def->int_value = atoi(val);
                } else if (def->type == GZ_ARG_FLOAT) {
                    const char *val = eq ? eq + 1 : (i + 1 < argc ? argv[++i] : NULL);
                    if (val) def->float_value = atof(val);
                }
            } else if (arg[1] != '\0') {
                if (arg[2] == '\0') {
                    gz_arg_def_t *def = find_def_short(args, arg);
                    if (!def) {
                        fprintf(stderr, "Unknown option: %s\n", arg);
                        return -1;
                    }

                    def->found = 1;
                    if (def->type != GZ_ARG_FLAG && i + 1 < argc) {
                        i++;
                        if (def->type == GZ_ARG_STRING) def->str_value = argv[i];
                        else if (def->type == GZ_ARG_INT) def->int_value = atoi(argv[i]);
                        else if (def->type == GZ_ARG_FLOAT) def->float_value = atof(argv[i]);
                    }
                } else {
                    const char *p = arg + 1;
                    while (*p) {
                        char short_flag[3] = { '-', *p, '\0' };
                        gz_arg_def_t *def = find_def_short(args, short_flag);
                        if (!def) {
                            fprintf(stderr, "Unknown option: -%c\n", *p);
                            return -1;
                        }
                        def->found = 1;
                        if (def->type != GZ_ARG_FLAG && *(p + 1) == '\0' && i + 1 < argc) {
                            i++;
                            if (def->type == GZ_ARG_STRING) def->str_value = argv[i];
                            else if (def->type == GZ_ARG_INT) def->int_value = atoi(argv[i]);
                            else if (def->type == GZ_ARG_FLOAT) def->float_value = atof(argv[i]);
                        }
                        p++;
                    }
                }
            }
        } else {
            add_positional(args, arg, i);
        }
        i++;
    }

    for (size_t d = 0; d < args->def_count; d++) {
        if (args->defs[d].required && !args->defs[d].found) {
            fprintf(stderr, "Missing required option: %s\n",
                    args->defs[d].long_flag ? args->defs[d].long_flag : args->defs[d].short_flag);
            return -1;
        }
    }

    return 0;
}

void gz_args_free(gz_args_t *args) {
    if (!args) return;
    free(args->positionals);
    free(args->pos_indices);
    args->positionals = NULL;
    args->pos_indices = NULL;
    args->pos_count = 0;
    args->pos_capacity = 0;
}

void gz_args_print_help(const gz_args_t *args) {
    if (!args) return;
    printf("Usage:\n");
    for (size_t i = 0; i < args->def_count; i++) {
        const gz_arg_def_t *d = &args->defs[i];
        printf("  ");
        if (d->short_flag) printf("%s", d->short_flag);
        if (d->short_flag && d->long_flag) printf(", ");
        if (d->long_flag) printf("%s", d->long_flag);
        if (d->type == GZ_ARG_STRING) printf(" <string>");
        else if (d->type == GZ_ARG_INT) printf(" <int>");
        else if (d->type == GZ_ARG_FLOAT) printf(" <float>");
        printf("\t%s\n", d->description ? d->description : "");
    }
}

int gz_args_found(const gz_args_t *args, const char *long_flag) {
    if (!args) return 0;
    for (size_t i = 0; i < args->def_count; i++) {
        if (args->defs[i].long_flag && strcmp(args->defs[i].long_flag, long_flag) == 0) {
            return args->defs[i].found;
        }
    }
    return 0;
}

const char *gz_args_get_string(const gz_args_t *args, const char *long_flag, const char *dflt) {
    if (!args) return dflt;
    for (size_t i = 0; i < args->def_count; i++) {
        if (args->defs[i].long_flag && strcmp(args->defs[i].long_flag, long_flag) == 0) {
            return args->defs[i].found ? args->defs[i].str_value : dflt;
        }
    }
    return dflt;
}

int gz_args_get_int(const gz_args_t *args, const char *long_flag, int dflt) {
    if (!args) return dflt;
    for (size_t i = 0; i < args->def_count; i++) {
        if (args->defs[i].long_flag && strcmp(args->defs[i].long_flag, long_flag) == 0) {
            return args->defs[i].found ? args->defs[i].int_value : dflt;
        }
    }
    return dflt;
}

double gz_args_get_float(const gz_args_t *args, const char *long_flag, double dflt) {
    if (!args) return dflt;
    for (size_t i = 0; i < args->def_count; i++) {
        if (args->defs[i].long_flag && strcmp(args->defs[i].long_flag, long_flag) == 0) {
            return args->defs[i].found ? args->defs[i].float_value : dflt;
        }
    }
    return dflt;
}

size_t gz_args_positional_count(const gz_args_t *args) {
    if (!args) return 0;
    return args->pos_count;
}

const char *gz_args_positional(const gz_args_t *args, size_t index) {
    if (!args || index >= args->pos_count) return NULL;
    return args->positionals[index].name;
}
