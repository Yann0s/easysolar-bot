Set-Location C:\bench
$rai = "rai\rai-0.2.5-x86_64-pc-windows-msvc\rai.exe"
$p = (Get-Content -Raw system.txt) + "`n`nQuestion : " + (Get-Content -Raw question.txt)
foreach ($i in 1..3) {
  $t = Measure-Command { & $rai run models\qwen3-1.7b-q4.raimodel --chat-template chatml --temperature 0 --max-tokens 300 --prompt "Session $i. $p" > "rai_out_$i.txt" 2> "rai_err_$i.txt" }
  "RUN $i : {0:N1} s" -f $t.TotalSeconds
}
Get-Content rai_err_1.txt -Tail 15
Get-Content rai_out_1.txt -TotalCount 5
"RAI DONE"
