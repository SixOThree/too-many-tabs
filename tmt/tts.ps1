param([Parameter(Mandatory = $true)][string]$Jobs)
# Batch text-to-speech: reads a JSON array of {path, voice, rate, text} and writes 48 kHz mono WAVs.
Add-Type -AssemblyName System.Speech
$list = Get-Content -Raw -LiteralPath $Jobs | ConvertFrom-Json
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(48000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$done = 0
foreach ($j in $list) {
    if (Test-Path -LiteralPath $j.path) { continue }
    $synth.SelectVoice($j.voice)
    $synth.Rate = [int]$j.rate
    $synth.SetOutputToWaveFile($j.path, $fmt)
    $synth.Speak([string]$j.text)
    $synth.SetOutputToNull()
    $done++
}
$synth.Dispose()
Write-Output "tts generated $done"
