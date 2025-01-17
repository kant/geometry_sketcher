bl_info = {
    "name": "Geometry Sketcher",
    "author": "hlorus",
    "version": (0, 10, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Toolbar",
    "description": "Dynamic constraint-based geometry sketcher",
    "warning": "Experimental",
    "category": "3D View",
}

if "bpy" in locals():
    import importlib

    my_modules = (
        functions,
        global_data,
        gizmos,
        operators,
        workspacetools,
        class_defines,
        ui,
        install,
        theme,
    )
    for m in my_modules:
        importlib.reload(m)
else:
    import bpy
    from . import (
        functions,
        global_data,
        gizmos,
        operators,
        workspacetools,
        class_defines,
        ui,
        install,
        theme,
    )

from tempfile import gettempdir
from pathlib import Path

import logging

logger = logging.getLogger(__name__)

# Clear handlers
if logger.hasHandlers():
    logger.handlers.clear()

logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(name)s:{%(levelname)s}: %(message)s")

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

filepath = Path(gettempdir()) / (__name__ + ".log")

logger.info("Logging into: " + str(filepath))
file_handler = logging.FileHandler(filepath, mode="w")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)




def get_wheel():
    p = Path(__file__).parent.absolute()
    from sys import platform, version_info

    if platform == "linux" or platform == "linux2":
        # Linux
        platform_strig = "linux"
    elif platform == "darwin":
        # OS X
        platform_strig = "macosx"
    elif platform == "win32":
        # Windows
        platform_strig = "win"

    matches = list(
        p.glob(
            "**/*cp{}{}*{}*.whl".format(
                version_info.major, version_info.minor, platform_strig
            )
        )
    )
    if matches:
        match = matches[0]
        logger.info("Local installation file available: " + str(match))
        return match.as_posix()
    return ""


from bpy.props import PointerProperty, BoolProperty, StringProperty, EnumProperty
import sys


log_levels = [
    ("CRITICAL", "Critical", "", 0),
    ("ERROR", "Error", "", 1),
    ("WARNING", "Warning", "", 2),
    ("INFO", "Info", "", 3),
    ("DEBUG", "Debug", "", 4),
    ("NOTSET", "Notset", "", 5),
]


def get_log_level(self):
    prop = self.bl_rna.properties["logging_level"]
    items = prop.enum_items
    default_value = items[prop.default].value
    item = items[self.get("logging_level", default_value)]
    return item.value


def set_log_level(self, value):
    items = self.bl_rna.properties["logging_level"].enum_items
    item = items[value]

    level = item.identifier
    logger.info("setting log level: {}".format(item.name))
    self["logging_level"] = level
    logger.setLevel(level)


def update_logger():
    prefs = functions.get_prefs()
    logger.setLevel(prefs.logging_level)


def ensure_addon_presets(force_write=False):
    import os
    import shutil

    scripts_folder = bpy.utils.user_resource("SCRIPTS")
    presets_dir = os.path.join(scripts_folder, "presets", "bgs")

    is_existing = True
    if not os.path.isdir(presets_dir):
        os.makedirs(presets_dir)
        is_existing = False

    if force_write or not is_existing:
        bundled_presets = os.path.join(os.path.dirname(__file__), "presets")
        files = os.listdir(bundled_presets)
        shutil.copytree(bundled_presets, presets_dir, dirs_exist_ok=True)

        logger.info("Copy addon presets to: " + presets_dir)


class Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    theme_settings: PointerProperty(type=theme.ThemeSettings)

    show_debug_settings: bpy.props.BoolProperty(
        name="Show Debug Settings",
        default=False,
    )
    show_theme_settings: bpy.props.BoolProperty(
        name="Show Theme Settings",
        description="Expand this box to show various theme settings",
        default=False,
    )
    package_path: bpy.props.StringProperty(
        name="Package Filepath",
        description="Filepath to the module's .whl file",
        subtype="FILE_PATH",
        default=get_wheel(),
    )
    logging_level: bpy.props.EnumProperty(
        name="Logging Level",
        items=log_levels,
        get=get_log_level,
        set=set_log_level,
        default=2,
    )
    hide_inactive_constraints: bpy.props.BoolProperty(
        name="Hide inactive Constraints", default=True, update=functions.update_cb
    )
    all_entities_selectable: bpy.props.BoolProperty(
        name="Make all Entities Selectable", update=functions.update_cb
    )
    force_redraw: BoolProperty(name="Force Entitie Redraw")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        box = layout.box()
        box.label(text="Solver Module")
        if global_data.registered:
            box.label(text="Registered", icon="CHECKMARK")
            module = sys.modules["py_slvs"]
            box.label(text="Path: " + module.__path__[0])
        else:
            row = box.row()
            row.label(text="Module isn't Registered", icon="CANCEL")
            split = box.split(factor=0.8)
            split.prop(self, "package_path", text="")
            split.operator(
                install.View3D_OT_slvs_install_package.bl_idname,
                text="Install from File",
            ).package = self.package_path

            row = box.row()
            row.operator(
                install.View3D_OT_slvs_install_package.bl_idname,
                text="Install from PIP",
            ).package = "py-slvs"

        box = layout.box()
        box.label(text="General")
        box.prop(self, "show_debug_settings")
        box.prop(self, "logging_level")

        box = layout.box()
        row = box.row()
        row.use_property_split = False

        subrow = row.row()
        subrow.alignment = "LEFT"
        subrow.prop(
            self,
            "show_theme_settings",
            text="Theme",
            emboss=False,
            icon="TRIA_DOWN" if self.show_theme_settings else "TRIA_RIGHT",
        )

        subrow = row.row()
        subrow.alignment = "RIGHT"
        if global_data.registered:
            ui.SKETCHER_PT_theme_presets.draw_panel_header(subrow)

        if self.show_theme_settings:
            row = box.row()

            row = box.row()
            flow = row.grid_flow(
                row_major=False,
                columns=0,
                even_columns=True,
                even_rows=False,
                align=False,
            )

            def list_props_recursiv(base):
                for prop in base.rna_type.properties:
                    prop_name = prop.identifier
                    if prop_name in ("name", "rna_type"):
                        continue

                    row = flow.row()
                    if type(prop) == bpy.types.PointerProperty:
                        row.label(text=prop.name)
                        list_props_recursiv(getattr(base, prop_name))
                    else:
                        row.prop(base, prop_name)

            list_props_recursiv(self.theme_settings)


def register():
    # Register base
    ensure_addon_presets()
    install.register()
    theme.register()
    bpy.utils.register_class(Preferences)

    update_logger()

    logger.info(
        "Enabled Geometry Sketcher base, version: {}".format(bl_info["version"])
    )

    # Check Module and register all modules
    try:
        install.check_module()
        logger.info("Solvespace available, fully registered modules")
    except ModuleNotFoundError:
        logger.warning(
            "Solvespace module isn't available, only base modules registered"
        )


def unregister():
    bpy.utils.unregister_class(Preferences)
    theme.unregister()
    install.unregister()

    if not global_data.registered:
        return

    install.unregister_full()
