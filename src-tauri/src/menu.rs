//! 菜单模块 - 应用菜单配置

use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem, Submenu},
    AppHandle, Emitter, Manager,
};

use crate::logger::log;

/// 创建应用菜单
pub fn create<R: tauri::Runtime, M: tauri::Manager<R>>(
    app: &M,
) -> Result<Menu<R>, tauri::Error> {
    let app_submenu = Submenu::with_items(
        app,
        "LocalBrisk",
        true,
        &[
            &MenuItem::with_id(app, "about", "About LocalBrisk", true, None::<&str>)?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(app, "settings", "Settings...", true, Some("CmdOrCtrl+,"))?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::hide(app, Some("Hide LocalBrisk"))?,
            &PredefinedMenuItem::hide_others(app, Some("Hide Others"))?,
            &PredefinedMenuItem::show_all(app, Some("Show All"))?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::quit(app, Some("Quit LocalBrisk"))?,
        ],
    )?;

    let edit_submenu = Submenu::with_items(
        app,
        "Edit",
        true,
        &[
            &PredefinedMenuItem::undo(app, Some("Undo"))?,
            &PredefinedMenuItem::redo(app, Some("Redo"))?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::cut(app, Some("Cut"))?,
            &PredefinedMenuItem::copy(app, Some("Copy"))?,
            &PredefinedMenuItem::paste(app, Some("Paste"))?,
            &PredefinedMenuItem::select_all(app, Some("Select All"))?,
        ],
    )?;

    let window_submenu = Submenu::with_items(
        app,
        "Window",
        true,
        &[
            &PredefinedMenuItem::minimize(app, Some("Minimize"))?,
            &PredefinedMenuItem::maximize(app, Some("Maximize"))?,
            &PredefinedMenuItem::separator(app)?,
            &PredefinedMenuItem::close_window(app, Some("Close Window"))?,
        ],
    )?;

    let help_submenu = Submenu::with_items(
        app,
        "Help",
        true,
        &[
            &MenuItem::with_id(app, "documentation", "Documentation", true, None::<&str>)?,
            &MenuItem::with_id(app, "feedback", "Report Issue", true, None::<&str>)?,
            &PredefinedMenuItem::separator(app)?,
            &MenuItem::with_id(
                app,
                "devtools",
                "Toggle Developer Tools",
                true,
                Some("CmdOrCtrl+Shift+I"),
            )?,
        ],
    )?;

    Ok(Menu::with_items(
        app,
        &[&app_submenu, &edit_submenu, &window_submenu, &help_submenu],
    )?)
}

/// 处理菜单事件
pub fn handle_event(app: &AppHandle, event_id: &str) {
    log(&format!("菜单事件触发: {}", event_id));

    match event_id {
        "settings" => emit_to_main(app, "open-settings"),
        "about" => emit_to_main(app, "open-about"),
        "documentation" => open_url("https://github.com/localbrisk/localbrisk"),
        "feedback" => open_url("https://github.com/localbrisk/localbrisk/issues"),
        "devtools" => toggle_devtools(app),
        _ => {}
    }
}

fn emit_to_main(app: &AppHandle, event: &str) {
    if let Some(window) = app.get_webview_window("main") {
        match window.emit(event, ()) {
            Ok(_) => log(&format!("已发送 {} 事件到主窗口", event)),
            Err(e) => log(&format!("发送事件失败: {:?}", e)),
        }
    } else {
        log("未找到主窗口");
    }
}

fn open_url(url: &str) {
    let url = url.to_string();
    tauri::async_runtime::spawn(async move {
        let _ = open::that(url);
    });
}

fn toggle_devtools(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        if window.is_devtools_open() {
            window.close_devtools();
        } else {
            window.open_devtools();
        }
    }
}
