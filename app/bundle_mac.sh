#!/bin/sh
# Construit EasySolar.app à la racine du projet (binaire release + modèles et vecteurs des paragraphes, copiés en clones APFS sans place disque en plus).
set -e
cd "$(dirname "$0")"
cargo build --release
app=../EasySolar.app
rm -rf "$app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources/models"
cp macos/Info.plist "$app/Contents/"
cp macos/launcher target/release/easysolar "$app/Contents/MacOS/"
cp macos/AppIcon.icns "$app/Contents/Resources/"
EASYSOLAR_MODELS=../models target/release/easysolar --save-vectors   # vecteurs des paragraphes : démarrage sans les recalculer
cp -c ../models/Qwen3.5-0.8B-easysolar-Q4_K_M.gguf ../models/Qwen3-Embedding-0.6B-Q8_0.gguf ../models/paragraphes.bin "$app/Contents/Resources/models/"
# signature ad hoc (sans compte développeur) : téléchargée, l'app est « non vérifiée » au lieu d'« endommagée »
codesign --force --deep --sign - "$app"
echo "OK : $(cd .. && pwd)/EasySolar.app"
