//! Sur macOS, compile la fenêtre native (native/macos_webview.m) en bibliothèque statique, comme Pulsefy.
//! Sous Windows, intègre l'icône (windows/easysolar.ico, générée par macos/icon.py) dans l'exe.
use std::env;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    #[cfg(windows)]
    {
        println!("cargo:rerun-if-changed=windows/easysolar.ico");
        winresource::WindowsResource::new().set_icon("windows/easysolar.ico").compile().unwrap();
    }
    if env::var("CARGO_CFG_TARGET_OS").unwrap() != "macos" {
        return;
    }
    println!("cargo:rerun-if-changed=native/macos_webview.m");
    let out = PathBuf::from(env::var("OUT_DIR").unwrap());
    let obj = out.join("macos_webview.o");
    let ok = Command::new("/usr/bin/clang").args(["-c", "-fobjc-arc", "-O2", "native/macos_webview.m", "-o"]).arg(&obj).status().unwrap();
    assert!(ok.success(), "clang a échoué sur native/macos_webview.m");
    let ok = Command::new("/usr/bin/ar").arg("rcs").arg(out.join("libmacos_webview.a")).arg(&obj).status().unwrap();
    assert!(ok.success(), "ar a échoué");
    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-lib=static=macos_webview");
    println!("cargo:rustc-link-lib=framework=Cocoa");
    println!("cargo:rustc-link-lib=framework=WebKit");
}
