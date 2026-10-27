/* Independent test of the generated facts against the built libretro ABI. */
#include <stdbool.h>
#include <dlfcn.h>
#include <stdio.h>

struct retro_system_info {
    const char *library_name;
    const char *library_version;
    const char *valid_extensions;
    bool need_fullpath;
    bool block_extract;
};

int main(int argc, char **argv)
{
    if (argc != 2)
        return 1;
    void *core = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!core) {
        fprintf(stderr, "%s\n", dlerror());
        return 1;
    }
    void (*get_info)(struct retro_system_info *) = dlsym(core, "retro_get_system_info");
    if (!get_info)
        return 1;
    struct retro_system_info info = {0};
    get_info(&info);
    if (!info.library_name || !info.library_version)
        return 1;
    printf("%s\n%s\n", info.library_name, info.library_version);
    dlclose(core);
    return 0;
}
