/* Build every setting with the extracted upstream constructors and read the
 * fields a constructor never assigns. The Nix check compiles this file with
 * -ftrivial-auto-var-init=pattern, so an unassigned field holds a nonzero
 * pattern instead of whatever the stack held. That makes the upstream defect
 * fail on every run. No frontend, display or game ROMs.
 */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "setting_list.h"

/* The constructors only store these addresses. Nothing calls them here. */
#define ONE_ARGUMENT_HANDLER(name) \
   static int name(rarch_setting_t *setting) { (void)setting; return 0; }
#define INDEXED_HANDLER(name) \
   static int name(rarch_setting_t *setting, size_t idx, bool wraparound) \
   { (void)setting; (void)idx; (void)wraparound; return 0; }
#define TEXT_HANDLER(name) \
   static size_t name(rarch_setting_t *setting, char *s, size_t len) \
   { (void)setting; (void)s; (void)len; return 0; }

ONE_ARGUMENT_HANDLER(setting_generic_action_start_default)
ONE_ARGUMENT_HANDLER(setting_string_action_start_generic)
ONE_ARGUMENT_HANDLER(setting_bind_action_start)
INDEXED_HANDLER(setting_generic_action_ok_default)
INDEXED_HANDLER(setting_action_action_ok)
INDEXED_HANDLER(setting_bind_action_ok)
INDEXED_HANDLER(setting_bool_action_ok_default)
INDEXED_HANDLER(setting_uint_action_left_default)
INDEXED_HANDLER(setting_uint_action_right_default)
INDEXED_HANDLER(setting_size_action_left_default)
INDEXED_HANDLER(setting_size_action_right_default)
INDEXED_HANDLER(setting_int_action_left_default)
INDEXED_HANDLER(setting_int_action_right_default)
INDEXED_HANDLER(setting_fraction_action_left_default)
INDEXED_HANDLER(setting_fraction_action_right_default)
TEXT_HANDLER(setting_get_string_representation_default)
TEXT_HANDLER(setting_get_string_representation_uint)
TEXT_HANDLER(setting_get_string_representation_int)
TEXT_HANDLER(setting_get_string_representation_st_string)
TEXT_HANDLER(setting_get_string_representation_st_path)
TEXT_HANDLER(setting_get_string_representation_st_dir)
TEXT_HANDLER(setting_get_string_representation_st_float)
TEXT_HANDLER(setting_get_string_representation_st_bool)
TEXT_HANDLER(setting_get_string_representation_st_bind)

#include "setting-constructors-extracted.h"

/* The Qt desktop menu switches on ui_type for every setting it lists. Only
 * some config_* helpers assign it after the constructor returns. */
static void desktop_menu_ignores(const char *constructor, rarch_setting_t setting)
{
   if (setting.ui_type != ST_UI_TYPE_NONE || setting.enum_value_idx != MSG_UNKNOWN)
   {
      fprintf(stderr, "%s left ui_type=%#x enum_value_idx=%#x unassigned\n",
            constructor, (unsigned)setting.ui_type, (unsigned)setting.enum_value_idx);
      exit(EXIT_FAILURE);
   }
}

/* Actions and groups have no value. A widget must never see a target. */
static void has_no_value(const char *constructor, rarch_setting_t setting)
{
   static const rarch_setting_t empty;
   desktop_menu_ignores(constructor, setting);
   if (setting.value.target.string
         || memcmp(&setting.default_value, &empty.default_value,
            sizeof(setting.default_value))
         || setting.dir.empty_path)
   {
      fprintf(stderr, "%s left a value field unassigned\n", constructor);
      exit(EXIT_FAILURE);
   }
}

int main(void)
{
   static bool boolean;
   static int integer;
   static unsigned unsigned_integer;
   static size_t size;
   static float fraction;
   static char text[8];

   has_no_value("setting_action_setting",
         setting_action_setting("name", "description", "group", "subgroup",
            "parent", false));
   has_no_value("setting_group_setting",
         setting_group_setting(ST_GROUP, "name", "parent"));
   has_no_value("setting_subgroup_setting",
         setting_subgroup_setting(ST_SUB_GROUP, "name", "parent name",
            "parent", false));

   desktop_menu_ignores("setting_bool_setting",
         setting_bool_setting("name", "description", &boolean, false, "off",
            "on", "group", "subgroup", "parent", NULL, NULL, false));
   desktop_menu_ignores("setting_int_setting",
         setting_int_setting("name", "description", &integer, 0, "group",
            "subgroup", "parent", NULL, NULL, false));
   desktop_menu_ignores("setting_uint_setting",
         setting_uint_setting("name", "description", &unsigned_integer, 0,
            "group", "subgroup", "parent", NULL, NULL, false));
   desktop_menu_ignores("setting_size_setting",
         setting_size_setting("name", "description", &size, 0, "group",
            "subgroup", "parent", NULL, NULL, false,
            setting_get_string_representation_default));
   desktop_menu_ignores("setting_float_setting",
         setting_float_setting("name", "description", &fraction, 0.0f, "%.1f",
            "group", "subgroup", "parent", NULL, NULL, false));
   desktop_menu_ignores("setting_bind_setting",
         setting_bind_setting("name", "description", NULL, 0, 0, NULL,
            "group", "subgroup", "parent", false));
   desktop_menu_ignores("setting_string_setting",
         setting_string_setting(ST_STRING, "name", "description", text,
            sizeof(text), "", "", "group", "subgroup", "parent", NULL, NULL,
            false));

   puts("Every RetroArch setting constructor returned its unassigned fields as zero");
   return 0;
}
