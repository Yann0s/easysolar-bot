$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force C:\bench, C:\bench\llama, C:\bench\rai | Out-Null
Set-Location C:\bench
curl.exe -sL -o llama.zip https://github.com/ggml-org/llama.cpp/releases/download/b12469/llama-b12469-bin-win-cpu-x64.zip
tar -xf llama.zip -C llama
curl.exe -sL -o rai.zip https://github.com/Classevelabs/rai/releases/download/v0.2.5/rai-0.2.5-x86_64-pc-windows-msvc.zip
tar -xf rai.zip -C rai
git clone -q --depth 1 https://github.com/razancodes/ferrite
git clone -q --depth 1 https://github.com/lucasjinreal/Crane
Get-ChildItem -Recurse llama, rai -Filter *.exe | Select-Object -ExpandProperty FullName
