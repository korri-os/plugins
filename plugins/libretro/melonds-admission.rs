//! Actual producer manifest, locked Core registry parser, and sandbox callback.
//! This check never installs a selection or starts an emulator.
use korrid::{
    launcher::plugin_launch::{PluginLaunchInput, evaluate_snapshot},
    plugin::PluginRegistry,
    plugin_installation::EnabledPackage,
    script::source::SourceSnapshot,
};
use serde::Deserialize;
use std::{collections::BTreeMap, fs, path::PathBuf};

// These fields are read from the builder's real manifest, as in Core's
// tests/published_game_launch.rs. Unrelated manifest fields remain producer-owned.
#[derive(Deserialize)]
struct Manifest {
    publisher: Publisher,
    entry: String,
    sources: Vec<String>,
    files: BTreeMap<String, PathBuf>,
}
#[derive(Deserialize)]
struct Publisher {
    namespace: String,
}

#[test]
fn packaged_melonds_panes_layouts_and_launch() {
    let package = PathBuf::from(std::env::var_os("KORRI_MELONDS_PACKAGE").unwrap());
    let manifest: Manifest =
        serde_json::from_slice(&fs::read(package.join("manifest.json")).unwrap()).unwrap();
    assert_eq!(manifest.publisher.namespace, "@korri");
    let registry = PluginRegistry::from_installed(vec![EnabledPackage {
        id: "@korri:melonds".into(),
        package: package.clone(),
        files: manifest.files.clone(),
        entry: manifest.entry.clone(),
        sources: manifest.sources.clone(),
        requires: Vec::new(),
        hosts: Vec::new(),
    }])
    .expect("locked Core must admit the packaged source graph and typed panes/layouts");
    let system = registry.systems().values().next().unwrap();
    assert_eq!(system.id, "nds");
    assert_eq!(
        system
            .panes
            .as_ref()
            .unwrap()
            .iter()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        ["upper", "lower"]
    );
    assert_eq!(system.arrangement.as_deref(), Some("upper-above-lower"));
    let runner = &registry.runners()["@korri:melonds/melonds"];
    assert_eq!(
        runner
            .layouts
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        ["Bottom Only", "Left/Right", "Top Only", "Top/Bottom"]
    );
    for (layout, expected) in [
        (
            "Top/Bottom",
            vec![("upper", [0., 0., 1., 0.5]), ("lower", [0., 0.5, 1., 0.5])],
        ),
        (
            "Left/Right",
            vec![("upper", [0., 0., 0.5, 1.]), ("lower", [0.5, 0., 0.5, 1.])],
        ),
        ("Top Only", vec![("upper", [0., 0., 1., 1.])]),
        ("Bottom Only", vec![("lower", [0., 0., 1., 1.])]),
    ] {
        let panes = &runner.layouts[layout].panes;
        assert_eq!(panes.len(), expected.len());
        for (pane, rect) in expected {
            let parsed = &panes[pane];
            assert_eq!(
                [
                    parsed.x.value(),
                    parsed.y.value(),
                    parsed.width.value(),
                    parsed.height.value()
                ],
                rect
            );
        }
        let input: PluginLaunchInput = serde_json::from_value(serde_json::json!({
            "runnerId": runner.id,
            "layout": layout,
            "familyId": "@korri:retroarch",
            "program": manifest.files["retroarch"],
            "corePath": manifest.files["melonds"],
            "contentPath": "/games/tetris.nds",
            "accountRoot": "/account",
            "saveRoot": "/saves",
            "cacheRoot": "/cache",
            "files": manifest.files,
            "artifacts": {},
        }))
        .unwrap();
        let source =
            SourceSnapshot::package_plugin(&package, &manifest.entry, &manifest.sources).unwrap();
        let plan = evaluate_snapshot(&source, &input)
            .expect("real launch.prepare must accept Core's selected layout");
        assert_eq!(
            plan.env["KORRI_RETROARCH_CORE_OPTIONS_OVERLAY"],
            "/account/melonds-layout.opt"
        );
        let overlay = plan
            .files
            .iter()
            .find(|file| file.path == "/account/melonds-layout.opt")
            .unwrap();
        assert_eq!(
            overlay.content,
            format!(
                "melonds_screen_layout = \"{layout}\"\nmelonds_screen_gap = \"0\"\nmelonds_touch_mode = \"Touch\"\n"
            )
        );
        let config = plan
            .files
            .iter()
            .find(|file| file.path == "/account/retroarch.cfg")
            .unwrap();
        assert!(
            config
                .content
                .lines()
                .any(|line| line == "input_driver = \"x\"")
        );
        assert!(
            config
                .content
                .lines()
                .any(|line| line == "input_joypad_driver = \"udev\"")
        );
        assert!(
            config
                .content
                .lines()
                .any(|line| line == "config_save_on_exit = \"false\"")
        );
    }
}
