Set-Location C:\bench\ferrite
cargo build --release 2>&1 | Select-Object -Last 5
"FERRITE EXIT $LASTEXITCODE"
Set-Location C:\bench\Crane
cargo build --release 2>&1 | Select-Object -Last 5
"CRANE EXIT $LASTEXITCODE"
